from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from pypdf import PdfReader
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditLog,
    Company,
    ParserRunLog,
    ProjectAddress,
    ProjectAlias,
    ProjectMaster,
    Report,
    ReviewQueueItem,
    StagingFieldCandidate,
    StagingProjectCandidate,
    StagingReport,
    StagingSection,
)
from app.services.identity_ops import normalize_text, refresh_candidate_match_suggestions


PARSER_VERSION = "rule_parser_v1"
MAX_SECTION_NOTE_LENGTH = 500
SECTION_HINTS = (
    "project",
    "projects",
    "residential",
    "urban renewal",
    "inventory",
    "pipeline",
    "פרויקט",
    "פרויק",
    "מגורים",
    "שיווק",
    "מלאי",
    "ביצוע",
    "התחדשות",
    "ייזום",
)
STATUS_PATTERNS = {
    "project_status": [
        ("construction", [r"\bconstruction\b", r"\bunder construction\b", r"בבנייה", r"בניה"]),
        ("marketing", [r"\bmarketing\b", r"\bsales\b", r"\bpre[\s-]?sale\b", r"שיווק", r"מכירה"]),
        ("planning", [r"\bplanning\b", r"\bplan(?:ning)?\b", r"תכנון"]),
        ("completed", [r"\bcompleted\b", r"\bdelivered\b", r"\boccup(?:ancy|ied)\b", r"הושלם", r"אוכלס"]),
        ("permit", [r"\bpermit\b", r"\blicen[cs]e\b", r"היתר"]),
        ("stalled", [r"\bstalled\b", r"\bfrozen\b", r"הוקפא", r"נעצר"]),
    ],
    "permit_status": [
        ("granted", [r"\bpermit granted\b", r"\bapproved permit\b", r"היתר בנ(?:י|י)ה", r"היתר התקבל"]),
        ("pending", [r"\bpending permit\b", r"\bawaiting permit\b", r"טרם התקבל", r"ממתין להיתר"]),
        ("partial", [r"\bpartial permit\b", r"היתר חלקי"]),
        ("none", [r"\bno permit\b", r"ללא היתר"]),
    ],
}
METRIC_PATTERNS = {
    "total_units": [
        r"(?:total units|units total|סה[\"״]?כ יח[\"״]?ד|סה[\"״]?כ דירות|יח[\"״]?ד)\D{0,24}(\d{1,4})",
    ],
    "marketed_units": [
        r"(?:marketed units|units marketed|דירות משווקות|יח[\"״]?ד משווקות|שווקו)\D{0,24}(\d{1,4})",
    ],
    "sold_units_cumulative": [
        r"(?:sold units|units sold|דירות שנמכרו|נמכרו)\D{0,24}(\d{1,4})",
    ],
    "unsold_units": [
        r"(?:unsold units|remaining units|דירות לא מכורות|מלאי לא מכור|יתרה לשיווק)\D{0,24}(-?\d{1,4})",
    ],
    "avg_price_per_sqm_cumulative": [
        r"(?:avg(?:\.|erage)? price(?: per)? sqm|מחיר ממוצע למ[\"״]?ר)\D{0,24}([\d,]{4,10}(?:\.\d{1,2})?)",
    ],
    "gross_margin_expected_pct": [
        r"(?:gross margin|רווח גולמי)\D{0,24}(-?\d{1,2}(?:\.\d{1,2})?)\s*%",
    ],
}


@dataclass
class ExtractedSection:
    section_name: str
    raw_label: str | None
    source_page_from: int
    source_page_to: int
    text: str


@dataclass
class AliasCandidate:
    project_id: UUID
    project_name: str
    city: str | None
    neighborhood: str | None
    aliases: list[str]
    addresses: list[str]


def _confidence_score(level: str) -> Decimal:
    return {
        "high": Decimal("95.00"),
        "medium": Decimal("78.00"),
        "low": Decimal("55.00"),
    }.get(level, Decimal("55.00"))


def _excerpt(value: str | None, limit: int = MAX_SECTION_NOTE_LENGTH) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _stringify(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


async def _record_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID,
    diff_json: dict[str, object] | None,
    comment: str | None,
) -> None:
    session.add(
        AdminAuditLog(
            id=uuid4(),
            actor_user_id=None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            diff_json=diff_json,
            comment=comment,
            created_at=datetime.now(UTC),
        )
    )


