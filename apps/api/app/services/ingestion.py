from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditLog,
    Company,
    FieldProvenance,
    ParserRunLog,
    ProjectAddress,
    ProjectLandReserveDetail,
    ProjectMaster,
    ProjectMaterialDisclosure,
    ProjectSnapshot,
    ProjectSensitivityScenario,
    ProjectUrbanRenewalDetail,
    Report,
    ReviewQueueItem,
    StagingAddressCandidate,
    StagingFieldCandidate,
    StagingProjectCandidate,
    StagingReport,
    StagingSection,
)
from app.services.extraction_profiles import FAMILY_FIELD_GROUPS
from app.services.identity_ops import get_persisted_candidate_match_suggestions, refresh_candidate_match_suggestions
from app.services.admin_review import _get_placeholder_admin


DIFF_FIELDS = (
    "total_units",
    "marketed_units",
    "sold_units_cumulative",
    "unsold_units",
    "avg_price_per_sqm_cumulative",
    "gross_profit_total_expected",
    "gross_margin_expected_pct",
    "permit_status",
    "project_status",
)

PROJECT_EXTENSION_KEYS = (
    "material_disclosure",
    "sensitivity_scenario",
    "urban_renewal_detail",
    "land_reserve_detail",
)
PILOT_SECTION_KINDS = (
    "construction",
    "planning",
    "completed",
    "land_reserve",
    "urban_renewal",
    "material_project",
)
PILOT_KEY_FIELDS = (
    "city",
    "candidate_lifecycle_stage",
    "candidate_disclosure_level",
    "project_status",
    "permit_status",
    "total_units",
    "marketed_units",
    "sold_units_cumulative",
    "unsold_units",
    "avg_price_per_sqm_cumulative",
    "gross_profit_total_expected",
    "gross_margin_expected_pct",
)

EXTENSION_MODEL_MAP = {
    "material_disclosure": ProjectMaterialDisclosure,
    "sensitivity_scenario": ProjectSensitivityScenario,
    "urban_renewal_detail": ProjectUrbanRenewalDetail,
    "land_reserve_detail": ProjectLandReserveDetail,
}

EXTENSION_ENTITY_TYPE_MAP = {
    "material_disclosure": "material_disclosure",
    "sensitivity_scenario": "sensitivity_scenario",
    "urban_renewal_detail": "urban_renewal_detail",
    "land_reserve_detail": "land_reserve_detail",
}

EXTENSION_COLUMN_MAP = {
    "material_disclosure": {
        "material.financing_institution": "financing_institution",
        "material.facility_amount": "facility_amount",
        "material.utilization_amount": "utilization_amount",
        "material.unused_capacity": "unused_capacity",
        "material.financing_terms": "financing_terms",
        "material.covenants_summary": "covenants_summary",
        "material.non_recourse_flag": "non_recourse_flag",
        "material.surplus_release_conditions": "surplus_release_conditions",
        "material.expected_economic_profit": "expected_economic_profit",
        "material.accounting_to_economic_bridge": "accounting_to_economic_bridge",
        "material.pledged_or_secured_notes": "pledged_or_secured_notes",
        "material.special_project_notes": "special_project_notes",
    },
    "sensitivity_scenario": {
        "sensitivity.sales_price_plus_5_effect": "sales_price_plus_5_effect",
        "sensitivity.sales_price_plus_10_effect": "sales_price_plus_10_effect",
        "sensitivity.sales_price_minus_5_effect": "sales_price_minus_5_effect",
        "sensitivity.sales_price_minus_10_effect": "sales_price_minus_10_effect",
        "sensitivity.construction_cost_plus_5_effect": "construction_cost_plus_5_effect",
        "sensitivity.construction_cost_plus_10_effect": "construction_cost_plus_10_effect",
        "sensitivity.construction_cost_minus_5_effect": "construction_cost_minus_5_effect",
        "sensitivity.construction_cost_minus_10_effect": "construction_cost_minus_10_effect",
        "sensitivity.base_gross_profit_not_yet_recognized": "base_gross_profit_not_yet_recognized",
    },
    "urban_renewal_detail": {
        "urban_renewal.existing_units": "existing_units",
        "urban_renewal.future_units_total": "future_units_total",
        "urban_renewal.future_units_marketed_by_company": "future_units_marketed_by_company",
        "urban_renewal.future_units_for_existing_tenants": "future_units_for_existing_tenants",
        "urban_renewal.tenant_signature_rate": "tenant_signature_rate",
        "urban_renewal.signature_timeline": "signature_timeline",
        "urban_renewal.average_exchange_ratio_signed": "average_exchange_ratio_signed",
        "urban_renewal.average_exchange_ratio_unsigned": "average_exchange_ratio_unsigned",
        "urban_renewal.tenant_relocation_or_demolition_cost": "tenant_relocation_or_demolition_cost",
        "urban_renewal.execution_dependencies": "execution_dependencies",
        "urban_renewal.planning_status_text": "planning_status_text",
        "urban_renewal.accounting_treatment_summary": "accounting_treatment_summary",
    },
    "land_reserve_detail": {
        "land_reserve.land_area_sqm": "land_area_sqm",
        "land_reserve.historical_cost": "historical_cost",
        "land_reserve.financing_cost": "financing_cost",
        "land_reserve.planning_cost": "planning_cost",
        "land_reserve.carrying_value": "carrying_value",
        "land_reserve.current_planning_status": "current_planning_status",
        "land_reserve.requested_planning_status": "requested_planning_status",
        "land_reserve.intended_units": "intended_units",
        "land_reserve.intended_uses": "intended_uses",
    },
}


def _confidence_score(level: str) -> Decimal:
    return {
        "high": Decimal("95.00"),
        "medium": Decimal("78.00"),
        "low": Decimal("55.00"),
    }.get(level, Decimal("55.00"))


def _sanitize_candidate_values(payload: dict) -> dict:
    values = dict(payload)
    project_business_type = values.get("project_business_type")
    if project_business_type != "govt_program":
        values["government_program_type"] = "none"
    if project_business_type != "urban_renewal":
        values["project_urban_renewal_type"] = "none"
    return values


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


def _parse_numeric(value: str | None) -> Decimal | None:
    if value is None:
        return None
    compact = value.replace(",", "").strip()
    if not compact:
        return None
    try:
        return Decimal(compact)
    except Exception:
        return None


def _parse_int(value: str | None) -> int | None:
    numeric = _parse_numeric(value)
    return int(numeric) if numeric is not None else None


