from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import or_, select

from app.db.session import get_session_factory
from app.models import Company, ProjectAlias, ProjectMaster, ProjectSnapshot, Report, StagingProjectCandidate, StagingReport
from app.services.ingestion import (
    create_admin_report,
    create_candidate,
    get_admin_report_qa,
    match_candidate,
    publish_candidate,
    update_admin_report,
    update_candidate,
)
from app.services.admin_review import merge_admin_projects
from app.services.parser_pipeline import run_report_extraction


BOOTSTRAP_BATCH_LABEL = "Bootstrap annual report batch 2026-03-26"
BOOTSTRAP_EXTRACTION_PROFILE = "bootstrap_manual_review"
BOOTSTRAP_NOTES = "Pragmatic bootstrap batch from uploaded annual reports. Extraction was attempted first; missing residential project rows were manually completed into staging and then published through the same review flow."


@dataclass(frozen=True, slots=True)
class CandidateSeed:
    canonical_name: str
    raw_name: str
    city: str | None
    lifecycle_stage: str
    disclosure_level: str
    section_kind: str
    project_status: str | None
    permit_status: str | None
    source_page: int
    source_section: str
    project_business_type: str | None = None
    project_urban_renewal_type: str | None = None
    source_table_name: str | None = None
    metrics: dict[str, Decimal | int | None] = field(default_factory=dict)
    match_existing_name: str | None = None
    reviewer_note: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportSeed:
    source_file_path: str
    company_name_he: str
    company_name_en: str | None
    ticker: str | None
    report_name: str
    report_type: str
    period_type: str
    period_end_date: date
    published_at: date | None
    source_label: str
    source_is_official: bool
    notes: str
    candidates: tuple[CandidateSeed, ...]


