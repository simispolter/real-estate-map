from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.benchmark.manifests import BENCHMARK_MANIFESTS, ExpectedProjectManifest, ReportBenchmarkManifest
from app.models import Company, ParserRunLog, Report, StagingFieldCandidate, StagingProjectCandidate, StagingReport
from app.services.document_conversion import convert_pdf_document
from app.services.extraction_profiles import (
    classify_section,
    infer_candidate_disclosure_level,
    infer_candidate_lifecycle_stage,
)
from app.services.ingestion import create_admin_report, update_admin_report
from app.services.identity_ops import normalize_text
from app.services.parser_pipeline import (
    _build_candidate_drafts,
    _context_window,
    _extract_metric,
    _extract_project_labels,
    _extract_status,
    _safe_decimal,
    _safe_int,
    _segment_sections,
    segment_report_chunks,
)


BENCHMARK_BACKENDS = ("pypdf", "pdfplumber", "docling")
FAMILY_KEYS = (
    "construction",
    "planning",
    "completed_unsold_tail",
    "land_reserve",
    "urban_renewal_pipeline",
    "material_project",
)
SECTION_KIND_TO_FAMILY = {
    "construction": "construction",
    "planning": "planning",
    "completed": "completed_unsold_tail",
    "land_reserve": "land_reserve",
    "urban_renewal": "urban_renewal_pipeline",
    "material_project": "material_project",
}


@dataclass(slots=True)
class CandidateBenchmarkRecord:
    id: UUID
    candidate_name: str
    family: str | None
    lifecycle_stage: str | None
    disclosure_level: str | None
    extraction_profile_key: str | None
    source_table_name: str | None
    source_row_label: str | None
    project_status: str | None
    permit_status: str | None
    total_units: int | None
    unsold_units: int | None
    field_presence: set[str]


def _candidate_field_presence(
    candidate: StagingProjectCandidate,
    field_rows: list[StagingFieldCandidate],
) -> set[str]:
    presence: set[str] = set()
    if candidate.candidate_project_name:
        presence.add("canonical_name")
    if candidate.candidate_lifecycle_stage:
        presence.add("candidate_lifecycle_stage")
    if candidate.candidate_disclosure_level:
        presence.add("candidate_disclosure_level")
    if candidate.candidate_section_kind:
        presence.add("candidate_section_kind")
    if candidate.extraction_profile_key:
        presence.add("extraction_profile_key")
    if candidate.project_status:
        presence.add("project_status")
    if candidate.permit_status:
        presence.add("permit_status")
    if candidate.total_units is not None:
        presence.add("total_units")
    if candidate.marketed_units is not None:
        presence.add("marketed_units")
    if candidate.sold_units_cumulative is not None:
        presence.add("sold_units_cumulative")
    if candidate.unsold_units is not None:
        presence.add("unsold_units")
    if candidate.avg_price_per_sqm_cumulative is not None:
        presence.add("avg_price_per_sqm_cumulative")
    if candidate.gross_profit_total_expected is not None:
        presence.add("gross_profit_total_expected")
    if candidate.gross_margin_expected_pct is not None:
        presence.add("gross_margin_expected_pct")

    if any(field.source_page is not None for field in field_rows):
        presence.add("source_page")
    if any(field.source_section for field in field_rows):
        presence.add("source_section")
    return presence


def _normalize_value(value: str) -> str:
    normalized = normalize_text(value or "")
    normalized = " ".join(part for part in normalized.replace("–", "-").replace("—", "-").split() if part)
    return normalized


