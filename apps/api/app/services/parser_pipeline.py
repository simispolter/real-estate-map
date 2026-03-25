from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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
from app.services.document_conversion import convert_pdf_document
from app.services.extraction_profiles import (
    classify_section,
    infer_data_families,
    infer_candidate_disclosure_level,
    infer_candidate_lifecycle_stage,
)
from app.services.identity_ops import normalize_text, refresh_candidate_match_suggestions


PARSER_VERSION = "rule_parser_v2"
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
PROJECT_LABEL_HINTS = (
    "יח",
    'יח"ד',
    "דירות",
    "פרויקט",
    "project",
)
ROW_REJECT_REASON_ORDER = (
    "header_row",
    "footer_row",
    "prose_fragment",
    "date_fragment",
    "aggregate_total_row",
    "low_confidence_identity",
)
AGGREGATE_ROW_TOKENS = (
    'סה"כ',
    'סה״כ',
    "סהכ",
    "total",
    "subtotal",
    "grand total",
)
HEADER_ROW_TOKENS = (
    "project name",
    "project status",
    "location",
    "city",
    "units",
    "name of project",
    "שם הפרויקט",
    "מיקום הפרויקט",
    "עיר",
    'יח"ד',
    "דירות",
    "סטטוס",
    "שיעור",
    "רווח",
)
FOOTER_ROW_TOKENS = (
    "page ",
    "עמוד ",
    "ליום",
    "נכון ליום",
)
GENERIC_PROSE_TOKENS = (
    "בהתאם",
    "זכויות הבניה",
    "הקיימות או העתידיות",
    "עשויים להשתנות",
    "subject to",
    "management discussion",
)
SECTION_KIND_ROW_CUES: dict[str, tuple[str, ...]] = {
    "construction": ("construction", "בנייה", "ביצוע", "בהקמה", "שיווק"),
    "planning": ("planning", "permit", "תכנון", "היתר", "ייזום"),
    "completed": ("completed", "delivered", "אוכלס", "מאוכלס", "גמורות", "לא מכורות"),
    "land_reserve": ("land reserve", "land bank", "קרקע", "עתודת", "זכויות"),
    "urban_renewal": ("urban renewal", "פינוי בינוי", "התחדשות", "חתימות", "דיירים"),
    "material_project": ("material", "אשראי", "ליווי", "קובננט", "עודפים"),
}
PROJECT_LABEL_STOPWORDS = (
    "תוכן עניינים",
    "החברה",
    "הקבוצה",
    "דוח תקופתי",
    "דוח שנתי",
    "פרק ",
    "חלק ",
    "שעבודים",
    "התאמה",
    "אזהרה",
    "מידע צופה פני עתיד",
    "רווח",
    "הכנסות",
    "עלויות",
    "עלות",
    "שיעור",
    "אחוז",
    "מועד",
    "מלאי",
    "התחלת",
    "צפוי",
    "סך",
    "תמורה",
    "תזרים",
    "ביצוע",
    "שיווק התחלת",
    "שם הפרויקט",
    "מיקום הפרויקט",
    "הפרויקט בגין",
    "רווח גולמי",
    "עודפים",
    "שעבודים",
    "חלק התאגיד",
    "הפרויקט",
    "הפרויקטים",
    "לפרויקט",
    "בפרויקט",
    "מידע נוסף",
    "נתונים כלליים",
    "עתודות קרקע",
    "פרויקטים",
    "יח\"ד",
    "לפרטים נוספים",
    "ראו סעיף",
    "מהותי מאוד",
    "שווק ואוכלס",
    "בקשר",
    "ליווי",
    "כל של",
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
class SegmentedChunk:
    section_name: str
    raw_label: str | None
    source_page_from: int
    source_page_to: int
    text: str
    chunk_order: int
    overlap_flag: bool
    section_kind: str
    extraction_profile_key: str
    disclosure_level: str | None
    lifecycle_stage: str | None
    materiality_flag: bool


@dataclass
class AliasCandidate:
    project_id: UUID
    project_name: str
    city: str | None
    neighborhood: str | None
    aliases: list[str]
    addresses: list[str]


@dataclass(slots=True)
class CandidateDraft:
    candidate_name: str
    source_row_label: str
    source_table_name: str
    source_page: int
    source_section: str
    extraction_profile_key: str
    candidate_section_kind: str
    candidate_lifecycle_stage: str | None
    candidate_disclosure_level: str | None
    detected_data_families: list[str]
    city: str | None
    neighborhood: str | None
    project_status: str | None
    permit_status: str | None
    metrics: dict[str, tuple[str | None, Decimal | int | None, str]]
    matched_source: AliasCandidate | None
    confidence_level: str
    candidate_quality_score: Decimal
    family_confidence_score: Decimal
    review_notes: str | None


@dataclass(slots=True)
class SuppressedRow:
    raw_text: str
    source_page: int
    source_section: str
    source_table_name: str
    reason: str
    quality_score: Decimal


def _compact_line(value: str) -> str:
    return " ".join(value.replace("\u200f", " ").replace("\u200e", " ").split())


def _candidate_key(value: str) -> str:
    return normalize_text(value).strip()


def _project_label_from_line(line: str) -> str | None:
    compact = _compact_line(line).strip(" |-\t")
    if len(compact) < 4 or len(compact) > 120:
        return None

    normalized = normalize_text(compact)
    if any(stopword in normalized for stopword in PROJECT_LABEL_STOPWORDS):
        return None
    if re.match(r"^\(?\d+(?:\.\d+)+", compact):
        return None
    if sum(character.isdigit() for character in compact) > 8:
        return None
    if not any(hint in normalized for hint in PROJECT_LABEL_HINTS):
        return None
    if not (
        re.search(r"(?:^|[\s\-–])(?:פרויקט|project)\s+", compact, flags=re.IGNORECASE)
        or "|" in compact
        or re.match(r"^\(?\d+\)", compact)
    ):
        return None

    label = compact
    project_match = re.search(r"(?:^|[\s\-–])(?:פרויקט|project)\s+[\"'״]?([^|()]{3,80})", compact, flags=re.IGNORECASE)
    if project_match:
        label = project_match.group(1)
    elif re.match(r"^\(?\d+\)", compact):
        enumerated = re.sub(r"^\(?\d+\)\s*", "", compact)
        enumerated = enumerated.split(":", 1)[0]
        metric_split = re.split(r"\b\d{1,4}\s*(?:יח|יח\"ד|units?)\b", enumerated, maxsplit=1, flags=re.IGNORECASE)
        label = metric_split[0]
    elif "|" in compact:
        label = compact.split("|", 1)[0]
    else:
        metric_split = re.split(r"\b\d{1,4}\s*(?:יח|יח\"ד|units?)\b", compact, maxsplit=1, flags=re.IGNORECASE)
        label = metric_split[0]

    label = re.sub(r"\s+", " ", label).strip(" ,.|-–")
    label = re.sub(r"^\(?\d+\)?\s*[-.)]*\s*", "", label).strip(" ,.|-–")
    label = re.sub(r"^(?:שלב\s+[א-ת0-9'\"-]+\s*)+", "", label).strip(" ,.|-–")
    if len(label) < 3:
        return None
    if label.isdigit():
        return None

    label_normalized = normalize_text(label)
    if any(stopword in label_normalized for stopword in PROJECT_LABEL_STOPWORDS):
        return None
    word_count = len([word for word in label.split(" ") if word])
    if word_count < 1 or word_count > 7:
        return None
    if sum(character.isdigit() for character in label) > 4:
        return None
    if label_normalized in {"פרויקט", "project", "שיווק", "מלאי", "רווח"}:
        return None
    return label


def _extract_project_labels(section_text: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for line in section_text.splitlines():
        label = _project_label_from_line(line)
        if not label:
            continue
        key = _candidate_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return labels


def _best_existing_match(label: str, candidate_sources: list[AliasCandidate]) -> AliasCandidate | None:
    label_key = _candidate_key(label)
    if not label_key:
        return None

    best: tuple[int, AliasCandidate] | None = None
    for source in candidate_sources:
        for alias in source.aliases:
            alias_key = _candidate_key(alias)
            if not alias_key:
                continue
            score = 0
            if alias_key == label_key:
                score = 3
            elif alias_key in label_key or label_key in alias_key:
                score = 2
            elif alias_key.replace(" ", "") in label_key.replace(" ", ""):
                score = 1
            if score == 0:
                continue
            if best is None or score > best[0]:
                best = (score, source)
    return best[1] if best else None


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
            diff_json=jsonable_encoder(diff_json) if diff_json is not None else None,
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
    converted = convert_pdf_document(pdf_bytes, backend="pypdf", ocr_mode="off")
    return converted.page_texts


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


def segment_report_chunks(pages: list[str]) -> list[SegmentedChunk]:
    sections = _segment_sections(pages)
    chunks: list[SegmentedChunk] = []
    pending: SegmentedChunk | None = None

    for section in sections:
        classification = classify_section(section.section_name, section.raw_label, _excerpt(section.text))
        current = SegmentedChunk(
            section_name=section.section_name,
            raw_label=section.raw_label,
            source_page_from=section.source_page_from,
            source_page_to=section.source_page_to,
            text=section.text,
            chunk_order=0,
            overlap_flag=False,
            section_kind=classification.section_kind,
            extraction_profile_key=classification.extraction_profile_key,
            disclosure_level=classification.disclosure_level,
            lifecycle_stage=classification.lifecycle_stage,
            materiality_flag=classification.materiality_flag,
        )
        if pending is None:
            pending = current
            continue

        should_merge = (
            pending.section_kind == current.section_kind
            and pending.section_kind != "summary_only"
            and current.source_page_from == pending.source_page_to + 1
            and (
                normalize_text(pending.section_name) == normalize_text(current.section_name)
                or normalize_text(pending.raw_label or "") == normalize_text(current.raw_label or "")
                or (
                    pending.extraction_profile_key == current.extraction_profile_key
                    and pending.source_page_to == current.source_page_from - 1
                )
            )
        )
        if should_merge:
            pending.source_page_to = current.source_page_to
            pending.text = f"{pending.text}\n{current.text}".strip()
            continue

        chunks.append(pending)
        pending = current

    if pending is not None:
        chunks.append(pending)

    for order, chunk in enumerate(chunks, start=1):
        chunk.chunk_order = order
    return chunks


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


def _is_date_fragment(value: str) -> bool:
    compact = value.strip()
    normalized = normalize_text(compact)
    if re.fullmatch(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", compact):
        return True
    if re.fullmatch(r"\d{4}", compact):
        return True
    return normalized in {"ליום", "נכון ליום", "as of"}


def _is_aggregate_total_row(value: str) -> bool:
    normalized = normalize_text(value)
    return any(normalize_text(token) in normalized for token in AGGREGATE_ROW_TOKENS)


def _header_token_hits(value: str) -> int:
    normalized = normalize_text(value)
    return sum(1 for token in HEADER_ROW_TOKENS if normalize_text(token) in normalized)


def _is_footer_or_page_row(value: str) -> bool:
    normalized = normalize_text(value)
    if any(normalize_text(token) in normalized for token in FOOTER_ROW_TOKENS):
        return True
    return bool(re.fullmatch(r"(?:page|עמוד)\s+\d+", normalized))


def _row_metric_marker_count(value: str) -> int:
    normalized = normalize_text(value)
    markers = 0
    if re.search(r"\b\d{1,4}\s*(?:יח|יח\"ד|דירות|units?)\b", normalized, flags=re.IGNORECASE):
        markers += 1
    if "%" in value:
        markers += 1
    if re.search(r"\b(?:sqm|מ\"ר|מחיר|margin|revenue|cost)\b", normalized, flags=re.IGNORECASE):
        markers += 1
    if value.count("|") >= 2:
        markers += 1
    return markers


def _looks_like_prose_fragment(value: str) -> bool:
    compact = _compact_line(value)
    normalized = normalize_text(compact)
    if any(normalize_text(token) in normalized for token in GENERIC_PROSE_TOKENS):
        return True
    word_count = len([word for word in compact.split(" ") if word])
    return word_count >= 9 and "|" not in compact and _row_metric_marker_count(compact) == 0


def _clean_candidate_label(value: str) -> str:
    label = _compact_line(value)
    label = re.sub(r"^\(?\d+\)?\s*[-.)]*\s*", "", label)
    label = re.sub(r"^(?:שלב\s+[א-ת0-9'\"-]+\s*)+", "", label)
    label = re.split(r"\b\d{1,4}\s*(?:יח|יח\"ד|דירות|units?)\b", label, maxsplit=1, flags=re.IGNORECASE)[0]
    label = re.split(r"\b(?:gross margin|margin|מחיר ממוצע|רווח גולמי|עלות|שיעור)\b", label, maxsplit=1, flags=re.IGNORECASE)[0]
    label = re.split(
        r"\b(?:להקמת|שיכללו|הכוללים|בש(?:טח|יעור)|המהווה|מעל|מימון|הלוואה|מסחרי|נמכרו|חתומים|לא צמודה|prime|cost)\b",
        label,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    label = label.split("|", 1)[0]
    label = label.split(":", 1)[0]
    label = re.sub(r"\s+", " ", label).strip(" ,.|-–")
    return label


def _project_label_from_line(
    line: str,
    *,
    section_kind: str | None = None,
    known_cities: list[str] | None = None,
) -> str | None:
    compact = _compact_line(line).strip(" |-\t")
    if len(compact) < 2 or len(compact) > 160:
        return None
    if _is_date_fragment(compact) or _is_aggregate_total_row(compact) or _is_footer_or_page_row(compact):
        return None
    if _header_token_hits(compact) >= 2:
        return None
    if _looks_like_prose_fragment(compact):
        return None

    normalized = normalize_text(compact)
    label: str | None = None
    if re.search(r"(?:^|[\s\-–])(?:פרויקט|project)\s+", compact, flags=re.IGNORECASE):
        project_match = re.search(
            r"(?:^|[\s\-–])(?:פרויקט|project)\s+[\"'״]?([^|()]{3,100})",
            compact,
            flags=re.IGNORECASE,
        )
        if project_match:
            label = project_match.group(1)
    elif "|" in compact or re.match(r"^\(?\d+\)", compact) or _row_metric_marker_count(compact) > 0:
        label = _clean_candidate_label(compact)
    else:
        fallback = _clean_candidate_label(compact)
        fallback_key = _candidate_key(fallback)
        if known_cities and any(_candidate_key(city) == fallback_key for city in known_cities):
            label = fallback

    if not label:
        return None

    label = _clean_candidate_label(label)
    if len(label) < 2 or label.isdigit():
        return None
    label_normalized = normalize_text(label)
    if any(stopword in label_normalized for stopword in PROJECT_LABEL_STOPWORDS):
        return None
    if any(
        token in label_normalized
        for token in ("מחיר", "עלות", "יתרת", "סכומים", "הלוואה", "מימון", "מסחרי", "מכור", "שוק", "פריים")
    ):
        return None
    if label_normalized in {"פרויקט", "project", "שיווק", "מלאי", "רווח", "מכירה"}:
        return None
    if re.match(r"^[\d%(/-]", label):
        return None
    word_count = len([word for word in label.split(" ") if word])
    if word_count < 1 or word_count > 8:
        return None
    if sum(character.isdigit() for character in label) > 6:
        return None
    if not re.search(r"[A-Za-zא-ת]", label):
        return None
    return label


def _should_merge_row_lines(current_line: str, next_line: str) -> bool:
    current = _compact_line(current_line)
    following = _compact_line(next_line)
    if not current or not following:
        return False
    if (
        _is_date_fragment(current)
        or _is_aggregate_total_row(current)
        or _is_footer_or_page_row(current)
        or _header_token_hits(current) >= 2
    ):
        return False
    if _is_aggregate_total_row(following) or _is_footer_or_page_row(following) or _header_token_hits(following) >= 2:
        return False
    if current.endswith(("-", "–", "/", ",")):
        return True
    current_markers = _row_metric_marker_count(current)
    next_markers = _row_metric_marker_count(following)
    if current_markers == 0 and next_markers > 0:
        return True
    if len(current.split()) <= 4 and len(following.split()) <= 6 and next_markers > 0:
        return True
    if current_markers == 0 and next_markers == 0 and len(current.split()) <= 3 and len(following.split()) <= 3:
        return True
    return False


def _iter_grouped_section_rows(section_text: str) -> list[str]:
    raw_lines = [_compact_line(line) for line in section_text.splitlines() if _compact_line(line)]
    rows: list[str] = []
    index = 0
    while index < len(raw_lines):
        current = raw_lines[index]
        while index + 1 < len(raw_lines) and _should_merge_row_lines(current, raw_lines[index + 1]):
            current = f"{current} {raw_lines[index + 1]}"
            index += 1
        rows.append(current)
        index += 1
    return rows


def _row_quality_score(
    row_text: str,
    *,
    label: str | None,
    section_kind: str | None,
    known_cities: list[str],
    matched_source: AliasCandidate | None,
) -> tuple[Decimal, str | None]:
    score = Decimal("0.10")
    normalized = normalize_text(row_text)
    if matched_source is not None:
        score += Decimal("0.28")
    if label:
        score += Decimal("0.28")
    if _row_metric_marker_count(row_text) > 0:
        score += Decimal("0.18")
    if any(_candidate_key(city) in normalized for city in known_cities):
        score += Decimal("0.14")
    if section_kind and section_kind != "summary_only":
        score += Decimal("0.08")
    if section_kind and any(normalize_text(token) in normalized for token in SECTION_KIND_ROW_CUES.get(section_kind, ())):
        score += Decimal("0.10")

    if _is_date_fragment(row_text):
        return Decimal("0.00"), "date_fragment"
    if _is_aggregate_total_row(row_text):
        return Decimal("0.00"), "aggregate_total_row"
    if _is_footer_or_page_row(row_text):
        return Decimal("0.00"), "footer_row"
    if _header_token_hits(row_text) >= 2:
        return Decimal("0.00"), "header_row"
    if _looks_like_prose_fragment(row_text):
        return Decimal("0.10"), "prose_fragment"
    if not label:
        return min(score, Decimal("0.35")), "low_confidence_identity"

    return min(score, Decimal("0.99")), None


def _family_confidence_score(
    *,
    section_kind: str | None,
    section_confidence_score: float,
    row_text: str,
    lifecycle_stage: str | None,
    disclosure_level: str | None,
    metrics: dict[str, tuple[str | None, Decimal | int | None, str]],
) -> Decimal:
    score = Decimal(str(round(section_confidence_score or 0.0, 4)))
    normalized = normalize_text(row_text)
    if lifecycle_stage:
        score += Decimal("0.18")
    if disclosure_level:
        score += Decimal("0.12")
    if section_kind and any(normalize_text(token) in normalized for token in SECTION_KIND_ROW_CUES.get(section_kind, ())):
        score += Decimal("0.16")
    if section_kind == "completed" and _safe_int(metrics["unsold_units"][1]) is not None:
        score += Decimal("0.08")
    if section_kind == "construction" and any(
        _safe_int(metrics[field_name][1]) is not None
        for field_name in ("marketed_units", "sold_units_cumulative", "unsold_units")
    ):
        score += Decimal("0.08")
    if section_kind == "planning" and _safe_int(metrics["total_units"][1]) is not None:
        score += Decimal("0.05")
    return min(score, Decimal("0.99"))


def _extract_project_labels(
    section_text: str,
    *,
    section_kind: str | None = None,
    known_cities: list[str] | None = None,
) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for row_text in _iter_grouped_section_rows(section_text):
        label = _project_label_from_line(
            row_text,
            section_kind=section_kind,
            known_cities=known_cities or [],
        )
        if not label:
            continue
        key = _candidate_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return labels


def _candidate_confidence(alias: str, canonical_name: str) -> str:
    alias_key = normalize_text(alias)
    canonical_key = normalize_text(canonical_name)
    if alias_key == canonical_key:
        return "high"
    if canonical_key and alias_key and (alias_key in canonical_key or canonical_key in alias_key):
        return "medium"
    return "low"


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


def _extract_trailing_project_label(value: str) -> str | None:
    compact = _compact_line(value)
    if sum(character.isdigit() for character in compact) < 10:
        return None

    trailing_after_market = re.search(
        r"(?:חופשי\s+שוק|שוק\s+חופשי|מחיר\s+למשתכן|דירה\s+להשכיר|להשכרה|שכירות)\s+(.+)$",
        compact,
        flags=re.IGNORECASE,
    )
    if trailing_after_market:
        candidate = _clean_candidate_label(trailing_after_market.group(1))
        if re.search(r"[A-Za-z\u0590-\u05FF]", candidate):
            return candidate

    trailing_words = re.search(r"([A-Za-z\u0590-\u05FF\"'()\-/, ]{6,})$", compact)
    if not trailing_words:
        return None

    candidate = _clean_candidate_label(trailing_words.group(1))
    word_count = len(candidate.split())
    if word_count < 1 or word_count > 6:
        return None
    if not re.search(r"[A-Za-z\u0590-\u05FF]", candidate):
        return None
    return candidate


def _project_label_from_line(
    line: str,
    *,
    section_kind: str | None = None,
    known_cities: list[str] | None = None,
) -> str | None:
    compact = _compact_line(line).strip(" |-\t")
    if len(compact) < 2 or len(compact) > 160:
        return None
    if _is_date_fragment(compact) or _is_aggregate_total_row(compact) or _is_footer_or_page_row(compact):
        return None
    if _header_token_hits(compact) >= 2:
        return None
    if _looks_like_prose_fragment(compact):
        return None

    normalized = normalize_text(compact)
    label: str | None = _extract_trailing_project_label(compact)
    if re.search(r"(?:^|[\s\-â€“])(?:×¤×¨×•×™×§×˜|project)\s+", compact, flags=re.IGNORECASE):
        project_match = re.search(
            r"(?:^|[\s\-â€“])(?:×¤×¨×•×™×§×˜|project)\s+[\"'×´]?([^|()]{3,100})",
            compact,
            flags=re.IGNORECASE,
        )
        if project_match:
            label = project_match.group(1)
    elif not label and ("|" in compact or re.match(r"^\(?\d+\)", compact) or _row_metric_marker_count(compact) > 0):
        label = _clean_candidate_label(compact)
    elif not label:
        fallback = _clean_candidate_label(compact)
        fallback_key = _candidate_key(fallback)
        if known_cities and any(_candidate_key(city) == fallback_key for city in known_cities):
            label = fallback

    if not label:
        return None

    label = _clean_candidate_label(label)
    if len(label) < 2 or label.isdigit():
        return None
    label_normalized = normalize_text(label)
    if any(stopword in label_normalized for stopword in PROJECT_LABEL_STOPWORDS):
        return None
    if any(
        token in label_normalized
        for token in ("×ž×—×™×¨", "×¢×œ×•×ª", "×™×ª×¨×ª", "×¡×›×•×ž×™×", "×”×œ×•×•××”", "×ž×™×ž×•×Ÿ", "×ž×¡×—×¨×™", "×ž×›×•×¨", "×©×•×§", "×¤×¨×™×™×")
    ):
        return None
    if label_normalized in {"×¤×¨×•×™×§×˜", "project", "×©×™×•×•×§", "×ž×œ××™", "×¨×•×•×—", "×ž×›×™×¨×”"}:
        return None
    if re.match(r"^[\d%(/-]", label):
        return None
    word_count = len([word for word in label.split(" ") if word])
    if word_count < 1 or word_count > 8:
        return None
    if sum(character.isdigit() for character in label) > 6:
        return None
    if not re.search(r"[A-Za-z\u0590-\u05FF]", label):
        return None
    if section_kind in {"construction", "planning", "completed", "land_reserve"} and _row_metric_marker_count(compact) > 1:
        return label
    if re.search(r"(?:^|[\s\-â€“])(?:×¤×¨×•×™×§×˜|project)\s+", compact, flags=re.IGNORECASE):
        return label
    if known_cities and any(_candidate_key(city) == _candidate_key(label) for city in known_cities):
        return label
    if "-" in label or "'" in label or '"' in label:
        return label
    return label if len(label.split()) >= 2 else None

def _project_label_from_line(
    line: str,
    *,
    section_kind: str | None = None,
    known_cities: list[str] | None = None,
) -> str | None:
    compact = _compact_line(line).strip(" |-\t")
    if len(compact) < 2 or len(compact) > 160:
        return None
    if _is_date_fragment(compact) or _is_aggregate_total_row(compact) or _is_footer_or_page_row(compact):
        return None
    if _header_token_hits(compact) >= 2:
        return None
    if _looks_like_prose_fragment(compact):
        return None

    label: str | None = _extract_trailing_project_label(compact)
    if re.search(r"(?:^|[\s\-–])(?:פרויקט|project)\s+", compact, flags=re.IGNORECASE):
        project_match = re.search(
            r"(?:^|[\s\-–])(?:פרויקט|project)\s+[\"'׳]?\s*([^|()]{2,100})",
            compact,
            flags=re.IGNORECASE,
        )
        if project_match:
            label = project_match.group(1)
    elif not label and ("|" in compact or re.match(r"^\(?\d+\)", compact) or _row_metric_marker_count(compact) > 0):
        label = _clean_candidate_label(compact)
    elif not label:
        fallback = _clean_candidate_label(compact)
        fallback_key = _candidate_key(fallback)
        if known_cities and any(_candidate_key(city) == fallback_key for city in known_cities):
            label = fallback

    if not label:
        return None

    label = _clean_candidate_label(label)
    if len(label) < 2 or label.isdigit():
        return None
    label_normalized = normalize_text(label)
    if any(stopword in label_normalized for stopword in PROJECT_LABEL_STOPWORDS):
        return None
    if any(token in label_normalized for token in ("מחיר", "עלות", "יתרת", "סכומים", "הלוואה", "מימון", "מסחרי")):
        return None
    if label_normalized in {"פרויקט", "project", "שיווק", "מלאי", "רווח", "מכירה", "חופשי שוק"}:
        return None
    if re.match(r"^[\d%(/-]", label):
        return None
    word_count = len([word for word in label.split(" ") if word])
    if word_count < 1 or word_count > 8:
        return None
    if sum(character.isdigit() for character in label) > 6:
        return None
    if not re.search(r"[A-Za-z\u0590-\u05FF]", label):
        return None
    if section_kind in {"construction", "planning", "completed", "land_reserve"} and _row_metric_marker_count(compact) > 1:
        return label
    if re.search(r"(?:^|[\s\-–])(?:פרויקט|project)\s+", compact, flags=re.IGNORECASE):
        return label
    if known_cities and any(_candidate_key(city) == _candidate_key(label) for city in known_cities):
        return label
    if "-" in label or "'" in label or '"' in label:
        return label
    if section_kind in {"construction", "planning", "completed", "land_reserve"} and _row_metric_marker_count(compact) > 0 and len(label) >= 3:
        return label
    return label if len(label.split()) >= 2 else None


def _project_label_from_line_high_recall(
    line: str,
    *,
    section_kind: str | None = None,
    known_cities: list[str] | None = None,
) -> str | None:
    return _project_label_from_line(line, section_kind=section_kind, known_cities=known_cities)


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


def _resolve_conversion_backend(backend: str | None) -> tuple[str, str]:
    settings = get_settings()
    selected_backend = (backend or settings.document_conversion_backend or "pypdf").strip().lower()
    selected_ocr_mode = (settings.document_conversion_ocr_mode or "off").strip().lower()
    if selected_backend == "docling":
        return selected_backend, "off"
    if selected_backend == "docling_ocr":
        return selected_backend, selected_ocr_mode if selected_ocr_mode != "off" else "auto"
    return selected_backend, "off"


def _build_candidate_drafts(
    *,
    sections: list[ExtractedSection],
    persisted_sections: list[StagingSection],
    candidate_sources: list[AliasCandidate],
    known_cities: list[str],
) -> tuple[list[CandidateDraft], list[SuppressedRow], dict[str, Any]]:
    drafts: list[CandidateDraft] = []
    suppressed_rows: list[SuppressedRow] = []
    seen_candidate_keys: set[str] = set()
    ambiguous_count = 0

    for section_row, section in zip(persisted_sections, sections, strict=False):
        if section_row.section_kind == "summary_only":
            continue

        section_classification = classify_section(
            section.section_name,
            section.raw_label,
            _excerpt(section.text),
        )
        for row_text in _iter_grouped_section_rows(section.text):
            matched_source = _best_existing_match(row_text, candidate_sources)
            label = _project_label_from_line(
                row_text,
                section_kind=section_row.section_kind,
                known_cities=known_cities,
            )
            quality_score, reject_reason = _row_quality_score(
                row_text,
                label=label,
                section_kind=section_row.section_kind,
                known_cities=known_cities,
                matched_source=matched_source,
            )
            if reject_reason is not None and quality_score < Decimal("0.56"):
                suppressed_rows.append(
                    SuppressedRow(
                        raw_text=row_text,
                        source_page=section_row.source_page_from or 0,
                        source_section=section_row.section_name,
                        source_table_name=section_row.raw_label or section_row.section_name,
                        reason=reject_reason,
                        quality_score=quality_score,
                    )
                )
                continue

            candidate_name = label or _clean_candidate_label(row_text)
            candidate_key = _candidate_key(candidate_name)
            if not candidate_key or candidate_key in seen_candidate_keys:
                continue

            context = _context_window(section.text, candidate_name)
            city, city_origin = _detect_city(context, known_cities, matched_source.city if matched_source else None)
            if city is None and any(_candidate_key(known_city) == candidate_key for known_city in known_cities):
                city = next((known_city for known_city in known_cities if _candidate_key(known_city) == candidate_key), None)
                city_origin = "reported" if city else "unknown"
            neighborhood, neighborhood_origin = _detect_neighborhood(
                context,
                matched_source.neighborhood if matched_source else None,
            )
            project_status, _ = _extract_status(context, "project_status")
            permit_status, _ = _extract_status(context, "permit_status")
            metrics: dict[str, tuple[str | None, Decimal | int | None, str]] = {}
            for field_name in METRIC_PATTERNS:
                metrics[field_name] = _extract_metric(context, field_name)

            candidate_lifecycle_stage = infer_candidate_lifecycle_stage(
                section_kind=section_row.section_kind,
                project_status=project_status,
                project_business_type=None,
                permit_status=permit_status,
            )
            candidate_disclosure_level = infer_candidate_disclosure_level(
                section_kind=section_row.section_kind,
                extraction_profile_key=section_row.extraction_profile_key,
                total_units=_safe_int(metrics["total_units"][1]),
                marketed_units=_safe_int(metrics["marketed_units"][1]),
                sold_units_cumulative=_safe_int(metrics["sold_units_cumulative"][1]),
                gross_margin_expected_pct=_safe_decimal(metrics["gross_margin_expected_pct"][1]),
            )
            detected_data_families = infer_data_families(
                lifecycle_stage=candidate_lifecycle_stage,
                disclosure_level=candidate_disclosure_level,
                section_kind=section_row.section_kind,
                project_business_type=None,
                metric_presence={
                    "has_sales_metrics": any(
                        _safe_int(metrics[field_name][1]) is not None
                        for field_name in ("marketed_units", "sold_units_cumulative", "unsold_units")
                    ),
                    "has_financing_fields": any(
                        _safe_decimal(metrics[field_name][1]) is not None
                        for field_name in ("gross_margin_expected_pct", "avg_price_per_sqm_cumulative")
                    ),
                    "has_completed_inventory_fields": section_row.section_kind == "completed"
                    and _safe_int(metrics["unsold_units"][1]) is not None,
                },
            )
            family_confidence_score = _family_confidence_score(
                section_kind=section_row.section_kind,
                section_confidence_score=section_classification.confidence_score,
                row_text=row_text,
                lifecycle_stage=candidate_lifecycle_stage,
                disclosure_level=candidate_disclosure_level,
                metrics=metrics,
            )
            confidence_level = (
                _candidate_confidence(candidate_name, matched_source.project_name)
                if matched_source
                else ("high" if quality_score >= Decimal("0.84") else "medium" if quality_score >= Decimal("0.68") else "low")
            )
            matching_status = "matched_existing_project" if matched_source else "unmatched"
            review_note = "Parser-created candidate. Human review required before publish."
            if matched_source is None and quality_score < Decimal("0.78"):
                matching_status = "ambiguous_match"
                review_note = "Parser-created candidate with ambiguous identity. Human review required before publish."
                ambiguous_count += 1

            drafts.append(
                CandidateDraft(
                    candidate_name=candidate_name,
                    source_row_label=row_text,
                    source_table_name=section_row.raw_label or section_row.section_name,
                    source_page=section_row.source_page_from or 0,
                    source_section=section_row.section_name,
                    extraction_profile_key=section_row.extraction_profile_key or "unknown",
                    candidate_section_kind=section_row.section_kind or "summary_only",
                    candidate_lifecycle_stage=candidate_lifecycle_stage,
                    candidate_disclosure_level=candidate_disclosure_level,
                    detected_data_families=detected_data_families,
                    city=city,
                    neighborhood=neighborhood,
                    project_status=project_status,
                    permit_status=permit_status,
                    metrics=metrics,
                    matched_source=matched_source,
                    confidence_level=confidence_level,
                    candidate_quality_score=quality_score,
                    family_confidence_score=family_confidence_score,
                    review_notes=review_note,
                )
            )
            seen_candidate_keys.add(candidate_key)

    suppressed_counts = dict(Counter(row.reason for row in suppressed_rows))
    noisy_sections = Counter(row.source_section for row in suppressed_rows)
    return drafts, suppressed_rows, {
        "suppressed_row_counts": suppressed_counts,
        "suppressed_row_total": len(suppressed_rows),
        "ambiguous_candidate_count": ambiguous_count,
        "noisy_sections": [
            {"section_name": key, "count": count}
            for key, count in noisy_sections.most_common(5)
        ],
    }


async def run_report_extraction(
    session: AsyncSession,
    report_id: UUID,
    *,
    conversion_backend: str | None = None,
) -> dict | None:
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
        selected_backend, selected_ocr_mode = _resolve_conversion_backend(conversion_backend)
        converted_document = convert_pdf_document(
            pdf_bytes,
            backend=selected_backend,
            ocr_mode=selected_ocr_mode,
        )
        pages = converted_document.page_texts
        if not any(page.strip() for page in pages):
            warnings.append("PDF text extraction returned empty content. OCR is intentionally out of scope for this phase.")

        await _clear_previous_parser_output(session, staging_report.id)
        chunks = segment_report_chunks(pages)
        parser_run.sections_found = len(chunks)
        diagnostics["page_count"] = len(pages)
        diagnostics["chunk_count"] = len(chunks)
        diagnostics["text_characters"] = sum(len(page) for page in pages)
        diagnostics["conversion_backend"] = converted_document.backend
        diagnostics["conversion_ocr_mode"] = converted_document.ocr_mode
        diagnostics["conversion_table_count"] = converted_document.table_count
        diagnostics["conversion_backend_diagnostics"] = converted_document.diagnostics

        persisted_sections: list[StagingSection] = []
        for chunk in chunks:
            row = StagingSection(
                id=uuid4(),
                staging_report_id=staging_report.id,
                parser_run_id=parser_run.id,
                section_name=chunk.section_name,
                section_kind=chunk.section_kind,
                raw_label=chunk.raw_label,
                extraction_profile_key=chunk.extraction_profile_key,
                source_page_from=chunk.source_page_from,
                source_page_to=chunk.source_page_to,
                notes=_excerpt(
                    f"chunk_order={chunk.chunk_order}; overlap={chunk.overlap_flag}; "
                    f"disclosure={chunk.disclosure_level}; lifecycle={chunk.lifecycle_stage}\n{chunk.text}"
                ),
            )
            session.add(row)
            persisted_sections.append(row)
        await session.flush()

        candidate_sources = await _company_alias_candidates(session, report.company_id)
        known_cities = await _known_city_lexicon(session)
        candidate_rows: list[StagingProjectCandidate] = []
        field_count = 0
        pass1_sections = [
            ExtractedSection(
                section_name=chunk.section_name,
                raw_label=chunk.raw_label,
                source_page_from=chunk.source_page_from,
                source_page_to=chunk.source_page_to,
                text=chunk.text,
            )
            for chunk in chunks
        ]
        _, suppressed_rows, quality_diagnostics = _build_candidate_drafts(
            sections=pass1_sections,
            persisted_sections=persisted_sections,
            candidate_sources=candidate_sources,
            known_cities=known_cities,
        )
        seen_candidate_keys: set[str] = set()

        for source in candidate_sources:
            section_hit: tuple[StagingSection, str, str] | None = None
            for section_row, section in zip(persisted_sections, pass1_sections, strict=False):
                section_norm = normalize_text(section.text)
                for alias in sorted(set(source.aliases), key=len, reverse=True):
                    alias_norm = normalize_text(alias)
                    if alias_norm and alias_norm in section_norm:
                        section_hit = (section_row, section.text, alias)
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
            candidate_lifecycle_stage = infer_candidate_lifecycle_stage(
                section_kind=section_row.section_kind,
                project_status=project_status,
                project_business_type=None,
                permit_status=permit_status,
            )
            candidate_disclosure_level = infer_candidate_disclosure_level(
                section_kind=section_row.section_kind,
                extraction_profile_key=section_row.extraction_profile_key,
                total_units=_safe_int(metrics["total_units"][1]),
                marketed_units=_safe_int(metrics["marketed_units"][1]),
                sold_units_cumulative=_safe_int(metrics["sold_units_cumulative"][1]),
                gross_margin_expected_pct=_safe_decimal(metrics["gross_margin_expected_pct"][1]),
            )
            detected_data_families = infer_data_families(
                lifecycle_stage=candidate_lifecycle_stage,
                disclosure_level=candidate_disclosure_level,
                section_kind=section_row.section_kind,
                project_business_type=None,
                metric_presence={
                    "has_sales_metrics": any(
                        _safe_int(metrics[field_name][1]) is not None
                        for field_name in ("marketed_units", "sold_units_cumulative", "unsold_units")
                    ),
                    "has_financing_fields": any(
                        _safe_decimal(metrics[field_name][1]) is not None
                        for field_name in ("gross_margin_expected_pct", "avg_price_per_sqm_cumulative")
                    ),
                },
            )

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
                candidate_lifecycle_stage=candidate_lifecycle_stage,
                candidate_disclosure_level=candidate_disclosure_level,
                candidate_section_kind=section_row.section_kind,
                candidate_materiality_flag=section_row.section_kind == "material_project",
                source_table_name=section_row.raw_label or section_row.section_name,
                source_row_label=matched_alias,
                extraction_profile_key=section_row.extraction_profile_key,
                detected_data_families=detected_data_families,
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
                confidence_level=_candidate_confidence(matched_alias, source.project_name),
                candidate_quality_score=Decimal("0.92"),
                family_confidence_score=_family_confidence_score(
                    section_kind=section_row.section_kind,
                    section_confidence_score=classify_section(section_row.section_name, section_row.raw_label, section_text[:500]).confidence_score,
                    row_text=context,
                    lifecycle_stage=candidate_lifecycle_stage,
                    disclosure_level=candidate_disclosure_level,
                    metrics=metrics,
                ),
                matching_status="matched_existing_project",
                publish_status="draft",
                review_status="pending",
                review_notes="Parser-created candidate. Human review required before publish.",
            )
            session.add(candidate)
            candidate_rows.append(candidate)
            seen_candidate_keys.add(_candidate_key(candidate.candidate_project_name))
            await session.flush()

            fields_to_insert: list[tuple[str, str | None, str | None, str, str]] = [
                ("canonical_name", matched_alias, source.project_name, "reported", candidate.confidence_level)
            ]
            if city:
                fields_to_insert.append(("city", city, city, city_origin, "high" if city_origin == "reported" else "medium"))
            if neighborhood:
                fields_to_insert.append(("neighborhood", neighborhood, neighborhood, neighborhood_origin, "medium"))
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
                        source_table_name=section_row.raw_label or section_row.section_name,
                        source_row_label=matched_alias,
                        extraction_profile_key=section_row.extraction_profile_key,
                        value_origin_type=origin if origin in {"reported", "inferred"} else "unknown",
                        confidence_level=field_confidence,
                        review_status="pending",
                        review_notes="Parser-created field candidate. Review before publish.",
                    )
                )
                field_count += 1

            await refresh_candidate_match_suggestions(session, candidate)
            await _sync_report_queue(session, report.id, candidate.id, "open", "Parser-created candidate awaiting review")

        for section_row, section in zip(persisted_sections, pass1_sections, strict=False):
            if section_row.section_kind == "summary_only":
                continue

            for extracted_label in _extract_project_labels(
                section.text,
                section_kind=section_row.section_kind,
                known_cities=known_cities,
            ):
                label_key = _candidate_key(extracted_label)
                if not label_key or label_key in seen_candidate_keys:
                    continue

                matched_source = _best_existing_match(extracted_label, candidate_sources)
                context = _context_window(section.text, extracted_label)
                city, city_origin = _detect_city(context, known_cities, matched_source.city if matched_source else None)
                neighborhood, neighborhood_origin = _detect_neighborhood(
                    context,
                    matched_source.neighborhood if matched_source else None,
                )
                project_status, project_status_origin = _extract_status(context, "project_status")
                permit_status, permit_status_origin = _extract_status(context, "permit_status")
                metrics: dict[str, tuple[str | None, Decimal | int | None, str]] = {}
                for field_name in METRIC_PATTERNS:
                    metrics[field_name] = _extract_metric(context, field_name)

                candidate_lifecycle_stage = infer_candidate_lifecycle_stage(
                    section_kind=section_row.section_kind,
                    project_status=project_status,
                    project_business_type=None,
                    permit_status=permit_status,
                )
                candidate_disclosure_level = infer_candidate_disclosure_level(
                    section_kind=section_row.section_kind,
                    extraction_profile_key=section_row.extraction_profile_key,
                    total_units=_safe_int(metrics["total_units"][1]),
                    marketed_units=_safe_int(metrics["marketed_units"][1]),
                    sold_units_cumulative=_safe_int(metrics["sold_units_cumulative"][1]),
                    gross_margin_expected_pct=_safe_decimal(metrics["gross_margin_expected_pct"][1]),
                )
                detected_data_families = infer_data_families(
                    lifecycle_stage=candidate_lifecycle_stage,
                    disclosure_level=candidate_disclosure_level,
                    section_kind=section_row.section_kind,
                    project_business_type=None,
                    metric_presence={
                        "has_sales_metrics": any(
                            _safe_int(metrics[field_name][1]) is not None
                            for field_name in ("marketed_units", "sold_units_cumulative", "unsold_units")
                        ),
                        "has_financing_fields": any(
                            _safe_decimal(metrics[field_name][1]) is not None
                            for field_name in ("gross_margin_expected_pct", "avg_price_per_sqm_cumulative")
                        ),
                    },
                )
                confidence_level = _candidate_confidence(extracted_label, matched_source.project_name) if matched_source else "medium"
                candidate = StagingProjectCandidate(
                    id=uuid4(),
                    staging_report_id=staging_report.id,
                    parser_run_id=parser_run.id,
                    company_id=report.company_id,
                    staging_section_id=section_row.id,
                    matched_project_id=matched_source.project_id if matched_source else None,
                    candidate_project_name=extracted_label,
                    city=city,
                    neighborhood=neighborhood,
                    candidate_lifecycle_stage=candidate_lifecycle_stage,
                    candidate_disclosure_level=candidate_disclosure_level,
                    candidate_section_kind=section_row.section_kind,
                    candidate_materiality_flag=section_row.section_kind == "material_project",
                    source_table_name=section_row.raw_label or section_row.section_name,
                    source_row_label=extracted_label,
                    extraction_profile_key=section_row.extraction_profile_key,
                    detected_data_families=detected_data_families,
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
                    candidate_quality_score=Decimal("0.84") if matched_source else Decimal("0.74"),
                    family_confidence_score=_family_confidence_score(
                        section_kind=section_row.section_kind,
                        section_confidence_score=classify_section(section_row.section_name, section_row.raw_label, section.text[:500]).confidence_score,
                        row_text=context,
                        lifecycle_stage=candidate_lifecycle_stage,
                        disclosure_level=candidate_disclosure_level,
                        metrics=metrics,
                    ),
                    matching_status="matched_existing_project" if matched_source else "unmatched",
                    publish_status="draft",
                    review_status="pending",
                    review_notes="Parser-created candidate. Human review required before publish.",
                )
                session.add(candidate)
                candidate_rows.append(candidate)
                seen_candidate_keys.add(label_key)
                await session.flush()

                fields_to_insert: list[tuple[str, str | None, str | None, str, str]] = [
                    (
                        "canonical_name",
                        extracted_label,
                        matched_source.project_name if matched_source else extracted_label,
                        "reported",
                        confidence_level,
                    )
                ]
                if city:
                    fields_to_insert.append(("city", city, city, city_origin, "high" if city_origin == "reported" else "medium"))
                if neighborhood:
                    fields_to_insert.append(("neighborhood", neighborhood, neighborhood, neighborhood_origin, "medium"))
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
                            source_table_name=section_row.raw_label or section_row.section_name,
                            source_row_label=extracted_label,
                            extraction_profile_key=section_row.extraction_profile_key,
                            value_origin_type=origin if origin in {"reported", "inferred"} else "unknown",
                            confidence_level=field_confidence,
                            review_status="pending",
                            review_notes="Parser-created field candidate. Review before publish.",
                        )
                    )
                    field_count += 1

                await refresh_candidate_match_suggestions(session, candidate)
                await _sync_report_queue(session, report.id, candidate.id, "open", "Parser-created candidate awaiting review")

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
            **quality_diagnostics,
            "segmentation": [
                {
                    "section_title": chunk.section_name,
                    "section_kind": chunk.section_kind,
                    "page_start": chunk.source_page_from,
                    "page_end": chunk.source_page_to,
                    "chunk_order": chunk.chunk_order,
                    "overlap_flag": chunk.overlap_flag,
                    "extraction_profile_key": chunk.extraction_profile_key,
                }
                for chunk in chunks
            ],
            "pass1_vs_pass2": {
                "pass1_candidates": len(candidate_rows) + len(suppressed_rows),
                "accepted_candidates": len(candidate_rows),
                "suppressed_candidates": len(suppressed_rows),
            },
            "matched_projects": [str(candidate.matched_project_id) for candidate in candidate_rows if candidate.matched_project_id],
            "section_kind_counts": dict(
                Counter(section.section_kind or "summary_only" for section in persisted_sections)
            ),
            "extraction_profile_counts": dict(
                Counter(section.extraction_profile_key or "unknown" for section in persisted_sections)
            ),
            "lifecycle_stage_distribution": dict(
                Counter(candidate.candidate_lifecycle_stage or "unknown" for candidate in candidate_rows)
            ),
            "disclosure_level_distribution": dict(
                Counter(candidate.candidate_disclosure_level or "unknown" for candidate in candidate_rows)
            ),
            "data_family_distribution": dict(
                Counter(
                    family
                    for candidate in candidate_rows
                    for family in (candidate.detected_data_families or [])
                )
            ),
            "candidate_confidence_distribution": dict(
                Counter(candidate.confidence_level for candidate in candidate_rows)
            ),
            "family_confidence_distribution": {
                "high": sum(1 for candidate in candidate_rows if (candidate.family_confidence_score or Decimal("0")) >= Decimal("0.80")),
                "medium": sum(
                    1
                    for candidate in candidate_rows
                    if Decimal("0.60") <= (candidate.family_confidence_score or Decimal("0")) < Decimal("0.80")
                ),
                "low": sum(1 for candidate in candidate_rows if (candidate.family_confidence_score or Decimal("0")) < Decimal("0.60")),
            },
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