def _coerce_extension_value(column_name: str, value: str | None) -> object | None:
    if value is None:
        return None
    int_fields = {
        "existing_units",
        "future_units_total",
        "future_units_marketed_by_company",
        "future_units_for_existing_tenants",
        "intended_units",
    }
    numeric_fields = {
        "facility_amount",
        "utilization_amount",
        "unused_capacity",
        "expected_economic_profit",
        "sales_price_plus_5_effect",
        "sales_price_plus_10_effect",
        "sales_price_minus_5_effect",
        "sales_price_minus_10_effect",
        "construction_cost_plus_5_effect",
        "construction_cost_plus_10_effect",
        "construction_cost_minus_5_effect",
        "construction_cost_minus_10_effect",
        "base_gross_profit_not_yet_recognized",
        "tenant_signature_rate",
        "average_exchange_ratio_signed",
        "average_exchange_ratio_unsigned",
        "tenant_relocation_or_demolition_cost",
        "land_area_sqm",
        "historical_cost",
        "financing_cost",
        "planning_cost",
        "carrying_value",
    }
    if column_name == "non_recourse_flag":
        return _parse_bool(value)
    if column_name in int_fields:
        return _parse_int(value)
    if column_name in numeric_fields:
        return _parse_numeric(value)
    return value


async def _record_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID,
    diff_json: dict | None,
    comment: str | None,
    actor_user_id: UUID,
) -> None:
    session.add(
        AdminAuditLog(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            diff_json=jsonable_encoder(diff_json) if diff_json is not None else None,
            comment=comment,
            created_at=datetime.now(UTC),
        )
    )


async def _get_report(session: AsyncSession, report_id: UUID) -> Report | None:
    return (await session.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()


async def _get_staging_report(session: AsyncSession, report: Report) -> StagingReport:
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
    return staging_report


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
    else:
        item.status = status
        item.notes = notes


async def _latest_snapshot(session: AsyncSession, project_id: UUID) -> ProjectSnapshot | None:
    return (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _previous_snapshot(session: AsyncSession, project_id: UUID, report_id: UUID) -> ProjectSnapshot | None:
    return (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project_id, ProjectSnapshot.report_id != report_id)
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _candidate_children(session: AsyncSession, candidate_id: UUID) -> tuple[list[StagingFieldCandidate], list[StagingAddressCandidate]]:
    field_candidates = (
        await session.execute(
            select(StagingFieldCandidate)
            .where(StagingFieldCandidate.candidate_id == candidate_id)
            .order_by(StagingFieldCandidate.created_at.asc())
        )
    ).scalars().all()
    address_candidates = (
        await session.execute(
            select(StagingAddressCandidate)
            .where(StagingAddressCandidate.candidate_id == candidate_id)
            .order_by(StagingAddressCandidate.created_at.asc())
        )
    ).scalars().all()
    return field_candidates, address_candidates


def _serialize_candidate_summary(candidate: StagingProjectCandidate, matched_project_name: str | None) -> dict:
    return {
        "id": candidate.id,
        "candidate_project_name": candidate.candidate_project_name,
        "city": candidate.city,
        "neighborhood": candidate.neighborhood,
        "candidate_lifecycle_stage": candidate.candidate_lifecycle_stage,
        "candidate_disclosure_level": candidate.candidate_disclosure_level,
        "candidate_section_kind": candidate.candidate_section_kind,
        "matching_status": candidate.matching_status,
        "publish_status": candidate.publish_status,
        "confidence_level": candidate.confidence_level,
        "review_status": candidate.review_status,
        "matched_project_id": candidate.matched_project_id,
        "matched_project_name": matched_project_name,
        "review_notes": candidate.review_notes,
        "diff_summary": candidate.diff_summary,
    }


async def list_admin_reports(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(Report, Company, StagingReport)
            .join(Company, Company.id == Report.company_id)
            .outerjoin(StagingReport, StagingReport.report_id == Report.id)
            .order_by(Report.period_end_date.desc(), Report.publish_date.desc().nullslast(), Company.name_he.asc())
        )
    ).all()
    items: list[dict] = []
    for report, company, staging_report in rows:
        candidate_count = int(
            (
                await session.execute(
                    select(func.count()).select_from(StagingProjectCandidate).where(
                        StagingProjectCandidate.staging_report_id == (staging_report.id if staging_report else UUID(int=0))
                    )
                )
            ).scalar_one()
            if staging_report
            else 0
        )
        items.append(
            {
                "id": report.id,
                "company_id": company.id,
                "company_name_he": company.name_he,
                "report_name": report.filing_reference,
                "report_type": report.report_type,
                "period_type": report.period_type,
                "period_end_date": report.period_end_date,
                "published_at": report.publish_date,
                "source_url": report.source_url,
                "source_file_path": report.source_file_path,
                "source_is_official": report.source_is_official,
                "source_label": report.source_label,
                "ingestion_status": report.ingestion_status,
                "notes": report.notes,
                "candidate_count": candidate_count,
                "created_at": report.created_at,
                "updated_at": report.updated_at,
            }
        )
    return items


async def create_admin_report(session: AsyncSession, payload: dict) -> dict:
    admin_user = await _get_placeholder_admin(session)
    report = Report(
        id=uuid4(),
        company_id=payload["company_id"],
        report_type=payload["report_type"],
        period_type=payload["period_type"],
        period_end_date=payload["period_end_date"],
        publish_date=payload.get("published_at"),
        filing_reference=payload["report_name"],
        source_url=payload.get("source_url"),
        source_file_path=payload.get("source_file_path"),
        source_is_official=payload.get("source_is_official", False),
        source_label=payload.get("source_label"),
        ingestion_status=payload.get("ingestion_status", "draft"),
        notes=payload.get("notes"),
        parser_version="manual_bridge_v1",
        status="reviewed",
    )
    session.add(report)
    await session.flush()
    staging_report = await _get_staging_report(session, report)
    await _sync_report_queue(session, report.id, None, "open", "Report created for manual staging")
    await _record_audit(
        session,
        action="admin_report_create",
        entity_type="report",
        entity_id=report.id,
        diff_json=payload,
        comment=payload.get("notes"),
        actor_user_id=admin_user.id,
    )
    await session.commit()
    return await get_admin_report_detail(session, report.id) or {"id": report.id, "staging_report_id": staging_report.id}


async def _report_candidates_summary(session: AsyncSession, staging_report_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            select(StagingProjectCandidate, ProjectMaster.canonical_name)
            .outerjoin(ProjectMaster, ProjectMaster.id == StagingProjectCandidate.matched_project_id)
            .where(StagingProjectCandidate.staging_report_id == staging_report_id)
            .order_by(StagingProjectCandidate.created_at.asc())
        )
    ).all()
    return [_serialize_candidate_summary(candidate, canonical_name) for candidate, canonical_name in rows]