REPORTS: tuple[ReportSeed, ...] = (
    ReportSeed(
        source_file_path="/app/input_reports/bootstrap_2026_03_26/1729852.pdf",
        company_name_he="אאורה",
        company_name_en="Aura Investments Ltd",
        ticker="AURA",
        report_name="דו\"ח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        source_label=BOOTSTRAP_BATCH_LABEL,
        source_is_official=True,
        notes=BOOTSTRAP_NOTES,
        candidates=(
            CandidateSeed("LINK (שוק אשכנזי)", "LINK (אשכנזי) יהוד", "יהוד", "under_construction", "material_very_high", "material_project", "construction", None, 56, "פרויקטים בהקמה – ניתוח רגישות", metrics={"gross_profit_total_expected": Decimal("226961")}, match_existing_name="LINK (שוק אשכנזי)", reviewer_note="Matched to existing Aura project and published from annual-report sensitivity table.", aliases=("LINK (אשכנזי) יהוד",)),
            CandidateSeed("אאורה רמת חן", "אאורה רמת חן", "רמת גן", "under_construction", "material_very_high", "material_project", "construction", None, 56, "פרויקטים בהקמה – ניתוח רגישות", metrics={"gross_profit_total_expected": Decimal("213004")}, match_existing_name="אאורה רמת חן", reviewer_note="Matched to existing Aura project and refreshed with 2025 annual-report snapshot."),
            CandidateSeed("פרויקט האורן", "פרויקט האורן", None, "under_construction", "material_very_high", "material_project", "construction", None, 56, "פרויקטים בהקמה – ניתוח רגישות", metrics={"gross_profit_total_expected": Decimal("113549")}, match_existing_name="פרויקט האורן", reviewer_note="Matched to existing Aura project and refreshed from annual-report sensitivity disclosure."),
            CandidateSeed("אאורה פיבקו בת ים", "אאורה פיבקו, בת ים", "בת ים", "under_construction", "material_very_high", "material_project", "construction", None, 56, "פרויקטים בהקמה – ניתוח רגישות", project_business_type="regular_dev", metrics={"gross_profit_total_expected": Decimal("87507")}, reviewer_note="Manual completion from Aura annual report because parser did not produce this material-project row."),
            CandidateSeed("גבעתיים אימאג'ין", "גבעתיים ONLY", "גבעתיים", "under_construction", "material_very_high", "material_project", "construction", None, 56, "פרויקטים בהקמה – ניתוח רגישות", project_business_type="regular_dev", metrics={"gross_profit_total_expected": Decimal("104018")}, reviewer_note="Manual completion from Aura annual report; canonical name normalized from report label.", aliases=("גבעתיים ONLY",)),
        ),
    ),
    ReportSeed(
        source_file_path="/app/input_reports/bootstrap_2026_03_26/1730633.pdf",
        company_name_he="רוטשטיין נדלן",
        company_name_en="Rotshtein Real Estate Ltd",
        ticker=None,
        report_name="דו\"ח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=date(2026, 3, 24),
        source_label=BOOTSTRAP_BATCH_LABEL,
        source_is_official=True,
        notes=BOOTSTRAP_NOTES,
        candidates=(
            CandidateSeed("פינוי-בינוי בת ים", "פינוי-בינוי בת ים", "בת ים", "under_construction", "operational_full", "construction", "construction", None, 30, "פרויקטים בהקמה", project_business_type="urban_renewal", project_urban_renewal_type="pinui_binui", metrics={"total_units": 137, "marketed_units": 115, "sold_units_cumulative": 98, "unsold_units": 27, "gross_profit_total_expected": Decimal("72171"), "gross_margin_expected_pct": Decimal("21")}, reviewer_note="Manual staging candidate from Rotshtein construction table."),
            CandidateSeed("לוד מתחם גלבוע - שלב א'", "לוד מתחם גלבוע- שלב א'", "לוד", "under_construction", "operational_full", "construction", "construction", None, 30, "פרויקטים בהקמה", project_business_type="urban_renewal", project_urban_renewal_type="pinui_binui", metrics={"total_units": 138, "marketed_units": 114, "sold_units_cumulative": 101, "unsold_units": 10, "gross_profit_total_expected": Decimal("49090"), "gross_margin_expected_pct": Decimal("22")}, reviewer_note="Manual staging candidate from Rotshtein construction table."),
            CandidateSeed("דוד המלך 29", "דוד המלך 29", "תל אביב", "under_construction", "operational_full", "construction", "construction", None, 31, "פרויקטים בהקמה", project_business_type="urban_renewal", project_urban_renewal_type="other", metrics={"total_units": 15, "marketed_units": 7, "sold_units_cumulative": 6, "unsold_units": 1, "gross_profit_total_expected": Decimal("8627"), "gross_margin_expected_pct": Decimal("17")}, reviewer_note="Manual staging candidate from Rotshtein construction table."),
            CandidateSeed("הקריה האקדמית", "הקריה האקדמית", "פתח תקווה", "under_construction", "operational_full", "construction", "construction", None, 31, "פרויקטים בהקמה", project_business_type="regular_dev", metrics={"total_units": 166, "marketed_units": 77, "sold_units_cumulative": 51, "unsold_units": 28, "gross_profit_total_expected": Decimal("42006"), "gross_margin_expected_pct": Decimal("14")}, reviewer_note="Manual staging candidate from Rotshtein construction table."),
            CandidateSeed("ENZO", "ENZO", "אשדוד", "under_construction", "operational_full", "construction", "construction", None, 31, "פרויקטים בהקמה", project_business_type="regular_dev", metrics={"total_units": 230, "marketed_units": 230, "sold_units_cumulative": 35, "unsold_units": 195, "gross_profit_total_expected": Decimal("142666"), "gross_margin_expected_pct": Decimal("23")}, reviewer_note="Manual staging candidate from Rotshtein construction table."),
            CandidateSeed("קדמת נתניה", "קדמת נתניה", "נתניה", "completed_unsold_tail", "inventory_tail", "completed", "completed", None, 33, "הקמתם הסתיימה ושמכירתם טרם הושלמה", project_business_type="regular_dev", metrics={"unsold_units": 4, "gross_profit_total_expected": Decimal("7765"), "gross_margin_expected_pct": Decimal("46")}, reviewer_note="Manual completion from Rotshtein completed inventory tail section."),
        ),
    ),
    ReportSeed(
        source_file_path="/app/input_reports/bootstrap_2026_03_26/1730670.htm",
        company_name_he="אפריקה ישראל מגורים",
        company_name_en="Africa Israel Residences Ltd",
        ticker=None,
        report_name="דו\"ח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=date(2026, 3, 24),
        source_label=BOOTSTRAP_BATCH_LABEL,
        source_is_official=True,
        notes=BOOTSTRAP_NOTES,
        candidates=(
            CandidateSeed("אגמי בראשית שלב א'", "אגמי בראשית שלב א'", "נשר", "planning_advanced", "operational_full", "planning", "planning", None, 59, "פרויקטים בתכנון", project_business_type="regular_dev", metrics={"total_units": 288, "marketed_units": 288, "sold_units_cumulative": 132, "unsold_units": 156, "gross_profit_total_expected": Decimal("24748"), "gross_margin_expected_pct": Decimal("17")}, match_existing_name="אגמי בראשית שלב א'", reviewer_note="Matched to existing Africa Israel project from planning tables."),
            CandidateSeed("קיציס", "קיציס", "תל אביב", "urban_renewal_pipeline", "pipeline_signature", "urban_renewal", "planning", None, 71, "פרויקטים התחדשות עירונית", project_business_type="urban_renewal", project_urban_renewal_type="other", metrics={"total_units": 178, "marketed_units": 98, "sold_units_cumulative": 19, "unsold_units": 79, "gross_profit_total_expected": Decimal("27655"), "gross_margin_expected_pct": Decimal("16")}, match_existing_name="קיציס", reviewer_note="Matched to existing Africa Israel urban-renewal project."),
            CandidateSeed("גבריאלוב", "גבריאלוב", "רחובות", "urban_renewal_pipeline", "pipeline_signature", "urban_renewal", "planning", None, 72, "פרויקטים התחדשות עירונית", project_business_type="urban_renewal", project_urban_renewal_type="other", metrics={"total_units": 156, "marketed_units": 126, "sold_units_cumulative": 10, "unsold_units": 116, "gross_profit_total_expected": Decimal("30393"), "gross_margin_expected_pct": Decimal("19")}, match_existing_name="גבריאלוב", reviewer_note="Matched to existing Africa Israel urban-renewal project."),
            CandidateSeed("ז'בוטינסקי 135-137", "ז'בוטינסקי 135-137", "תל אביב", "under_construction", "operational_full", "urban_renewal", "construction", None, 71, "פרויקטים התחדשות עירונית", project_business_type="urban_renewal", project_urban_renewal_type="other", metrics={"total_units": 34}, match_existing_name="ז'בוטינסקי 135-137", reviewer_note="Matched to existing Africa Israel project from urban-renewal section."),
            CandidateSeed("סביוני השמורה (זלמן שניאור) שלב ב'", "סביוני השמורה (זלמן שניאור) שלב ב'", "נתניה", "urban_renewal_pipeline", "pipeline_signature", "urban_renewal", "planning", None, 71, "פרויקטים התחדשות עירונית", project_business_type="urban_renewal", project_urban_renewal_type="pinui_binui", metrics={"total_units": 256, "marketed_units": 192, "unsold_units": 192, "gross_profit_total_expected": Decimal("105565"), "gross_margin_expected_pct": Decimal("20")}, reviewer_note="Manual completion from Africa Israel urban-renewal planning rows."),
        ),
    ),
    ReportSeed(
        source_file_path="/app/input_reports/bootstrap_2026_03_26/1730981.pdf",
        company_name_he="קבוצת יובלים השקעות",
        company_name_en="Yuvalim Group Investments Ltd",
        ticker=None,
        report_name="דו\"ח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        source_label=BOOTSTRAP_BATCH_LABEL,
        source_is_official=True,
        notes=BOOTSTRAP_NOTES,
        candidates=(
            CandidateSeed("מתחם הכלנית שלב ב'", "מתחם הכלנית שלב ב', אור יהודה", "אור יהודה", "under_construction", "material_very_high", "material_project", "construction", "granted", 59, "פרויקט מהותי מאוד", project_business_type="urban_renewal", project_urban_renewal_type="pinui_binui", metrics={"total_units": 328, "marketed_units": 280, "sold_units_cumulative": 153, "unsold_units": 126, "gross_profit_total_expected": Decimal("185066"), "gross_margin_expected_pct": Decimal("27.02")}, reviewer_note="Manual completion from Yuvalim material-project disclosure pages."),
            CandidateSeed("פארק חדרה", "פארק חדרה, חדרה", "חדרה", "under_construction", "operational_full", "construction", "construction", "granted", 39, "פרויקטים בהקמה", project_business_type="regular_dev", metrics={"total_units": 252, "marketed_units": 252, "sold_units_cumulative": 104, "unsold_units": 148, "gross_profit_total_expected": Decimal("73144"), "gross_margin_expected_pct": Decimal("13")}, reviewer_note="Manual completion from Yuvalim construction table."),
            CandidateSeed("ימים הצעירה נתניה שלב א'", "ימים הצעירה, נתניה שלב א'", "נתניה", "under_construction", "operational_full", "construction", "construction", "granted", 39, "פרויקטים בהקמה", project_business_type="urban_renewal", project_urban_renewal_type="pinui_binui", metrics={"total_units": 480, "marketed_units": 368, "sold_units_cumulative": 350, "unsold_units": 18, "gross_profit_total_expected": Decimal("225291"), "gross_margin_expected_pct": Decimal("25")}, reviewer_note="Manual completion from Yuvalim construction table."),
            CandidateSeed("ימים הצעירה נתניה שלב ב'", "ימים הצעירה, נתניה שלב ב'", "נתניה", "planning_advanced", "operational_full", "construction", "marketing", "pending", 39, "פרויקטים בהקמה", project_business_type="urban_renewal", project_urban_renewal_type="pinui_binui", metrics={"total_units": 392, "marketed_units": 296, "sold_units_cumulative": 58, "unsold_units": 238, "gross_profit_total_expected": Decimal("168150"), "gross_margin_expected_pct": Decimal("22")}, reviewer_note="Manual completion from Yuvalim construction table; kept as planning/early-execution due to permit stage in the row."),
        ),
    ),
    ReportSeed(
        source_file_path="/app/input_reports/bootstrap_2026_03_26/1730985.pdf",
        company_name_he="צבי צרפתי ובניו השקעות ובנין 1992",
        company_name_en="Zvi Tsarfati & Sons Investments and Construction 1992 Ltd",
        ticker=None,
        report_name="דו\"ח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        source_label=BOOTSTRAP_BATCH_LABEL,
        source_is_official=True,
        notes=BOOTSTRAP_NOTES,
        candidates=(
            CandidateSeed("תמ\"א 38/2 ברח' ז'בוטינסקי ברעננה", "תמ\"א 38/2 ברח' ז'בוטינסקי ברעננה", "רעננה", "under_construction", "material_very_high", "material_project", "construction", "granted", 32, "פרויקט מהותי מאוד", project_business_type="urban_renewal", project_urban_renewal_type="tama_38_2", metrics={"total_units": 48, "marketed_units": 32, "gross_profit_total_expected": Decimal("1501"), "gross_margin_expected_pct": Decimal("12.7")}, reviewer_note="Manual completion from Tsarfati material-project disclosure."),
            CandidateSeed("מגרש 214 ח370/4 בחולון", "מגרש 214 ח370/4 בחולון", "חולון", "completed_unsold_tail", "inventory_tail", "completed", "completed", None, 33, "הקמתם הסתיימה ושמכירתם טרם הושלמה", project_business_type="regular_dev", metrics={"unsold_units": 1, "gross_profit_total_expected": Decimal("334"), "gross_margin_expected_pct": Decimal("20")}, reviewer_note="Manual completion from Tsarfati completed inventory tail section."),
            CandidateSeed("מגרש 207 ח370/4 בחולון", "מגרש 207 ח370/4 בחולון", "חולון", "completed_unsold_tail", "inventory_tail", "completed", "completed", None, 33, "הקמתם הסתיימה ושמכירתם טרם הושלמה", project_business_type="regular_dev", metrics={"unsold_units": 13, "gross_profit_total_expected": Decimal("6883"), "gross_margin_expected_pct": Decimal("29")}, reviewer_note="Manual completion from Tsarfati completed inventory tail section."),
            CandidateSeed("שפרינצק (מגרש מס' 1)", "שפרינצק (מגרש מס' 1)", "ראשון לציון", "completed_unsold_tail", "inventory_tail", "completed", "completed", None, 33, "הקמתם הסתיימה ושמכירתם טרם הושלמה", project_business_type="regular_dev", metrics={"unsold_units": 15, "gross_profit_total_expected": Decimal("9276"), "gross_margin_expected_pct": Decimal("22")}, reviewer_note="Manual completion from Tsarfati completed inventory tail section."),
            CandidateSeed("נתניה גוש 8254 חלקה 128", "נתניה גוש 8254 חלקה 128", "נתניה", "completed_unsold_tail", "inventory_tail", "completed", "completed", None, 33, "הקמתם הסתיימה ושמכירתם טרם הושלמה", project_business_type="regular_dev", metrics={"unsold_units": 1, "gross_profit_total_expected": Decimal("1417"), "gross_margin_expected_pct": Decimal("62")}, reviewer_note="Manual completion from Tsarfati completed inventory tail section."),
        ),
    ),
)