def _name_similarity(left: str, right: str) -> float:
    left_norm = _normalize_value(left)
    right_norm = _normalize_value(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.92
    if left_norm.replace(" ", "") in right_norm.replace(" ", "") or right_norm.replace(" ", "") in left_norm.replace(" ", ""):
        return 0.88
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _match_candidate_to_expected(
    candidate_name: str,
    expected_projects: tuple[ExpectedProjectManifest, ...],
    *,
    threshold: float = 0.72,
) -> tuple[ExpectedProjectManifest | None, float, list[str]]:
    best_match: ExpectedProjectManifest | None = None
    best_score = 0.0
    all_matches: list[str] = []
    for expected in expected_projects:
        aliases = (expected.canonical_name, *expected.aliases)
        score = max(_name_similarity(candidate_name, alias) for alias in aliases)
        if score >= threshold:
            all_matches.append(expected.canonical_name)
        if score > best_score:
            best_match = expected
            best_score = score
    if best_score < threshold:
        return None, best_score, []
    return best_match, best_score, all_matches


async def _resolve_company(session: AsyncSession, manifest: ReportBenchmarkManifest) -> Company:
    filters = [Company.name_he == manifest.company_name_he]
    if manifest.ticker:
        filters.append(Company.ticker == manifest.ticker)
    company = (
        await session.execute(select(Company).where(or_(*filters)).order_by(Company.created_at.asc()))
    ).scalar_one_or_none()
    if company is not None:
        return company

    company = Company(
        id=uuid4(),
        name_he=manifest.company_name_he,
        name_en=manifest.company_name_en,
        ticker=manifest.ticker,
        public_status="public",
        sector="residential_developer",
    )
    session.add(company)
    await session.commit()
    return company


async def _upsert_report(session: AsyncSession, manifest: ReportBenchmarkManifest) -> Report:
    company = await _resolve_company(session, manifest)
    report = (
        await session.execute(
            select(Report)
            .where(Report.source_file_path == manifest.source_file_path)
            .order_by(Report.created_at.asc())
        )
    ).scalar_one_or_none()

    payload = {
        "company_id": company.id,
        "report_name": manifest.report_name,
        "report_type": "annual",
        "period_type": "annual",
        "period_end_date": manifest.period_end_date,
        "published_at": manifest.published_at,
        "source_url": None,
        "source_file_path": manifest.source_file_path,
        "source_is_official": False,
        "source_label": "Document-conversion benchmark annual report",
        "ingestion_status": "ready_for_staging",
        "notes": manifest.notes,
    }

    if report is None:
        created = await create_admin_report(session, payload)
        report = (await session.execute(select(Report).where(Report.id == created["id"]))).scalar_one()
    else:
        await update_admin_report(session, report.id, payload)
        report = (await session.execute(select(Report).where(Report.id == report.id))).scalar_one()
    return report


async def _load_candidate_records(session: AsyncSession, report_id: UUID) -> tuple[list[CandidateBenchmarkRecord], dict[str, Any]]:
    staging_report = (
        await session.execute(select(StagingReport).where(StagingReport.report_id == report_id))
    ).scalar_one()
    candidates = (
        await session.execute(
            select(StagingProjectCandidate)
            .where(StagingProjectCandidate.staging_report_id == staging_report.id)
            .order_by(StagingProjectCandidate.created_at.asc())
        )
    ).scalars().all()
    candidate_ids = [candidate.id for candidate in candidates]
    fields = []
    if candidate_ids:
        fields = (
            await session.execute(
                select(StagingFieldCandidate)
                .where(StagingFieldCandidate.candidate_id.in_(candidate_ids))
                .order_by(StagingFieldCandidate.created_at.asc())
            )
        ).scalars().all()
    fields_by_candidate: dict[UUID, list[StagingFieldCandidate]] = defaultdict(list)
    for field in fields:
        fields_by_candidate[field.candidate_id].append(field)

    latest_parser_run = (
        await session.execute(
            select(ParserRunLog)
            .where(ParserRunLog.report_id == report_id)
            .order_by(ParserRunLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    records: list[CandidateBenchmarkRecord] = []
    for candidate in candidates:
        field_rows = fields_by_candidate.get(candidate.id, [])
        records.append(
            CandidateBenchmarkRecord(
                id=candidate.id,
                candidate_name=candidate.candidate_project_name,
                family=SECTION_KIND_TO_FAMILY.get(candidate.candidate_section_kind or ""),
                lifecycle_stage=candidate.candidate_lifecycle_stage,
                disclosure_level=candidate.candidate_disclosure_level,
                extraction_profile_key=candidate.extraction_profile_key,
                source_table_name=candidate.source_table_name,
                source_row_label=candidate.source_row_label,
                project_status=candidate.project_status,
                permit_status=candidate.permit_status,
                total_units=candidate.total_units,
                unsold_units=candidate.unsold_units,
                field_presence=_candidate_field_presence(candidate, field_rows),
            )
        )

    parser_diagnostics = dict(latest_parser_run.diagnostics_json or {}) if latest_parser_run else {}
    return records, parser_diagnostics


def _field_coverage_for_expected(
    expected: ExpectedProjectManifest,
    assigned_candidates: list[CandidateBenchmarkRecord],
) -> tuple[int, int]:
    if not assigned_candidates:
        return 0, len(expected.required_fields)
    covered = set().union(*(candidate.field_presence for candidate in assigned_candidates))
    covered_count = sum(1 for field_name in expected.required_fields if field_name in covered)
    return covered_count, len(expected.required_fields)


def _family_recall(
    manifest: ReportBenchmarkManifest,
    matched_candidates: list[CandidateBenchmarkRecord],
) -> tuple[float, dict[str, dict[str, int]]]:
    detected = Counter(candidate.family or "unknown" for candidate in matched_candidates)
    comparison: dict[str, dict[str, int]] = {}
    recall_components: list[float] = []
    for family in FAMILY_KEYS:
        expected_count = manifest.expected_family_counts.get(family, 0)
        detected_count = int(detected.get(family, 0))
        comparison[family] = {"expected": expected_count, "detected": detected_count}
        if expected_count > 0:
            recall_components.append(min(expected_count, detected_count) / expected_count)
    return (sum(recall_components) / len(recall_components) if recall_components else 1.0), comparison


def _backend_score(result: dict[str, Any]) -> float:
    false_split_penalty = min(result["false_split_count"] / max(result["expected_project_count"], 1), 1.0)
    false_merge_penalty = min(result["false_merge_count"] / max(result["expected_project_count"], 1), 1.0)
    return round(
        (result["project_recall"] * 0.35)
        + (result["family_recall"] * 0.2)
        + (result["field_coverage"] * 0.2)
        + (result["table_quality"] * 0.1)
        + (result["provenance_preservation"] * 0.1)
        - (result["unmatched_rate"] * 0.1)
        - (false_split_penalty * 0.08)
        - (false_merge_penalty * 0.07),
        4,
    )


def _evaluate_manifest(
    manifest: ReportBenchmarkManifest,
    backend: str,
    candidates: list[CandidateBenchmarkRecord],
    parser_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    matched_expected: dict[str, list[CandidateBenchmarkRecord]] = defaultdict(list)
    unexpected_candidates: list[str] = []
    multi_match_count = 0

    for candidate in candidates:
        expected, score, all_matches = _match_candidate_to_expected(candidate.candidate_name, manifest.expected_projects)
        if len(all_matches) > 1:
            multi_match_count += 1
        if expected is None:
            unexpected_candidates.append(candidate.candidate_name)
            continue
        matched_expected[expected.canonical_name].append(candidate)

    matched_expected_count = len(matched_expected)
    expected_project_count = len(manifest.expected_projects)
    project_recall = matched_expected_count / expected_project_count if expected_project_count else 1.0
    false_split_count = sum(max(len(items) - 1, 0) for items in matched_expected.values())
    false_merge_count = multi_match_count
    unmatched_rate = len(unexpected_candidates) / len(candidates) if candidates else 0.0

    field_covered = 0
    field_total = 0
    missing_expected_projects: list[str] = []
    for expected in manifest.expected_projects:
        assigned = matched_expected.get(expected.canonical_name, [])
        if not assigned:
            missing_expected_projects.append(expected.canonical_name)
        covered_count, total_count = _field_coverage_for_expected(expected, assigned)
        field_covered += covered_count
        field_total += total_count
    field_coverage = field_covered / field_total if field_total else 1.0

    matched_candidate_rows = [candidate for items in matched_expected.values() for candidate in items]
    family_recall, family_comparison = _family_recall(manifest, matched_candidate_rows)

    structured_candidates = sum(
        1
        for candidate in candidates
        if candidate.source_table_name and candidate.source_row_label and candidate.extraction_profile_key
    )
    provenance_candidates = sum(
        1
        for candidate in candidates
        if "source_page" in candidate.field_presence and "source_section" in candidate.field_presence
    )
    table_quality = structured_candidates / len(candidates) if candidates else 0.0
    provenance_preservation = provenance_candidates / len(candidates) if candidates else 0.0
    lifecycle_distribution = dict(Counter(candidate.lifecycle_stage or "unknown" for candidate in candidates))
    disclosure_distribution = dict(Counter(candidate.disclosure_level or "unknown" for candidate in candidates))
    key_field_missing_counts = {
        "project_status": sum(1 for candidate in candidates if "project_status" not in candidate.field_presence),
        "total_units": sum(1 for candidate in candidates if "total_units" not in candidate.field_presence),
        "candidate_lifecycle_stage": sum(
            1 for candidate in candidates if "candidate_lifecycle_stage" not in candidate.field_presence
        ),
        "candidate_disclosure_level": sum(
            1 for candidate in candidates if "candidate_disclosure_level" not in candidate.field_presence
        ),
    }

    result = {
        "backend": backend,
        "candidate_count": len(candidates),
        "expected_project_count": expected_project_count,
        "matched_expected_count": matched_expected_count,
        "project_recall": round(project_recall, 4),
        "family_recall": round(family_recall, 4),
        "field_coverage": round(field_coverage, 4),
        "false_split_count": false_split_count,
        "false_merge_count": false_merge_count,
        "unmatched_rate": round(unmatched_rate, 4),
        "table_quality": round(table_quality, 4),
        "provenance_preservation": round(provenance_preservation, 4),
        "missing_expected_projects": missing_expected_projects,
        "unexpected_candidates": unexpected_candidates,
        "family_comparison": family_comparison,
        "lifecycle_stage_distribution": lifecycle_distribution,
        "disclosure_level_distribution": disclosure_distribution,
        "missing_key_field_counts": key_field_missing_counts,
        "conversion_backend_diagnostics": parser_diagnostics.get("conversion_backend_diagnostics", {}),
        "conversion_table_count": parser_diagnostics.get("conversion_table_count", 0),
    }
    result["score"] = _backend_score(result)
    return result


async def run_document_conversion_benchmark(
    session: AsyncSession,
    *,
    backends: tuple[str, ...] = BENCHMARK_BACKENDS,
) -> dict[str, Any]:
    generated_at = datetime.now(UTC)
    report_results: list[dict[str, Any]] = []
    backend_rollups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for manifest in BENCHMARK_MANIFESTS:
        if not Path(manifest.source_file_path).exists():
            report_results.append(
                {
                    "report_key": manifest.report_key,
                    "company_name_he": manifest.company_name_he,
                    "report_name": manifest.report_name,
                    "source_file_path": manifest.source_file_path,
                    "skipped": True,
                    "skip_reason": "missing_file",
                    "expected_project_count": len(manifest.expected_projects),
                    "results": [],
                }
            )
            continue

        current_results: list[dict[str, Any]] = []

        for backend in backends:
            try:
                pdf_bytes = Path(manifest.source_file_path).read_bytes()
                converted_document = convert_pdf_document(
                    pdf_bytes,
                    backend=backend,
                    ocr_mode="off",
                )
                candidate_rows, parser_diagnostics = _extract_candidates_offline(converted_document)
                evaluation = _evaluate_manifest(manifest, backend, candidate_rows, parser_diagnostics)
                current_results.append(evaluation)
                backend_rollups[backend].append(evaluation)
            except Exception as exc:
                current_results.append(
                    {
                        "backend": backend,
                        "error": str(exc),
                        "candidate_count": 0,
                        "expected_project_count": len(manifest.expected_projects),
                        "matched_expected_count": 0,
                        "project_recall": 0.0,
                        "family_recall": 0.0,
                        "field_coverage": 0.0,
                        "false_split_count": 0,
                        "false_merge_count": 0,
                        "unmatched_rate": 1.0,
                        "table_quality": 0.0,
                        "provenance_preservation": 0.0,
                        "missing_expected_projects": [project.canonical_name for project in manifest.expected_projects],
                        "unexpected_candidates": [],
                        "family_comparison": {family: {"expected": manifest.expected_family_counts.get(family, 0), "detected": 0} for family in FAMILY_KEYS},
                        "lifecycle_stage_distribution": {},
                        "disclosure_level_distribution": {},
                        "missing_key_field_counts": {},
                        "conversion_backend_diagnostics": {},
                        "conversion_table_count": 0,
                        "score": -1.0,
                    }
                )

        report_results.append(
            {
                "report_key": manifest.report_key,
                "company_name_he": manifest.company_name_he,
                "report_name": manifest.report_name,
                "source_file_path": manifest.source_file_path,
                "expected_project_count": len(manifest.expected_projects),
                "expected_family_counts": manifest.expected_family_counts,
                "results": current_results,
            }
        )

    backend_summary: dict[str, dict[str, Any]] = {}
    for backend, rows in backend_rollups.items():
        if not rows:
            continue
        backend_summary[backend] = {
            "average_score": round(sum(row["score"] for row in rows) / len(rows), 4),
            "average_project_recall": round(sum(row["project_recall"] for row in rows) / len(rows), 4),
            "average_family_recall": round(sum(row["family_recall"] for row in rows) / len(rows), 4),
            "average_field_coverage": round(sum(row["field_coverage"] for row in rows) / len(rows), 4),
            "average_unmatched_rate": round(sum(row["unmatched_rate"] for row in rows) / len(rows), 4),
            "average_table_quality": round(sum(row["table_quality"] for row in rows) / len(rows), 4),
            "average_provenance_preservation": round(
                sum(row["provenance_preservation"] for row in rows) / len(rows),
                4,
            ),
        }

    recommended_default_backend = "pypdf"
    if backend_summary:
        recommended_default_backend = max(
            backend_summary.items(),
            key=lambda item: item[1]["average_score"],
        )[0]

    return {
        "generated_at": generated_at,
        "report_count": len(BENCHMARK_MANIFESTS),
        "backends": list(backends),
        "recommended_default_backend": recommended_default_backend,
        "backend_summary": backend_summary,
        "reports": report_results,
    }


def _extract_candidates_offline(
    converted_document: Any,
) -> tuple[list[CandidateBenchmarkRecord], dict[str, Any]]:
    chunks = segment_report_chunks(converted_document.page_texts)
    sections = [
        type(
            "BenchmarkSection",
            (),
            {
                "section_name": chunk.section_name,
                "raw_label": chunk.raw_label,
                "source_page_from": chunk.source_page_from,
                "source_page_to": chunk.source_page_to,
                "text": chunk.text,
            },
        )()
        for chunk in chunks
    ]
    candidates: list[CandidateBenchmarkRecord] = []
    persisted_section_stubs = []
    for chunk, section in zip(chunks, sections, strict=False):
        classification = classify_section(section.section_name, section.raw_label, section.text[:500])
        persisted_section_stubs.append(
            type(
                "SectionStub",
                (),
                {
                    "section_name": chunk.section_name,
                    "section_kind": chunk.section_kind,
                    "raw_label": chunk.raw_label,
                    "extraction_profile_key": chunk.extraction_profile_key,
                    "source_page_from": chunk.source_page_from,
                },
            )()
        )
        if chunk.section_kind == "summary_only":
            continue

        for extracted_label in _extract_project_labels(
            section.text,
            section_kind=chunk.section_kind,
            known_cities=[],
        ):
            context = _context_window(section.text, extracted_label)
            project_status, _ = _extract_status(context, "project_status")
            permit_status, _ = _extract_status(context, "permit_status")
            metrics: dict[str, tuple[str | None, Any, str]] = {}
            for field_name in ("total_units", "marketed_units", "sold_units_cumulative", "unsold_units", "avg_price_per_sqm_cumulative", "gross_margin_expected_pct"):
                metrics[field_name] = _extract_metric(context, field_name)

            lifecycle_stage = infer_candidate_lifecycle_stage(
                section_kind=chunk.section_kind,
                project_status=project_status,
                project_business_type=None,
                permit_status=permit_status,
            )
            disclosure_level = infer_candidate_disclosure_level(
                section_kind=chunk.section_kind,
                extraction_profile_key=chunk.extraction_profile_key,
                total_units=_safe_int(metrics["total_units"][1]),
                marketed_units=_safe_int(metrics["marketed_units"][1]),
                sold_units_cumulative=_safe_int(metrics["sold_units_cumulative"][1]),
                gross_margin_expected_pct=_safe_decimal(metrics["gross_margin_expected_pct"][1]),
            )
            field_presence = {
                "canonical_name",
                "source_page",
                "source_section",
                "extraction_profile_key",
            }
            if lifecycle_stage:
                field_presence.add("candidate_lifecycle_stage")
            if disclosure_level:
                field_presence.add("candidate_disclosure_level")
            if project_status:
                field_presence.add("project_status")
            if permit_status:
                field_presence.add("permit_status")
            if _safe_int(metrics["total_units"][1]) is not None:
                field_presence.add("total_units")
            if _safe_int(metrics["marketed_units"][1]) is not None:
                field_presence.add("marketed_units")
            if _safe_int(metrics["sold_units_cumulative"][1]) is not None:
                field_presence.add("sold_units_cumulative")
            if _safe_int(metrics["unsold_units"][1]) is not None:
                field_presence.add("unsold_units")
            if _safe_decimal(metrics["avg_price_per_sqm_cumulative"][1]) is not None:
                field_presence.add("avg_price_per_sqm_cumulative")
            if _safe_decimal(metrics["gross_margin_expected_pct"][1]) is not None:
                field_presence.add("gross_margin_expected_pct")

            candidates.append(
                CandidateBenchmarkRecord(
                    id=uuid4(),
                    candidate_name=extracted_label,
                    family=SECTION_KIND_TO_FAMILY.get(chunk.section_kind),
                    lifecycle_stage=lifecycle_stage,
                    disclosure_level=disclosure_level,
                    extraction_profile_key=chunk.extraction_profile_key,
                    source_table_name=chunk.raw_label or chunk.section_name,
                    source_row_label=extracted_label,
                    project_status=project_status,
                    permit_status=permit_status,
                    total_units=_safe_int(metrics["total_units"][1]),
                    unsold_units=_safe_int(metrics["unsold_units"][1]),
                    field_presence=field_presence,
                )
            )

    _, suppressed_rows, quality_diagnostics = _build_candidate_drafts(
        sections=sections,
        persisted_sections=persisted_section_stubs,
        candidate_sources=[],
        known_cities=[],
    )
    for draft in []:
        field_presence = {
            "canonical_name",
            "source_page",
            "source_section",
            "extraction_profile_key",
        }

    parser_diagnostics = {
        "conversion_backend_diagnostics": converted_document.diagnostics,
        "conversion_table_count": converted_document.table_count,
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
        **quality_diagnostics,
        "suppressed_rows_preview": [
            {
                "reason": row.reason,
                "source_section": row.source_section,
                "raw_text": row.raw_text[:120],
            }
            for row in suppressed_rows[:10]
        ],
    }
    return candidates, parser_diagnostics