async def get_admin_report_detail(session: AsyncSession, report_id: UUID) -> dict | None:
    row = (
        await session.execute(
            select(Report, Company, StagingReport)
            .join(Company, Company.id == Report.company_id)
            .outerjoin(StagingReport, StagingReport.report_id == Report.id)
            .where(Report.id == report_id)
        )
    ).first()
    if row is None:
        return None

    report, company, staging_report = row
    staging_report = staging_report or await _get_staging_report(session, report)
    candidates = await _report_candidates_summary(session, staging_report.id)
    return {
        "id": report.id,
        "company_id": company.id,
        "company_name_he": company.name_he,
        "report_name": report.filing_reference,
        "report_type": report.report_type,
        "period_type": report.period_type,
        "period_end_date": report.period_end_date,
        "published_at": report.publish_date,
        "source_url": report.source_url,
        "source_file_path": report.source_file_path,
        "source_is_official": report.source_is_official,
        "source_label": report.source_label,
        "ingestion_status": report.ingestion_status,
        "notes": report.notes,
        "candidate_count": len(candidates),
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "staging_report_id": staging_report.id,
        "staging_publish_status": staging_report.publish_status,
        "staging_review_status": staging_report.review_status,
        "staging_notes_internal": staging_report.notes_internal,
        "candidates": candidates,
    }