def _field_candidate(field_name: str, raw_value: str | None, normalized_value: str | int | Decimal | None, *, page: int, section: str, row_label: str, table_name: str | None, value_origin_type: str, confidence_level: str = "high") -> dict[str, object]:
    return {
        "field_name": field_name,
        "raw_value": raw_value,
        "normalized_value": None if normalized_value is None else str(normalized_value),
        "source_page": page,
        "source_section": section,
        "source_table_name": table_name,
        "source_row_label": row_label,
        "extraction_profile_key": BOOTSTRAP_EXTRACTION_PROFILE,
        "value_origin_type": value_origin_type,
        "confidence_level": confidence_level,
        "review_status": "approved",
        "review_notes": "Bootstrap manual completion from uploaded annual report.",
    }


async def _resolve_company(session, seed: ReportSeed) -> Company:
    filters = [Company.name_he == seed.company_name_he]
    if seed.ticker:
        filters.append(Company.ticker == seed.ticker)
    company = (
        await session.execute(
            select(Company).where(or_(*filters)).order_by(Company.created_at.asc())
        )
    ).scalar_one_or_none()
    if company is not None:
        return company
    company = Company(
        id=uuid5(NAMESPACE_URL, f"bootstrap-company:{seed.company_name_he}"),
        name_he=seed.company_name_he,
        name_en=seed.company_name_en,
        ticker=seed.ticker,
        public_status="public",
        sector="residential_developer",
    )
    session.add(company)
    await session.commit()
    return company