async def _sync_report_queue(
    session: AsyncSession,
    report_id: UUID,
    candidate_id: UUID | None,
    status: str,
    notes: str | None,
) -> None:
    item = (
        await session.execute(
            select(ReviewQueueItem).where(
                ReviewQueueItem.report_id == report_id,
                ReviewQueueItem.candidate_id == candidate_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        item = ReviewQueueItem(
            id=uuid4(),
            entity_type="candidate" if candidate_id else "report",
            entity_id=candidate_id or report_id,
            report_id=report_id,
            candidate_id=candidate_id,
            status=status,
            notes=notes,
        )
        session.add(item)
        return
    item.status = status
    item.notes = notes


async def _load_report(session: AsyncSession, report_id: UUID) -> tuple[Report, StagingReport] | tuple[None, None]:
    report = (await session.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if report is None:
        return None, None
    staging_report = (
        await session.execute(select(StagingReport).where(StagingReport.report_id == report.id))
    ).scalar_one_or_none()
    if staging_report is None:
        staging_report = StagingReport(
            id=uuid4(),
            report_id=report.id,
            company_id=report.company_id,
            publish_status="draft",
            review_status="pending",
        )
        session.add(staging_report)
        await session.flush()
    return report, staging_report


def _source_reference(report: Report) -> str | None:
    return report.source_file_path or report.source_url


async def _read_report_bytes(report: Report) -> tuple[bytes, str]:
    if report.source_file_path:
        with open(report.source_file_path, "rb") as file_handle:
            return file_handle.read(), report.source_file_path
    if report.source_url:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            response = await client.get(report.source_url)
            response.raise_for_status()
            return response.content, report.source_url
    raise ValueError("Report has no source_url or source_file_path configured for extraction.")


def _extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.replace("\x00", " ").strip())
    return pages


def _section_label_from_page(page_text: str, page_number: int) -> tuple[str, str | None]:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for line in lines[:12]:
        normalized = normalize_text(line)
        if 4 <= len(line) <= 120 and any(hint in normalized for hint in SECTION_HINTS):
            return line[:120], line[:120]
    return f"Page {page_number}", None


def _segment_sections(pages: list[str]) -> list[ExtractedSection]:
    sections: list[ExtractedSection] = []
    for index, page_text in enumerate(pages, start=1):
        if not page_text.strip():
            sections.append(
                ExtractedSection(
                    section_name=f"Page {index}",
                    raw_label=None,
                    source_page_from=index,
                    source_page_to=index,
                    text="",
                )
            )
            continue
        section_name, raw_label = _section_label_from_page(page_text, index)
        sections.append(
            ExtractedSection(
                section_name=section_name,
                raw_label=raw_label,
                source_page_from=index,
                source_page_to=index,
                text=page_text,
            )
        )
    return sections


async def _company_alias_candidates(session: AsyncSession, company_id: UUID) -> list[AliasCandidate]:
    rows = (
        await session.execute(
            select(ProjectMaster)
            .where(
                ProjectMaster.company_id == company_id,
                ProjectMaster.deleted_at.is_(None),
                ProjectMaster.merged_into_project_id.is_(None),
            )
            .order_by(ProjectMaster.canonical_name.asc())
        )
    ).scalars().all()
    items: list[AliasCandidate] = []
    for project in rows:
        aliases = (
            await session.execute(
                select(ProjectAlias.alias_name)
                .where(ProjectAlias.project_id == project.id, ProjectAlias.is_active.is_(True))
                .order_by(ProjectAlias.created_at.asc())
            )
        ).scalars().all()
        addresses = (
            await session.execute(
                select(ProjectAddress.address_text_raw, ProjectAddress.street, ProjectAddress.city)
                .where(ProjectAddress.project_id == project.id)
                .order_by(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc())
            )
        ).all()
        address_values: list[str] = []
        for address_text_raw, street, city in addresses:
            for value in (address_text_raw, street, city):
                if value:
                    address_values.append(value)
        items.append(
            AliasCandidate(
                project_id=project.id,
                project_name=project.canonical_name,
                city=project.city,
                neighborhood=project.neighborhood,
                aliases=[project.canonical_name, *[alias for alias in aliases if alias]],
                addresses=address_values,
            )
        )
    return items


async def _known_city_lexicon(session: AsyncSession) -> list[str]:
    values = (
        await session.execute(
            select(ProjectMaster.city)
            .where(ProjectMaster.city.is_not(None))
            .distinct()
            .order_by(ProjectMaster.city.asc())
        )
    ).scalars().all()
    cities = [value for value in values if value]
    cities.sort(key=len, reverse=True)
    return cities


def _context_window(text: str, alias: str, radius: int = 320) -> str:
    lowered = normalize_text(text)
    marker = normalize_text(alias)
    if not marker:
        return text[: radius * 2]
    index = lowered.find(marker)
    if index < 0:
        return text[: radius * 2]
    start = max(0, index - radius)
    end = min(len(text), index + len(alias) + radius)
    return text[start:end]


def _detect_city(text: str, known_cities: list[str], fallback_city: str | None) -> tuple[str | None, str]:
    normalized = normalize_text(text)
    for city in known_cities:
        if normalize_text(city) and normalize_text(city) in normalized:
            return city, "reported"
    if fallback_city and normalize_text(fallback_city) in normalized:
        return fallback_city, "reported"
    return None, "unknown"


def _detect_neighborhood(text: str, fallback_neighborhood: str | None) -> tuple[str | None, str]:
    if fallback_neighborhood and normalize_text(fallback_neighborhood) in normalize_text(text):
        return fallback_neighborhood, "reported"
    return None, "unknown"


def _extract_status(window_text: str, field_name: str) -> tuple[str | None, str]:
    normalized = normalize_text(window_text)
    for status_value, patterns in STATUS_PATTERNS[field_name]:
        for pattern in patterns:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return status_value, "inferred"
    return None, "unknown"


def _extract_metric(window_text: str, field_name: str) -> tuple[str | None, Decimal | int | None, str]:
    for pattern in METRIC_PATTERNS.get(field_name, []):
        match = re.search(pattern, window_text, flags=re.IGNORECASE)
        if not match:
            continue
        raw_value = match.group(1)
        if raw_value is None:
            continue
        compact = raw_value.replace(",", "").strip()
        try:
            if field_name in {"avg_price_per_sqm_cumulative", "gross_margin_expected_pct"}:
                return raw_value.strip(), Decimal(compact), "reported"
            return raw_value.strip(), int(compact), "reported"
        except (InvalidOperation, ValueError):
            continue
    return None, None, "unknown"


def _candidate_confidence(alias: str, canonical_name: str) -> str:
    if normalize_text(alias) == normalize_text(canonical_name):
        return "high"
    if canonical_name and alias and normalize_text(alias) in normalize_text(canonical_name):
        return "medium"
    return "medium"


def _safe_int(value: object | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    return None


def _safe_decimal(value: object | None) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return None


def _parser_confidence_from_status(status: str) -> Decimal:
    if status == "succeeded":
        return Decimal("92.00")
    if status == "partial":
        return Decimal("70.00")
    if status == "failed":
        return Decimal("25.00")
    return Decimal("55.00")


async def _clear_previous_parser_output(
    session: AsyncSession,
    staging_report_id: UUID,
) -> None:
    await session.execute(
        delete(StagingProjectCandidate).where(
            StagingProjectCandidate.staging_report_id == staging_report_id,
            StagingProjectCandidate.parser_run_id.is_not(None),
            StagingProjectCandidate.publish_status != "published",
        )
    )
    await session.execute(
        delete(StagingSection).where(
            StagingSection.staging_report_id == staging_report_id,
            StagingSection.parser_run_id.is_not(None),
        )
    )


async def run_report_extraction(session: AsyncSession, report_id: UUID) -> dict | None:
    report, staging_report = await _load_report(session, report_id)
    if report is None or staging_report is None:
        return None

    parser_run = ParserRunLog(
        id=uuid4(),
        report_id=report.id,
        staging_report_id=staging_report.id,
        status="running",
        parser_version=PARSER_VERSION,
        source_label=report.source_label,
        source_reference=_source_reference(report),
        started_at=datetime.now(UTC),
    )
    session.add(parser_run)
    await session.flush()

    warnings: list[str] = []
    errors: list[str] = []
    diagnostics: dict[str, Any] = {
        "report_name": report.filing_reference,
        "period_end_date": report.period_end_date.isoformat(),
    }

    try:
        pdf_bytes, source_reference = await _read_report_bytes(report)
        parser_run.source_reference = source_reference
        parser_run.source_checksum = sha256(pdf_bytes).hexdigest()
        pages = _extract_pdf_pages(pdf_bytes)
        if not any(page.strip() for page in pages):
            warnings.append("PDF text extraction returned empty content. OCR is intentionally out of scope for this phase.")

        await _clear_previous_parser_output(session, staging_report.id)
        sections = _segment_sections(pages)
        parser_run.sections_found = len(sections)
        diagnostics["page_count"] = len(pages)
        diagnostics["text_characters"] = sum(len(page) for page in pages)

        persisted_sections: list[StagingSection] = []
        for section in sections:
            row = StagingSection(
                id=uuid4(),
                staging_report_id=staging_report.id,
                parser_run_id=parser_run.id,
                section_name=section.section_name,
                raw_label=section.raw_label,
                source_page_from=section.source_page_from,
                source_page_to=section.source_page_to,
                notes=_excerpt(section.text),
            )
            session.add(row)
            persisted_sections.append(row)
        await session.flush()

        candidate_sources = await _company_alias_candidates(session, report.company_id)
        known_cities = await _known_city_lexicon(session)
        candidate_rows: list[StagingProjectCandidate] = []
        field_count = 0

        for source in candidate_sources:
            section_hit: tuple[StagingSection, str, str] | None = None
            best_alias = source.project_name
            for section_row, section in zip(persisted_sections, sections, strict=False):
                section_norm = normalize_text(section.text)
                for alias in sorted(set(source.aliases), key=len, reverse=True):
                    alias_norm = normalize_text(alias)
                    if alias_norm and alias_norm in section_norm:
                        section_hit = (section_row, section.text, alias)
                        best_alias = alias
                        break
                if section_hit:
                    break

            if section_hit is None:
                continue

            section_row, section_text, matched_alias = section_hit
            context = _context_window(section_text, matched_alias)
            city, city_origin = _detect_city(context, known_cities, source.city)
            neighborhood, neighborhood_origin = _detect_neighborhood(context, source.neighborhood)
            project_status, project_status_origin = _extract_status(context, "project_status")
            permit_status, permit_status_origin = _extract_status(context, "permit_status")

            metrics: dict[str, tuple[str | None, Decimal | int | None, str]] = {}
            for field_name in METRIC_PATTERNS:
                metrics[field_name] = _extract_metric(context, field_name)

            confidence_level = _candidate_confidence(matched_alias, source.project_name)
            candidate = StagingProjectCandidate(
                id=uuid4(),
                staging_report_id=staging_report.id,
                parser_run_id=parser_run.id,
                company_id=report.company_id,
                staging_section_id=section_row.id,
                matched_project_id=source.project_id,
                candidate_project_name=matched_alias,
                city=city,
                neighborhood=neighborhood,
                project_business_type=None,
                government_program_type="none",
                project_urban_renewal_type="none",
                project_status=project_status,
                permit_status=permit_status,
                total_units=_safe_int(metrics["total_units"][1]),
                marketed_units=_safe_int(metrics["marketed_units"][1]),
                sold_units_cumulative=_safe_int(metrics["sold_units_cumulative"][1]),
                unsold_units=_safe_int(metrics["unsold_units"][1]),
                avg_price_per_sqm_cumulative=_safe_decimal(metrics["avg_price_per_sqm_cumulative"][1]),
                gross_profit_total_expected=None,
                gross_margin_expected_pct=_safe_decimal(metrics["gross_margin_expected_pct"][1]),
                location_confidence="city_only" if city else "unknown",
                value_origin_type="imported",
                confidence_level=confidence_level,
                matching_status="matched_existing_project",
                publish_status="draft",
                review_status="pending",
                review_notes="Parser-created candidate. Human review required before publish.",
            )
            session.add(candidate)
            candidate_rows.append(candidate)
            await session.flush()

            fields_to_insert: list[tuple[str, str | None, str | None, str, str]] = []
            fields_to_insert.append(("canonical_name", matched_alias, source.project_name, "reported", confidence_level))
            if city:
                fields_to_insert.append(("city", city, city, city_origin, "high" if city_origin == "reported" else "medium"))
            if neighborhood:
                fields_to_insert.append(
                    ("neighborhood", neighborhood, neighborhood, neighborhood_origin, "medium")
                )
            if project_status:
                fields_to_insert.append(("project_status", project_status, project_status, project_status_origin, "medium"))
            if permit_status:
                fields_to_insert.append(("permit_status", permit_status, permit_status, permit_status_origin, "medium"))

            for metric_field, (raw_value, normalized_value, origin) in metrics.items():
                if normalized_value is None:
                    continue
                fields_to_insert.append(
                    (
                        metric_field,
                        raw_value,
                        _stringify(normalized_value),
                        origin,
                        "medium" if metric_field == "gross_margin_expected_pct" else "high",
                    )
                )

            for field_name, raw_value, normalized_value, origin, field_confidence in fields_to_insert:
                session.add(
                    StagingFieldCandidate(
                        id=uuid4(),
                        candidate_id=candidate.id,
                        field_name=field_name,
                        raw_value=raw_value,
                        normalized_value=normalized_value,
                        source_page=section_row.source_page_from,
                        source_section=section_row.section_name,
                        value_origin_type=origin if origin in {"reported", "inferred"} else "unknown",
                        confidence_level=field_confidence,
                        review_status="pending",
                        review_notes="Parser-created field candidate. Review before publish.",
                    )
                )
                field_count += 1

            await refresh_candidate_match_suggestions(session, candidate)
            await _sync_report_queue(
                session,
                report.id,
                candidate.id,
                "open",
                "Parser-created candidate awaiting review",
            )

        parser_run.candidate_count = len(candidate_rows)
        parser_run.field_candidate_count = field_count
        parser_run.address_candidate_count = 0
        if not candidate_rows:
            warnings.append("No project candidates were detected from the extracted text.")

        report.ingestion_status = "in_review"
        staging_report.review_status = "pending"
        await _sync_report_queue(
            session,
            report.id,
            None,
            "open",
            f"Parser run completed with {len(candidate_rows)} candidate(s).",
        )
        parser_run.status = "succeeded" if candidate_rows else "partial"
        parser_run.warnings_json = warnings
        parser_run.errors_json = errors
        parser_run.diagnostics_json = {
            **diagnostics,
            "matched_projects": [str(candidate.matched_project_id) for candidate in candidate_rows if candidate.matched_project_id],
        }
        parser_run.finished_at = datetime.now(UTC)
        await _record_audit(
            session,
            action="parser_report_extract",
            entity_type="report",
            entity_id=report.id,
            diff_json={
                "parser_run_id": str(parser_run.id),
                "status": parser_run.status,
                "candidate_count": parser_run.candidate_count,
                "field_candidate_count": parser_run.field_candidate_count,
            },
            comment="Automated extraction to staging only.",
        )
        await session.commit()
    except Exception as exc:
        parser_run.status = "failed"
        parser_run.errors_json = [str(exc)]
        parser_run.warnings_json = warnings
        parser_run.diagnostics_json = diagnostics
        parser_run.finished_at = datetime.now(UTC)
        await _record_audit(
            session,
            action="parser_report_extract_failed",
            entity_type="report",
            entity_id=report.id,
            diff_json={"parser_run_id": str(parser_run.id), "error": str(exc)},
            comment="Automated extraction failed.",
        )
        await session.commit()

    from app.services.ingestion import get_admin_report_detail

    return await get_admin_report_detail(session, report.id)


async def list_report_parser_runs(session: AsyncSession, report_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            select(ParserRunLog)
            .where(ParserRunLog.report_id == report_id)
            .order_by(ParserRunLog.created_at.desc())
        )
    ).scalars().all()
    items: list[dict] = []
    for row in rows:
        items.append(
            {
                "id": row.id,
                "report_id": row.report_id,
                "staging_report_id": row.staging_report_id,
                "status": row.status,
                "parser_version": row.parser_version,
                "source_label": row.source_label,
                "source_reference": row.source_reference,
                "source_checksum": row.source_checksum,
                "sections_found": row.sections_found,
                "candidate_count": row.candidate_count,
                "field_candidate_count": row.field_candidate_count,
                "address_candidate_count": row.address_candidate_count,
                "warnings": list(row.warnings_json or []),
                "errors": list(row.errors_json or []),
                "diagnostics": dict(row.diagnostics_json or {}),
                "started_at": row.started_at,
                "finished_at": row.finished_at,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )
    return items


async def get_parser_health_summary(session: AsyncSession) -> dict[str, Any]:
    total_runs = int((await session.execute(select(func.count()).select_from(ParserRunLog))).scalar_one())
    success_runs = int(
        (
            await session.execute(
                select(func.count()).select_from(ParserRunLog).where(ParserRunLog.status == "succeeded")
            )
        ).scalar_one()
    )
    failed_runs = int(
        (
            await session.execute(
                select(func.count()).select_from(ParserRunLog).where(ParserRunLog.status == "failed")
            )
        ).scalar_one()
    )
    warning_runs = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ParserRunLog)
                .where(func.jsonb_array_length(ParserRunLog.warnings_json) > 0)
            )
        ).scalar_one()
    )
    latest = (
        await session.execute(select(ParserRunLog).order_by(ParserRunLog.created_at.desc()).limit(5))
    ).scalars().all()
    return {
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "warning_runs": warning_runs,
        "recent_runs": [
            {
                "id": row.id,
                "report_id": row.report_id,
                "status": row.status,
                "candidate_count": row.candidate_count,
                "warnings_count": len(row.warnings_json or []),
                "errors_count": len(row.errors_json or []),
                "finished_at": row.finished_at,
            }
            for row in latest
        ],
    }