async def get_admin_report_qa(session: AsyncSession, report_id: UUID) -> dict | None:
    report = await _get_report(session, report_id)
    if report is None:
        return None

    staging_report = await _get_staging_report(session, report)
    sections = (
        await session.execute(
            select(StagingSection)
            .where(StagingSection.staging_report_id == staging_report.id)
            .order_by(StagingSection.source_page_from.asc().nullslast(), StagingSection.created_at.asc())
        )
    ).scalars().all()
    candidates = (
        await session.execute(
            select(StagingProjectCandidate)
            .where(StagingProjectCandidate.staging_report_id == staging_report.id)
            .order_by(StagingProjectCandidate.created_at.asc())
        )
    ).scalars().all()

    latest_parser_run = (
        await session.execute(
            select(ParserRunLog)
            .where(ParserRunLog.report_id == report.id)
            .order_by(ParserRunLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    lifecycle_distribution = Counter(candidate.candidate_lifecycle_stage or "unknown" for candidate in candidates)
    disclosure_distribution = Counter(candidate.candidate_disclosure_level or "unknown" for candidate in candidates)
    missing_field_counts = Counter(
        field_name
        for candidate in candidates
        for field_name in PILOT_KEY_FIELDS
        if getattr(candidate, field_name) is None
    )
    section_count_by_kind = Counter(section.section_kind or "summary_only" for section in sections)
    candidates_by_kind = Counter(candidate.candidate_section_kind or "summary_only" for candidate in candidates)
    matched_by_kind = Counter(
        candidate.candidate_section_kind or "summary_only"
        for candidate in candidates
        if candidate.matching_status == "matched_existing_project"
    )
    new_by_kind = Counter(
        candidate.candidate_section_kind or "summary_only"
        for candidate in candidates
        if candidate.matching_status == "new_project_needed"
    )
    ambiguous_by_kind = Counter(
        candidate.candidate_section_kind or "summary_only"
        for candidate in candidates
        if candidate.matching_status == "ambiguous_match"
    )
    ignored_by_kind = Counter(
        candidate.candidate_section_kind or "summary_only"
        for candidate in candidates
        if candidate.matching_status == "ignored"
    )

    return {
        "report_id": report.id,
        "summary": {
            "total_candidates": len(candidates),
            "projects_detected": len(
                {
                    candidate.candidate_project_name.strip().lower()
                    for candidate in candidates
                    if candidate.candidate_project_name.strip()
                }
            ),
            "matched_existing_projects": sum(
                1 for candidate in candidates if candidate.matching_status == "matched_existing_project"
            ),
            "new_projects_needed": sum(
                1 for candidate in candidates if candidate.matching_status == "new_project_needed"
            ),
            "ambiguous_candidates": sum(
                1 for candidate in candidates if candidate.matching_status == "ambiguous_match"
            ),
            "rejected_or_ignored_candidates": sum(
                1 for candidate in candidates if candidate.matching_status == "ignored"
            ),
            "published_candidates": sum(
                1 for candidate in candidates if candidate.publish_status == "published"
            ),
            "missing_key_field_total": sum(missing_field_counts.values()),
            "latest_parser_sections_found": latest_parser_run.sections_found if latest_parser_run else 0,
            "latest_parser_candidate_count": latest_parser_run.candidate_count if latest_parser_run else 0,
        },
        "lifecycle_stage_distribution": [
            {"key": key, "count": count}
            for key, count in sorted(lifecycle_distribution.items(), key=lambda item: (-item[1], item[0]))
        ],
        "disclosure_level_distribution": [
            {"key": key, "count": count}
            for key, count in sorted(disclosure_distribution.items(), key=lambda item: (-item[1], item[0]))
        ],
        "family_coverage": [
            {
                "section_kind": section_kind,
                "section_count": section_count_by_kind.get(section_kind, 0),
                "candidate_count": candidates_by_kind.get(section_kind, 0),
                "matched_existing_count": matched_by_kind.get(section_kind, 0),
                "new_project_count": new_by_kind.get(section_kind, 0),
                "ambiguous_count": ambiguous_by_kind.get(section_kind, 0),
                "ignored_count": ignored_by_kind.get(section_kind, 0),
            }
            for section_kind in PILOT_SECTION_KINDS
        ],
        "missing_key_fields": [
            {"field_name": field_name, "missing_count": count}
            for field_name, count in sorted(missing_field_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "latest_parser_run": (
            {
                "id": latest_parser_run.id,
                "report_id": latest_parser_run.report_id,
                "staging_report_id": latest_parser_run.staging_report_id,
                "status": latest_parser_run.status,
                "parser_version": latest_parser_run.parser_version,
                "source_label": latest_parser_run.source_label,
                "source_reference": latest_parser_run.source_reference,
                "source_checksum": latest_parser_run.source_checksum,
                "sections_found": latest_parser_run.sections_found,
                "candidate_count": latest_parser_run.candidate_count,
                "field_candidate_count": latest_parser_run.field_candidate_count,
                "address_candidate_count": latest_parser_run.address_candidate_count,
                "warnings": list(latest_parser_run.warnings_json or []),
                "errors": list(latest_parser_run.errors_json or []),
                "diagnostics": dict(latest_parser_run.diagnostics_json or {}),
                "started_at": latest_parser_run.started_at,
                "finished_at": latest_parser_run.finished_at,
                "created_at": latest_parser_run.created_at,
                "updated_at": latest_parser_run.updated_at,
            }
            if latest_parser_run
            else None
        ),
    }


async def update_admin_report(session: AsyncSession, report_id: UUID, payload: dict) -> dict | None:
    report = await _get_report(session, report_id)
    if report is None:
        return None

    staging_report = await _get_staging_report(session, report)
    admin_user = await _get_placeholder_admin(session)
    diffs: dict[str, dict[str, object | None]] = {}
    report_field_map = {
        "report_name": "filing_reference",
        "published_at": "publish_date",
        "source_url": "source_url",
        "source_file_path": "source_file_path",
        "source_is_official": "source_is_official",
        "source_label": "source_label",
        "ingestion_status": "ingestion_status",
        "notes": "notes",
        "report_type": "report_type",
        "period_type": "period_type",
        "period_end_date": "period_end_date",
    }
    for payload_key, model_field in report_field_map.items():
        if payload_key in payload and getattr(report, model_field) != payload[payload_key]:
            diffs[payload_key] = {"before": getattr(report, model_field), "after": payload[payload_key]}
            setattr(report, model_field, payload[payload_key])

    staging_field_map = {
        "staging_publish_status": "publish_status",
        "staging_review_status": "review_status",
        "staging_notes_internal": "notes_internal",
    }
    for payload_key, model_field in staging_field_map.items():
        if payload_key in payload and getattr(staging_report, model_field) != payload[payload_key]:
            diffs[payload_key] = {"before": getattr(staging_report, model_field), "after": payload[payload_key]}
            setattr(staging_report, model_field, payload[payload_key])

    if report.ingestion_status == "ready_for_staging":
        await _sync_report_queue(session, report.id, None, "open", "Report marked ready for staging")

    if diffs:
        await _record_audit(
            session,
            action="admin_report_update",
            entity_type="report",
            entity_id=report.id,
            diff_json=diffs,
            comment=payload.get("notes"),
            actor_user_id=admin_user.id,
        )
        await session.commit()
    else:
        await session.rollback()
    return await get_admin_report_detail(session, report_id)


async def list_report_candidates(session: AsyncSession, report_id: UUID) -> list[dict]:
    detail = await get_admin_report_detail(session, report_id)
    return [] if detail is None else detail["candidates"]


async def _replace_candidate_children(session: AsyncSession, candidate_id: UUID, payload: dict) -> None:
    if "field_candidates" in payload and payload["field_candidates"] is not None:
        await session.execute(delete(StagingFieldCandidate).where(StagingFieldCandidate.candidate_id == candidate_id))
        for item in payload["field_candidates"]:
            session.add(
                StagingFieldCandidate(
                    id=item.get("id") or uuid4(),
                    candidate_id=candidate_id,
                    field_name=item["field_name"],
                    raw_value=item.get("raw_value"),
                    normalized_value=item.get("normalized_value"),
                    source_page=item.get("source_page"),
                    source_section=item.get("source_section"),
                    source_table_name=item.get("source_table_name"),
                    source_row_label=item.get("source_row_label"),
                    extraction_profile_key=item.get("extraction_profile_key"),
                    value_origin_type=item.get("value_origin_type", "manual"),
                    confidence_level=item.get("confidence_level", "medium"),
                    review_status=item.get("review_status", "pending"),
                    review_notes=item.get("review_notes"),
                )
            )

    if "address_candidates" in payload and payload["address_candidates"] is not None:
        await session.execute(delete(StagingAddressCandidate).where(StagingAddressCandidate.candidate_id == candidate_id))
        for item in payload["address_candidates"]:
            session.add(
                StagingAddressCandidate(
                    id=item.get("id") or uuid4(),
                    candidate_id=candidate_id,
                    address_text_raw=item.get("address_text_raw"),
                    street=item.get("street"),
                    house_number_from=item.get("house_number_from"),
                    house_number_to=item.get("house_number_to"),
                    city=item.get("city"),
                    lat=item.get("lat"),
                    lng=item.get("lng"),
                    location_confidence=item.get("location_confidence", "unknown"),
                    is_primary=item.get("is_primary", False),
                    value_origin_type=item.get("value_origin_type", "manual"),
                    confidence_level=item.get("confidence_level", "medium"),
                    review_status=item.get("review_status", "pending"),
                    review_notes=item.get("review_notes"),
                )
            )


async def create_candidate(session: AsyncSession, report_id: UUID, payload: dict) -> dict | None:
    report = await _get_report(session, report_id)
    if report is None:
        return None

    staging_report = await _get_staging_report(session, report)
    admin_user = await _get_placeholder_admin(session)
    values = _sanitize_candidate_values(payload)
    candidate = StagingProjectCandidate(
        id=uuid4(),
        staging_report_id=staging_report.id,
        company_id=report.company_id,
        staging_section_id=values.get("staging_section_id"),
        candidate_project_name=values["candidate_project_name"],
        city=values.get("city"),
        neighborhood=values.get("neighborhood"),
        candidate_lifecycle_stage=values.get("candidate_lifecycle_stage"),
        candidate_disclosure_level=values.get("candidate_disclosure_level"),
        candidate_section_kind=values.get("candidate_section_kind"),
        candidate_materiality_flag=values.get("candidate_materiality_flag"),
        source_table_name=values.get("source_table_name"),
        source_row_label=values.get("source_row_label"),
        extraction_profile_key=values.get("extraction_profile_key"),
        project_business_type=values.get("project_business_type"),
        government_program_type=values.get("government_program_type", "none"),
        project_urban_renewal_type=values.get("project_urban_renewal_type", "none"),
        project_status=values.get("project_status"),
        permit_status=values.get("permit_status"),
        total_units=values.get("total_units"),
        marketed_units=values.get("marketed_units"),
        sold_units_cumulative=values.get("sold_units_cumulative"),
        unsold_units=values.get("unsold_units"),
        avg_price_per_sqm_cumulative=values.get("avg_price_per_sqm_cumulative"),
        gross_profit_total_expected=values.get("gross_profit_total_expected"),
        gross_margin_expected_pct=values.get("gross_margin_expected_pct"),
        location_confidence=values.get("location_confidence", "unknown"),
        value_origin_type=values.get("value_origin_type", "manual"),
        confidence_level=values.get("confidence_level", "medium"),
        review_status=values.get("review_status", "pending"),
        review_notes=values.get("review_notes"),
    )
    session.add(candidate)
    await session.flush()
    await _replace_candidate_children(session, candidate.id, values)
    await _sync_report_queue(session, report.id, candidate.id, "open", "Candidate created for review")
    report.ingestion_status = "in_review"
    staging_report.review_status = "pending"
    await _record_audit(
        session,
        action="staging_candidate_create",
        entity_type="staging_project_candidate",
        entity_id=candidate.id,
        diff_json=values,
        comment=values.get("review_notes"),
        actor_user_id=admin_user.id,
    )
    await refresh_candidate_match_suggestions(session, candidate)
    await session.commit()
    return await get_candidate_detail(session, candidate.id)


def _candidate_field_lookup(field_candidates: list[StagingFieldCandidate]) -> dict[str, StagingFieldCandidate]:
    lookup: dict[str, StagingFieldCandidate] = {}
    for item in field_candidates:
        if item.field_name not in lookup:
            lookup[item.field_name] = item
    return lookup


def _collect_extension_payloads(field_candidates: list[StagingFieldCandidate]) -> dict[str, dict[str, tuple[object | None, StagingFieldCandidate]]]:
    payloads: dict[str, dict[str, tuple[object | None, StagingFieldCandidate]]] = {key: {} for key in PROJECT_EXTENSION_KEYS}
    for field_candidate in field_candidates:
        for family_key, allowed_fields in FAMILY_FIELD_GROUPS.items():
            if field_candidate.field_name not in allowed_fields:
                continue
            column_name = EXTENSION_COLUMN_MAP[family_key][field_candidate.field_name]
            payloads[family_key][column_name] = (
                _coerce_extension_value(column_name, field_candidate.normalized_value or field_candidate.raw_value),
                field_candidate,
            )
    return payloads


async def _upsert_project_extension_rows(
    session: AsyncSession,
    *,
    project: ProjectMaster,
    snapshot: ProjectSnapshot,
    report_id: UUID,
    field_candidates: list[StagingFieldCandidate],
) -> dict[str, dict[str, object | None]]:
    payloads = _collect_extension_payloads(field_candidates)
    result: dict[str, dict[str, object | None]] = {}
    for family_key, values in payloads.items():
        if not values:
            continue
        model = EXTENSION_MODEL_MAP[family_key]
        row = (
            await session.execute(
                select(model).where(model.project_id == project.id, model.snapshot_id == snapshot.id)  # type: ignore[attr-defined]
            )
        ).scalar_one_or_none()
        if row is None:
            row = model(id=uuid4(), project_id=project.id, snapshot_id=snapshot.id, report_id=report_id)  # type: ignore[call-arg]
            session.add(row)
        for column_name, (value, _) in values.items():
            setattr(row, column_name, value)
        result[family_key] = {column_name: value for column_name, (value, _) in values.items()}
    return result


def _serialize_extension_row(row: object | None, family_key: str) -> dict[str, object | None] | None:
    if row is None:
        return None
    columns = EXTENSION_COLUMN_MAP[family_key].values()
    return {column_name: getattr(row, column_name) for column_name in columns if getattr(row, column_name) is not None}


async def _candidate_compare_rows(
    session: AsyncSession,
    candidate: StagingProjectCandidate,
    field_candidates: list[StagingFieldCandidate],
) -> list[dict]:
    matched_project = None
    latest_snapshot = None
    if candidate.matched_project_id:
        matched_project = (
            await session.execute(select(ProjectMaster).where(ProjectMaster.id == candidate.matched_project_id))
        ).scalar_one_or_none()
        if matched_project is not None:
            latest_snapshot = await _latest_snapshot(session, matched_project.id)

    field_lookup = _candidate_field_lookup(field_candidates)
    compare_fields = (
        ("canonical_name", getattr(matched_project, "canonical_name", None), candidate.candidate_project_name),
        ("city", getattr(matched_project, "city", None), candidate.city),
        ("neighborhood", getattr(matched_project, "neighborhood", None), candidate.neighborhood),
        ("lifecycle_stage", getattr(matched_project, "lifecycle_stage", None), candidate.candidate_lifecycle_stage),
        ("disclosure_level", getattr(matched_project, "disclosure_level", None), candidate.candidate_disclosure_level),
        ("project_business_type", getattr(matched_project, "project_business_type", None), candidate.project_business_type),
        ("government_program_type", getattr(matched_project, "government_program_type", None), candidate.government_program_type),
        ("project_urban_renewal_type", getattr(matched_project, "project_urban_renewal_type", None), candidate.project_urban_renewal_type),
        ("source_section_kind", getattr(latest_snapshot, "source_section_kind", None), candidate.candidate_section_kind),
        ("project_status", getattr(latest_snapshot, "project_status", None), candidate.project_status),
        ("permit_status", getattr(latest_snapshot, "permit_status", None), candidate.permit_status),
        ("total_units", getattr(latest_snapshot, "total_units", None), candidate.total_units),
        ("marketed_units", getattr(latest_snapshot, "marketed_units", None), candidate.marketed_units),
        ("sold_units_cumulative", getattr(latest_snapshot, "sold_units_cumulative", None), candidate.sold_units_cumulative),
        ("unsold_units", getattr(latest_snapshot, "unsold_units", None), candidate.unsold_units),
        ("avg_price_per_sqm_cumulative", getattr(latest_snapshot, "avg_price_per_sqm_cumulative", None), candidate.avg_price_per_sqm_cumulative),
        ("gross_profit_total_expected", getattr(latest_snapshot, "gross_profit_total_expected", None), candidate.gross_profit_total_expected),
        ("gross_margin_expected_pct", getattr(latest_snapshot, "gross_margin_expected_pct", None), candidate.gross_margin_expected_pct),
    )
    rows: list[dict] = []
    for field_name, canonical_value, staging_value in compare_fields:
        field_candidate = field_lookup.get(field_name)
        rows.append(
            {
                "field_name": field_name,
                "canonical_value": None if canonical_value is None else str(canonical_value),
                "staging_value": None if staging_value is None else str(staging_value),
                "raw_source_value": field_candidate.raw_value if field_candidate else None,
                "source_page": field_candidate.source_page if field_candidate else None,
                "source_section": field_candidate.source_section if field_candidate else None,
                "value_origin_type": field_candidate.value_origin_type if field_candidate else candidate.value_origin_type,
                "confidence_level": field_candidate.confidence_level if field_candidate else candidate.confidence_level,
                "changed": (None if canonical_value is None else str(canonical_value))
                != (None if staging_value is None else str(staging_value)),
            }
        )
    return rows


def _diff_summary(compare_rows: list[dict]) -> list[dict]:
    return [
        {
            "field_name": row["field_name"],
            "previous_value": row["canonical_value"],
            "incoming_value": row["staging_value"],
            "changed": row["changed"],
        }
        for row in compare_rows
        if row["field_name"] in DIFF_FIELDS
    ]


async def get_candidate_detail(session: AsyncSession, candidate_id: UUID) -> dict | None:
    row = (
        await session.execute(
            select(StagingProjectCandidate, StagingReport, Report, Company, ProjectMaster.canonical_name)
            .join(StagingReport, StagingReport.id == StagingProjectCandidate.staging_report_id)
            .join(Report, Report.id == StagingReport.report_id)
            .join(Company, Company.id == StagingProjectCandidate.company_id)
            .outerjoin(ProjectMaster, ProjectMaster.id == StagingProjectCandidate.matched_project_id)
            .where(StagingProjectCandidate.id == candidate_id)
        )
    ).first()
    if row is None:
        return None

    candidate, staging_report, report, company, matched_project_name = row
    field_candidates, address_candidates = await _candidate_children(session, candidate.id)
    await refresh_candidate_match_suggestions(session, candidate)
    compare_rows = await _candidate_compare_rows(session, candidate, field_candidates)
    diff_summary = _diff_summary(compare_rows)
    extension_payloads = _collect_extension_payloads(field_candidates)
    candidate.diff_summary = {item["field_name"]: item["changed"] for item in diff_summary if item["changed"]}
    await session.flush()
    return {
        "id": candidate.id,
        "staging_report_id": staging_report.id,
        "report_id": report.id,
        "company_id": company.id,
        "company_name_he": company.name_he,
        "candidate_project_name": candidate.candidate_project_name,
        "city": candidate.city,
        "neighborhood": candidate.neighborhood,
        "candidate_lifecycle_stage": candidate.candidate_lifecycle_stage,
        "candidate_disclosure_level": candidate.candidate_disclosure_level,
        "candidate_section_kind": candidate.candidate_section_kind,
        "candidate_materiality_flag": candidate.candidate_materiality_flag,
        "source_table_name": candidate.source_table_name,
        "source_row_label": candidate.source_row_label,
        "extraction_profile_key": candidate.extraction_profile_key,
        "project_business_type": candidate.project_business_type,
        "government_program_type": candidate.government_program_type,
        "project_urban_renewal_type": candidate.project_urban_renewal_type,
        "project_status": candidate.project_status,
        "permit_status": candidate.permit_status,
        "total_units": candidate.total_units,
        "marketed_units": candidate.marketed_units,
        "sold_units_cumulative": candidate.sold_units_cumulative,
        "unsold_units": candidate.unsold_units,
        "avg_price_per_sqm_cumulative": candidate.avg_price_per_sqm_cumulative,
        "gross_profit_total_expected": candidate.gross_profit_total_expected,
        "gross_margin_expected_pct": candidate.gross_margin_expected_pct,
        "location_confidence": candidate.location_confidence,
        "value_origin_type": candidate.value_origin_type,
        "confidence_level": candidate.confidence_level,
        "matching_status": candidate.matching_status,
        "publish_status": candidate.publish_status,
        "review_status": candidate.review_status,
        "review_notes": candidate.review_notes,
        "matched_project_id": candidate.matched_project_id,
        "matched_project_name": matched_project_name,
        "field_candidates": [
            {
                "id": item.id,
                "field_name": item.field_name,
                "raw_value": item.raw_value,
                "normalized_value": item.normalized_value,
                "source_page": item.source_page,
                "source_section": item.source_section,
                "source_table_name": item.source_table_name,
                "source_row_label": item.source_row_label,
                "extraction_profile_key": item.extraction_profile_key,
                "value_origin_type": item.value_origin_type,
                "confidence_level": item.confidence_level,
                "review_status": item.review_status,
                "review_notes": item.review_notes,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in field_candidates
        ],
        "address_candidates": [
            {
                "id": item.id,
                "address_text_raw": item.address_text_raw,
                "street": item.street,
                "house_number_from": item.house_number_from,
                "house_number_to": item.house_number_to,
                "city": item.city,
                "lat": item.lat,
                "lng": item.lng,
                "location_confidence": item.location_confidence,
                "is_primary": item.is_primary,
                "value_origin_type": item.value_origin_type,
                "confidence_level": item.confidence_level,
                "review_status": item.review_status,
                "review_notes": item.review_notes,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in address_candidates
        ],
        "match_suggestions": await get_persisted_candidate_match_suggestions(session, candidate.id),
        "compare_rows": compare_rows,
        "diff_summary": diff_summary,
        "extension_blocks": {
            family_key: {
                column_name: value
                for column_name, (value, _) in values.items()
                if value is not None
            }
            for family_key, values in extension_payloads.items()
            if values
        },
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
    }


async def update_candidate(session: AsyncSession, candidate_id: UUID, payload: dict) -> dict | None:
    candidate = (
        await session.execute(select(StagingProjectCandidate).where(StagingProjectCandidate.id == candidate_id))
    ).scalar_one_or_none()
    if candidate is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    values = _sanitize_candidate_values(payload)
    diffs: dict[str, dict[str, object | None]] = {}
    for field_name in (
        "candidate_project_name",
        "city",
        "neighborhood",
        "candidate_lifecycle_stage",
        "candidate_disclosure_level",
        "candidate_section_kind",
        "candidate_materiality_flag",
        "source_table_name",
        "source_row_label",
        "extraction_profile_key",
        "project_business_type",
        "government_program_type",
        "project_urban_renewal_type",
        "project_status",
        "permit_status",
        "total_units",
        "marketed_units",
        "sold_units_cumulative",
        "unsold_units",
        "avg_price_per_sqm_cumulative",
        "gross_profit_total_expected",
        "gross_margin_expected_pct",
        "location_confidence",
        "value_origin_type",
        "confidence_level",
        "matching_status",
        "publish_status",
        "review_status",
        "review_notes",
        "matched_project_id",
    ):
        if field_name in values and getattr(candidate, field_name) != values[field_name]:
            diffs[field_name] = {"before": getattr(candidate, field_name), "after": values[field_name]}
            setattr(candidate, field_name, values[field_name])

    await _replace_candidate_children(session, candidate_id, values)
    await refresh_candidate_match_suggestions(session, candidate)
    await _record_audit(
        session,
        action="staging_candidate_update",
        entity_type="staging_project_candidate",
        entity_id=candidate.id,
        diff_json=diffs if diffs else values,
        comment=values.get("review_notes"),
        actor_user_id=admin_user.id,
    )
    await session.commit()
    return await get_candidate_detail(session, candidate_id)


async def match_candidate(session: AsyncSession, candidate_id: UUID, payload: dict) -> dict | None:
    candidate = (
        await session.execute(select(StagingProjectCandidate).where(StagingProjectCandidate.id == candidate_id))
    ).scalar_one_or_none()
    if candidate is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    candidate.matching_status = payload["match_status"]
    candidate.matched_project_id = payload.get("matched_project_id")
    if candidate.matching_status not in {"matched_existing_project", "new_project_needed"}:
        candidate.matched_project_id = None
    candidate.review_status = "approved" if candidate.matching_status in {"matched_existing_project", "new_project_needed", "ignored"} else "pending"
    await refresh_candidate_match_suggestions(session, candidate)
    report_id = (
        await session.execute(select(StagingReport.report_id).where(StagingReport.id == candidate.staging_report_id))
    ).scalar_one()
    await _sync_report_queue(
        session,
        report_id,
        candidate.id,
        "in_progress" if candidate.matching_status in {"matched_existing_project", "new_project_needed"} else "open",
        payload.get("reviewer_note"),
    )
    await _record_audit(
        session,
        action="staging_candidate_match",
        entity_type="staging_project_candidate",
        entity_id=candidate.id,
        diff_json={"matching_status": candidate.matching_status, "matched_project_id": candidate.matched_project_id},
        comment=payload.get("reviewer_note"),
        actor_user_id=admin_user.id,
    )
    await session.commit()
    return await get_candidate_detail(session, candidate.id)


async def _upsert_project_address_from_candidate(
    session: AsyncSession,
    *,
    project_id: UUID,
    address_candidate: StagingAddressCandidate,
    admin_user_id: UUID,
    report_id: UUID,
    reviewer_note: str | None,
) -> ProjectAddress:
    existing_addresses = (
        await session.execute(select(ProjectAddress).where(ProjectAddress.project_id == project_id))
    ).scalars().all()
    match = next(
        (
            address
            for address in existing_addresses
            if address.city == address_candidate.city
            and address.street == address_candidate.street
            and address.address_text_raw == address_candidate.address_text_raw
        ),
        None,
    )
    address = match or ProjectAddress(
        id=uuid4(),
        project_id=project_id,
        source_type="admin",
        assigned_by=admin_user_id,
        assigned_at=datetime.now(UTC),
    )
    if match is None:
        session.add(address)

    address.address_text_raw = address_candidate.address_text_raw
    address.street = address_candidate.street
    address.house_number_from = address_candidate.house_number_from
    address.house_number_to = address_candidate.house_number_to
    address.city = address_candidate.city
    address.lat = address_candidate.lat
    address.lng = address_candidate.lng
    address.location_confidence = address_candidate.location_confidence
    address.is_primary = address_candidate.is_primary
    if address_candidate.is_primary:
        for other_address in existing_addresses:
            if other_address.id != address.id:
                other_address.is_primary = False

    await session.flush()
    session.add(
        FieldProvenance(
            id=uuid4(),
            entity_type="address",
            entity_id=address.id,
            field_name="address_record",
            raw_value=address_candidate.address_text_raw,
            normalized_value=address.city or address.street or address.address_text_raw,
            source_report_id=report_id,
            source_page=None,
            source_section="Manual staging publish",
            extraction_method="admin",
            parser_version="manual_bridge_v1",
            confidence_score=_confidence_score(address_candidate.confidence_level),
            value_origin_type=address_candidate.value_origin_type,
            review_status=address_candidate.review_status,
            review_note=address_candidate.review_notes or reviewer_note,
            reviewed_by=admin_user_id,
            reviewed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
    )
    return address


async def _write_candidate_provenance(
    session: AsyncSession,
    *,
    candidate: StagingProjectCandidate,
    project: ProjectMaster,
    snapshot: ProjectSnapshot,
    report_id: UUID,
    admin_user_id: UUID,
    reviewer_note: str | None,
    field_candidates: list[StagingFieldCandidate],
) -> None:
    field_lookup = _candidate_field_lookup(field_candidates)
    project_field_map = {
        "canonical_name": ("project_master", project.id, candidate.candidate_project_name),
        "city": ("project_master", project.id, candidate.city),
        "neighborhood": ("project_master", project.id, candidate.neighborhood),
        "lifecycle_stage": ("project_master", project.id, candidate.candidate_lifecycle_stage),
        "disclosure_level": ("project_master", project.id, candidate.candidate_disclosure_level),
        "project_business_type": ("project_master", project.id, candidate.project_business_type),
        "government_program_type": ("project_master", project.id, candidate.government_program_type),
        "project_urban_renewal_type": ("project_master", project.id, candidate.project_urban_renewal_type),
    }
    snapshot_field_map = {
        "source_section_kind": ("snapshot", snapshot.id, candidate.candidate_section_kind),
        "project_status": ("snapshot", snapshot.id, candidate.project_status),
        "permit_status": ("snapshot", snapshot.id, candidate.permit_status),
        "total_units": ("snapshot", snapshot.id, candidate.total_units),
        "marketed_units": ("snapshot", snapshot.id, candidate.marketed_units),
        "sold_units_cumulative": ("snapshot", snapshot.id, candidate.sold_units_cumulative),
        "unsold_units": ("snapshot", snapshot.id, candidate.unsold_units),
        "avg_price_per_sqm_cumulative": ("snapshot", snapshot.id, candidate.avg_price_per_sqm_cumulative),
        "gross_profit_total_expected": ("snapshot", snapshot.id, candidate.gross_profit_total_expected),
        "gross_margin_expected_pct": ("snapshot", snapshot.id, candidate.gross_margin_expected_pct),
    }

    for field_name, (entity_type, entity_id, value) in {**project_field_map, **snapshot_field_map}.items():
        field_candidate = field_lookup.get(field_name)
        session.add(
            FieldProvenance(
                id=uuid4(),
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                raw_value=field_candidate.raw_value if field_candidate else (None if value is None else str(value)),
                normalized_value=field_candidate.normalized_value if field_candidate else (None if value is None else str(value)),
                source_report_id=report_id,
                source_page=field_candidate.source_page if field_candidate else None,
                source_section=field_candidate.source_section if field_candidate else "Manual staging publish",
                extraction_method="admin",
                parser_version="manual_bridge_v1",
                confidence_score=_confidence_score(
                    field_candidate.confidence_level if field_candidate else candidate.confidence_level
                ),
                value_origin_type=field_candidate.value_origin_type if field_candidate else candidate.value_origin_type,
                review_status=field_candidate.review_status if field_candidate else candidate.review_status,
                review_note=field_candidate.review_notes if field_candidate else reviewer_note,
                reviewed_by=admin_user_id,
                reviewed_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
        )


async def _write_extension_provenance(
    session: AsyncSession,
    *,
    extension_rows: dict[str, object],
    extension_payloads: dict[str, dict[str, tuple[object | None, StagingFieldCandidate]]],
    report_id: UUID,
    admin_user_id: UUID,
    reviewer_note: str | None,
) -> None:
    for family_key, row in extension_rows.items():
        entity_type = EXTENSION_ENTITY_TYPE_MAP[family_key]
        for column_name, value in extension_payloads.get(family_key, {}).items():
            normalized_value, field_candidate = value
            session.add(
                FieldProvenance(
                    id=uuid4(),
                    entity_type=entity_type,
                    entity_id=row.id,  # type: ignore[attr-defined]
                    field_name=column_name,
                    raw_value=field_candidate.raw_value,
                    normalized_value=None if normalized_value is None else str(normalized_value),
                    source_report_id=report_id,
                    source_page=field_candidate.source_page,
                    source_section=field_candidate.source_section,
                    extraction_method="admin",
                    parser_version="manual_bridge_v1",
                    confidence_score=_confidence_score(field_candidate.confidence_level),
                    value_origin_type=field_candidate.value_origin_type,
                    review_status=field_candidate.review_status,
                    review_note=field_candidate.review_notes or reviewer_note,
                    reviewed_by=admin_user_id,
                    reviewed_at=datetime.now(UTC),
                    created_at=datetime.now(UTC),
                )
            )


async def publish_candidate(session: AsyncSession, candidate_id: UUID, reviewer_note: str | None) -> dict | None:
    row = (
        await session.execute(
            select(StagingProjectCandidate, StagingReport, Report)
            .join(StagingReport, StagingReport.id == StagingProjectCandidate.staging_report_id)
            .join(Report, Report.id == StagingReport.report_id)
            .where(StagingProjectCandidate.id == candidate_id)
        )
    ).first()
    if row is None:
        return None

    candidate, staging_report, report = row
    if candidate.matching_status in {"ambiguous_match", "ignored", "unmatched"} and candidate.matched_project_id is None:
        raise ValueError("Candidate must be matched or marked as new_project_needed before publish.")

    admin_user = await _get_placeholder_admin(session)
    field_candidates, address_candidates = await _candidate_children(session, candidate.id)
    values = _sanitize_candidate_values(
        {
            "project_business_type": candidate.project_business_type or "regular_dev",
            "government_program_type": candidate.government_program_type,
            "project_urban_renewal_type": candidate.project_urban_renewal_type,
        }
    )

    project = None
    if candidate.matched_project_id:
        project = (
            await session.execute(select(ProjectMaster).where(ProjectMaster.id == candidate.matched_project_id))
        ).scalar_one_or_none()

    if project is None:
        project = ProjectMaster(
            id=uuid4(),
            company_id=candidate.company_id,
            canonical_name=candidate.candidate_project_name,
            city=candidate.city,
            neighborhood=candidate.neighborhood,
            asset_domain="residential_only",
            project_business_type=values["project_business_type"],
            government_program_type=values["government_program_type"],
            project_urban_renewal_type=values["project_urban_renewal_type"],
            project_deal_type="ownership",
            project_usage_profile="residential_only",
            lifecycle_stage=candidate.candidate_lifecycle_stage,
            disclosure_level=candidate.candidate_disclosure_level,
            is_publicly_visible=False,
            location_confidence=candidate.location_confidence,
            classification_confidence=candidate.confidence_level,
            mapping_review_status="approved",
            source_conflict_flag=False,
            notes_internal=reviewer_note,
        )
        session.add(project)
        await session.flush()
        candidate.matched_project_id = project.id
        candidate.matching_status = "new_project_needed"
    else:
        project.canonical_name = candidate.candidate_project_name or project.canonical_name
        project.city = candidate.city
        project.neighborhood = candidate.neighborhood
        project.lifecycle_stage = candidate.candidate_lifecycle_stage or project.lifecycle_stage
        project.disclosure_level = candidate.candidate_disclosure_level or project.disclosure_level
        if candidate.project_business_type:
            project.project_business_type = values["project_business_type"]
        project.government_program_type = values["government_program_type"]
        project.project_urban_renewal_type = values["project_urban_renewal_type"]
        project.location_confidence = candidate.location_confidence
        project.classification_confidence = candidate.confidence_level
        project.mapping_review_status = "approved"

    previous_snapshot = await _previous_snapshot(session, project.id, report.id)
    snapshot = (
        await session.execute(
            select(ProjectSnapshot).where(ProjectSnapshot.project_id == project.id, ProjectSnapshot.report_id == report.id)
        )
    ).scalar_one_or_none()
    if snapshot is None:
        snapshot = ProjectSnapshot(
            id=uuid4(),
            project_id=project.id,
            report_id=report.id,
            snapshot_date=report.period_end_date,
        )
        session.add(snapshot)

    snapshot.project_status = candidate.project_status
    snapshot.permit_status = candidate.permit_status
    snapshot.lifecycle_stage = candidate.candidate_lifecycle_stage or project.lifecycle_stage
    snapshot.disclosure_level = candidate.candidate_disclosure_level or project.disclosure_level
    snapshot.source_section_kind = candidate.candidate_section_kind
    snapshot.total_units = candidate.total_units
    snapshot.marketed_units = candidate.marketed_units
    snapshot.sold_units_cumulative = candidate.sold_units_cumulative
    snapshot.unsold_units = candidate.unsold_units
    snapshot.avg_price_per_sqm_cumulative = candidate.avg_price_per_sqm_cumulative
    snapshot.gross_profit_total_expected = candidate.gross_profit_total_expected
    snapshot.gross_margin_expected_pct = candidate.gross_margin_expected_pct
    snapshot.needs_admin_review = False
    await session.flush()
    extension_payloads = _collect_extension_payloads(field_candidates)
    extension_summaries = await _upsert_project_extension_rows(
        session,
        project=project,
        snapshot=snapshot,
        report_id=report.id,
        field_candidates=field_candidates,
    )
    extension_rows: dict[str, object] = {}
    for family_key, model in EXTENSION_MODEL_MAP.items():
        if family_key not in extension_summaries:
            continue
        row = (
            await session.execute(
                select(model).where(model.project_id == project.id, model.snapshot_id == snapshot.id)  # type: ignore[attr-defined]
            )
        ).scalar_one_or_none()
        if row is not None:
            extension_rows[family_key] = row

    for address_candidate in address_candidates:
        await _upsert_project_address_from_candidate(
            session,
            project_id=project.id,
            address_candidate=address_candidate,
            admin_user_id=admin_user.id,
            report_id=report.id,
            reviewer_note=reviewer_note,
        )

    await _write_candidate_provenance(
        session,
        candidate=candidate,
        project=project,
        snapshot=snapshot,
        report_id=report.id,
        admin_user_id=admin_user.id,
        reviewer_note=reviewer_note,
        field_candidates=field_candidates,
    )
    await _write_extension_provenance(
        session,
        extension_rows=extension_rows,
        extension_payloads=extension_payloads,
        report_id=report.id,
        admin_user_id=admin_user.id,
        reviewer_note=reviewer_note,
    )

    diff_json = {}
    for field_name in DIFF_FIELDS:
        previous_value = getattr(previous_snapshot, field_name, None) if previous_snapshot else None
        current_value = getattr(snapshot, field_name, None)
        diff_json[field_name] = {
            "before": None if previous_value is None else str(previous_value),
            "after": None if current_value is None else str(current_value),
            "changed": (None if previous_value is None else str(previous_value))
            != (None if current_value is None else str(current_value)),
        }

    candidate.publish_status = "published"
    candidate.review_status = "approved"
    candidate.review_notes = reviewer_note or candidate.review_notes
    candidate.diff_summary = diff_json
    report.ingestion_status = "published"

    published_count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(StagingProjectCandidate)
                .where(
                    StagingProjectCandidate.staging_report_id == staging_report.id,
                    StagingProjectCandidate.publish_status == "published",
                )
            )
        ).scalar_one()
    )
    total_candidates = int(
        (
            await session.execute(
                select(func.count()).select_from(StagingProjectCandidate).where(
                    StagingProjectCandidate.staging_report_id == staging_report.id
                )
            )
        ).scalar_one()
    )
    staging_report.publish_status = "published" if published_count == total_candidates else "partially_approved"
    staging_report.review_status = "approved" if published_count == total_candidates else "pending"

    await _sync_report_queue(session, report.id, candidate.id, "done", reviewer_note or "Candidate published")
    await _record_audit(
        session,
        action="staging_candidate_publish",
        entity_type="staging_project_candidate",
        entity_id=candidate.id,
        diff_json={**diff_json, "extension_families": extension_summaries},
        comment=reviewer_note,
        actor_user_id=admin_user.id,
    )
    await session.commit()
    return await get_candidate_detail(session, candidate.id)