async def _upsert_report(session, seed: ReportSeed) -> Report:
    company = await _resolve_company(session, seed)
    report = (
        await session.execute(select(Report).where(Report.source_file_path == seed.source_file_path).order_by(Report.created_at.asc()))
    ).scalar_one_or_none()
    payload = {
        "company_id": str(company.id),
        "report_name": seed.report_name,
        "report_type": seed.report_type,
        "period_type": seed.period_type,
        "period_end_date": seed.period_end_date,
        "published_at": seed.published_at,
        "source_url": None,
        "source_file_path": seed.source_file_path,
        "source_is_official": seed.source_is_official,
        "source_label": seed.source_label,
        "ingestion_status": "ready_for_staging",
        "notes": seed.notes,
    }
    if report is None:
        created = await create_admin_report(session, payload)
        report = (await session.execute(select(Report).where(Report.id == created["id"]))).scalar_one()
    else:
        await update_admin_report(session, report.id, payload)
        report = (await session.execute(select(Report).where(Report.id == report.id))).scalar_one()
    return report


async def _resolve_existing_project(session, company_id: UUID, canonical_name: str) -> ProjectMaster | None:
    return (
        await session.execute(
            select(ProjectMaster)
            .where(ProjectMaster.company_id == company_id, ProjectMaster.canonical_name == canonical_name)
            .order_by(ProjectMaster.created_at.asc(), ProjectMaster.id.asc())
        )
    ).scalars().first()


async def _list_exact_projects(session, company_id: UUID, canonical_name: str) -> list[ProjectMaster]:
    return (
        await session.execute(
            select(ProjectMaster)
            .where(ProjectMaster.company_id == company_id, ProjectMaster.canonical_name == canonical_name)
            .order_by(ProjectMaster.created_at.asc(), ProjectMaster.id.asc())
        )
    ).scalars().all()


async def _find_existing_candidate(session, report_id: UUID, canonical_name: str) -> StagingProjectCandidate | None:
    staging_report_id = (
        await session.execute(select(StagingReport.id).join(Report, Report.id == StagingReport.report_id).where(Report.id == report_id))
    ).scalar_one()
    return (
        await session.execute(
            select(StagingProjectCandidate)
            .where(
                StagingProjectCandidate.staging_report_id == staging_report_id,
                StagingProjectCandidate.candidate_project_name == canonical_name,
                StagingProjectCandidate.parser_run_id.is_(None),
            )
            .order_by(StagingProjectCandidate.created_at.asc())
        )
    ).scalar_one_or_none()


def _candidate_payload(seed: CandidateSeed, matched_project: ProjectMaster | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_project_name": seed.canonical_name,
        "city": seed.city or (matched_project.city if matched_project is not None else None),
        "candidate_lifecycle_stage": seed.lifecycle_stage,
        "candidate_disclosure_level": seed.disclosure_level,
        "candidate_section_kind": seed.section_kind,
        "project_business_type": seed.project_business_type or (matched_project.project_business_type if matched_project is not None else None),
        "government_program_type": matched_project.government_program_type if matched_project is not None else "none",
        "project_urban_renewal_type": seed.project_urban_renewal_type or (matched_project.project_urban_renewal_type if matched_project is not None else "none"),
        "project_status": seed.project_status,
        "permit_status": seed.permit_status,
        "location_confidence": matched_project.location_confidence if matched_project is not None else "city_only",
        "value_origin_type": "manual",
        "confidence_level": "medium",
        "review_status": "pending",
        "review_notes": seed.reviewer_note,
        "source_table_name": seed.source_table_name or seed.source_section,
        "source_row_label": seed.raw_name,
        "extraction_profile_key": BOOTSTRAP_EXTRACTION_PROFILE,
    }
    payload.update(seed.metrics)
    payload["field_candidates"] = [
        _field_candidate("canonical_name", seed.raw_name, seed.canonical_name, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="reported"),
        _field_candidate("lifecycle_stage", seed.source_section, seed.lifecycle_stage, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="manual", confidence_level="medium"),
        _field_candidate("disclosure_level", seed.source_section, seed.disclosure_level, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="manual", confidence_level="medium"),
        _field_candidate("source_section_kind", seed.source_section, seed.section_kind, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="manual", confidence_level="medium"),
    ]
    if seed.city or (matched_project is not None and matched_project.city):
        payload["field_candidates"].append(
            _field_candidate(
                "city",
                seed.city or matched_project.city,
                seed.city or matched_project.city,
                page=seed.source_page,
                section=seed.source_section,
                row_label=seed.raw_name,
                table_name=seed.source_table_name,
                value_origin_type="reported",
            )
        )
    if seed.project_status:
        payload["field_candidates"].append(
            _field_candidate("project_status", seed.project_status, seed.project_status, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="manual", confidence_level="medium")
        )
    if seed.permit_status:
        payload["field_candidates"].append(
            _field_candidate("permit_status", seed.permit_status, seed.permit_status, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="manual", confidence_level="medium")
        )
    for field_name, value in seed.metrics.items():
        if value is not None:
            payload["field_candidates"].append(
                _field_candidate(field_name, str(value), value, page=seed.source_page, section=seed.source_section, row_label=seed.raw_name, table_name=seed.source_table_name, value_origin_type="reported")
            )
    return payload


async def _ensure_alias(session, *, project_id: UUID, alias_name: str, report_id: UUID, notes: str) -> None:
    existing = (
        await session.execute(
            select(ProjectAlias).where(ProjectAlias.project_id == project_id, ProjectAlias.alias_name == alias_name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        if not existing.is_active:
            existing.is_active = True
            existing.notes = notes
            await session.commit()
        return
    session.add(
        ProjectAlias(
            id=uuid5(NAMESPACE_URL, f"bootstrap-alias:{project_id}:{alias_name}"),
            project_id=project_id,
            alias_name=alias_name,
            value_origin_type="reported",
            alias_source_type="source",
            source_report_id=report_id,
            is_active=True,
            notes=notes,
        )
    )
    await session.commit()


async def _publish_seed_candidate(session, report: Report, seed: CandidateSeed) -> tuple[UUID, bool]:
    existing = await _find_existing_candidate(session, report.id, seed.canonical_name)
    matched_project = await _resolve_existing_project(session, report.company_id, seed.match_existing_name) if seed.match_existing_name else None
    if matched_project is None:
        matched_project = await _resolve_existing_project(session, report.company_id, seed.canonical_name)
    payload = _candidate_payload(seed, matched_project)
    if existing is None:
        candidate_detail = await create_candidate(session, report.id, payload)
    else:
        candidate_detail = await update_candidate(session, existing.id, payload)
    if candidate_detail is None:
        raise RuntimeError(f"Could not create or update candidate for {seed.canonical_name}")

    if matched_project is not None:
        await match_candidate(
            session,
            UUID(str(candidate_detail["id"])),
            {
                "match_status": "matched_existing_project",
                "matched_project_id": matched_project.id,
                "reviewer_note": seed.reviewer_note,
            },
        )
    else:
        await match_candidate(
            session,
            UUID(str(candidate_detail["id"])),
            {
                "match_status": "new_project_needed",
                "matched_project_id": None,
                "reviewer_note": seed.reviewer_note,
            },
        )

    published_detail = await publish_candidate(session, UUID(str(candidate_detail["id"])), seed.reviewer_note)
    if published_detail is None:
        raise RuntimeError(f"Could not publish candidate for {seed.canonical_name}")

    project_id = UUID(str(published_detail["matched_project_id"]))
    project = (await session.execute(select(ProjectMaster).where(ProjectMaster.id == project_id))).scalar_one()
    project.is_publicly_visible = True
    await session.commit()

    if seed.raw_name != seed.canonical_name:
        await _ensure_alias(
            session,
            project_id=project_id,
            alias_name=seed.raw_name,
            report_id=report.id,
            notes="Bootstrap alias captured from uploaded annual report row.",
        )
    for alias_name in seed.aliases:
        await _ensure_alias(
            session,
            project_id=project_id,
            alias_name=alias_name,
            report_id=report.id,
            notes="Bootstrap alias captured from uploaded annual report row.",
        )
    return project_id, seed.match_existing_name is None and matched_project is None


async def _merge_exact_duplicates_for_seed(session, report: Report, seed: CandidateSeed) -> None:
    projects = await _list_exact_projects(session, report.company_id, seed.canonical_name)
    if len(projects) <= 1:
        return
    winner = projects[0]
    for loser in projects[1:]:
        await merge_admin_projects(
            session,
            winner_project_id=winner.id,
            loser_project_id=loser.id,
            merge_reason=f"Bootstrap dedupe for {seed.canonical_name} from {BOOTSTRAP_BATCH_LABEL}",
        )


async def run_bootstrap() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        summary = {
            "reports_registered": 0,
            "new_projects_created": 0,
            "published_snapshots": 0,
        }
        for report_seed in REPORTS:
            report = await _upsert_report(session, report_seed)
            summary["reports_registered"] += 1
            await run_report_extraction(session, report.id)
            for candidate_seed in report_seed.candidates:
                _, is_new_project = await _publish_seed_candidate(session, report, candidate_seed)
                await _merge_exact_duplicates_for_seed(session, report, candidate_seed)
                summary["published_snapshots"] += 1
                if is_new_project:
                    summary["new_projects_created"] += 1
            await update_admin_report(
                session,
                report.id,
                {
                    "ingestion_status": "published",
                    "notes": f"{report_seed.notes}\nBootstrap batch completed on 2026-03-26.",
                },
            )
            qa = await get_admin_report_qa(session, report.id)
            print(
                f"report company={report_seed.company_name_he} report_id={report.id} "
                f"candidates={qa['summary']['total_candidates'] if qa else 0} "
                f"manual={qa['summary']['manual_candidates'] if qa else 0} "
                f"published={qa['summary']['published_candidates'] if qa else 0}"
            )

        project_count = (
            await session.execute(
                select(ProjectSnapshot.project_id).join(Report, Report.id == ProjectSnapshot.report_id).where(Report.source_label == BOOTSTRAP_BATCH_LABEL)
            )
        ).scalars().all()
        unique_project_count = len({project_id for project_id in project_count})
        snapshot_count = len(project_count)
        print(
            f"bootstrap_complete reports_registered={summary['reports_registered']} "
            f"new_projects_created={summary['new_projects_created']} "
            f"published_snapshots={summary['published_snapshots']} "
            f"canonical_projects_touched={unique_project_count} "
            f"snapshots_from_batch={snapshot_count}"
        )


def main() -> None:
    asyncio.run(run_bootstrap())


if __name__ == "__main__":
    main()
