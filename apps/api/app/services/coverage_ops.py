from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditLog,
    AdminUser,
    Company,
    CompanyCoverageRegistry,
    ProjectAddress,
    ProjectMaster,
    ProjectSnapshot,
    Report,
    StagingProjectCandidate,
)
from app.services.catalog import _latest_snapshot_subquery, _location_quality
from app.services.identity_ops import normalize_text


PLACEHOLDER_ADMIN_EMAIL = "phase3-admin@local"
KEY_COMPLETENESS_FIELDS = (
    "city",
    "neighborhood",
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
    "latest_snapshot_date",
)
STALE_SNAPSHOT_DAYS = 210


async def _get_placeholder_admin(session: AsyncSession) -> AdminUser:
    admin = (
        await session.execute(select(AdminUser).where(AdminUser.email == PLACEHOLDER_ADMIN_EMAIL))
    ).scalar_one_or_none()
    if admin is None:
        admin = AdminUser(
            id=uuid4(),
            email=PLACEHOLDER_ADMIN_EMAIL,
            full_name="Phase 3 Admin Reviewer",
            role="super_admin",
            is_active=True,
        )
        session.add(admin)
        await session.flush()
    return admin


async def _record_audit(
    session: AsyncSession,
    *,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    diff_json: dict | None,
    comment: str | None,
) -> None:
    session.add(
        AdminAuditLog(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            diff_json=diff_json,
            comment=comment,
            created_at=datetime.now(UTC),
        )
    )


def _missing_key_fields_from_row(row: dict) -> list[str]:
    missing: list[str] = []
    for field_name in KEY_COMPLETENESS_FIELDS:
        value = row.get(field_name)
        if field_name in {
            "government_program_type",
            "project_urban_renewal_type",
            "project_business_type",
        }:
            if value in {None, "", "unknown"}:
                missing.append(field_name)
            continue
        if value is None or value == "":
            missing.append(field_name)
    return missing


def _snapshot_age_days(snapshot_date: date | None) -> int | None:
    if snapshot_date is None:
        return None
    return (date.today() - snapshot_date).days


def _safe_text(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


async def _ensure_company_coverage_registry(
    session: AsyncSession,
    *,
    persist: bool = False,
) -> dict[UUID, CompanyCoverageRegistry]:
    companies = (await session.execute(select(Company))).scalars().all()
    existing = {
        row.company_id: row
        for row in (
            await session.execute(select(CompanyCoverageRegistry))
        ).scalars().all()
    }
    missing_company_ids = [company.id for company in companies if company.id not in existing]
    if missing_company_ids:
        await session.execute(
            pg_insert(CompanyCoverageRegistry)
            .values([{"company_id": company_id} for company_id in missing_company_ids])
            .on_conflict_do_nothing(index_elements=["company_id"])
        )
        await session.flush()
        existing = {
            row.company_id: row
            for row in (
                await session.execute(select(CompanyCoverageRegistry))
            ).scalars().all()
        }

    report_rows = (
        await session.execute(
            select(
                Report.id,
                Report.company_id,
                Report.period_end_date,
                Report.publish_date,
                Report.ingestion_status,
                Report.is_in_scope,
            )
            .order_by(Report.company_id.asc(), Report.period_end_date.desc(), Report.publish_date.desc().nullslast())
        )
    ).all()
    reports_by_company: dict[UUID, list[tuple]] = {}
    for row in report_rows:
        reports_by_company.setdefault(row.company_id, []).append(row)

    changed = False
    for company in companies:
        coverage = existing.get(company.id)
        if coverage is None:
            continue

        company_reports = reports_by_company.get(company.id, [])
        scoped_reports = [row for row in company_reports if row.is_in_scope]
        latest_registered = company_reports[0] if company_reports else None
        latest_ingested = next(
            (row for row in company_reports if row.ingestion_status in {"ready_for_staging", "in_review", "published"}),
            None,
        )
        historical_scope = scoped_reports or company_reports

        updates = {
            "latest_report_registered_id": latest_registered.id if latest_registered else None,
            "latest_report_published_date": latest_registered.publish_date if latest_registered else None,
            "latest_report_ingested_id": latest_ingested.id if latest_ingested else None,
            "historical_coverage_start": min((row.period_end_date for row in historical_scope), default=None),
            "historical_coverage_end": max((row.period_end_date for row in historical_scope), default=None),
        }
        for field_name, value in updates.items():
            if getattr(coverage, field_name) != value:
                setattr(coverage, field_name, value)
                changed = True

    if changed:
        if persist:
            await session.commit()
        else:
            await session.flush()
    return existing


async def _project_gap_rows(session: AsyncSession) -> list[dict]:
    latest_snapshot = _latest_snapshot_subquery()
    source_counts = (
        select(
            ProjectSnapshot.project_id.label("project_id"),
            func.count(func.distinct(ProjectSnapshot.report_id)).label("source_count"),
        )
        .group_by(ProjectSnapshot.project_id)
        .subquery()
    )
    address_counts = (
        select(
            ProjectAddress.project_id.label("project_id"),
            func.count().label("address_count"),
        )
        .group_by(ProjectAddress.project_id)
        .subquery()
    )
    primary_addresses = (
        select(
            ProjectAddress.project_id.label("project_id"),
            ProjectAddress.id.label("address_id"),
            ProjectAddress.address_text_raw,
            ProjectAddress.normalized_display_address,
            ProjectAddress.normalized_address_text,
            ProjectAddress.city.label("address_city"),
            ProjectAddress.location_confidence.label("address_location_confidence"),
            ProjectAddress.geocoding_status,
            ProjectAddress.geocoding_method,
            ProjectAddress.geocoding_source_label,
            ProjectAddress.is_geocoding_ready,
            func.row_number()
            .over(
                partition_by=ProjectAddress.project_id,
                order_by=(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc()),
            )
            .label("row_num"),
        )
        .subquery()
    )

    rows = (
        await session.execute(
            select(
                ProjectMaster.id.label("project_id"),
                ProjectMaster.company_id,
                ProjectMaster.canonical_name,
                ProjectMaster.city,
                ProjectMaster.neighborhood,
                ProjectMaster.project_business_type,
                ProjectMaster.government_program_type,
                ProjectMaster.project_urban_renewal_type,
                ProjectMaster.location_confidence,
                ProjectMaster.display_geometry_type,
                ProjectMaster.display_geometry_source,
                ProjectMaster.display_address_summary,
                ProjectMaster.is_publicly_visible,
                Company.name_he.label("company_name_he"),
                latest_snapshot.c.snapshot_id,
                latest_snapshot.c.snapshot_date.label("latest_snapshot_date"),
                latest_snapshot.c.project_status,
                latest_snapshot.c.permit_status,
                latest_snapshot.c.total_units,
                latest_snapshot.c.marketed_units,
                latest_snapshot.c.sold_units_cumulative,
                latest_snapshot.c.unsold_units,
                latest_snapshot.c.avg_price_per_sqm_cumulative,
                latest_snapshot.c.gross_profit_total_expected,
                latest_snapshot.c.gross_margin_expected_pct,
                func.coalesce(source_counts.c.source_count, 0).label("source_count"),
                func.coalesce(address_counts.c.address_count, 0).label("address_count"),
                primary_addresses.c.address_id,
                primary_addresses.c.address_text_raw,
                primary_addresses.c.normalized_display_address,
                primary_addresses.c.normalized_address_text,
                primary_addresses.c.address_city,
                primary_addresses.c.address_location_confidence,
                primary_addresses.c.geocoding_status,
                primary_addresses.c.geocoding_method,
                primary_addresses.c.geocoding_source_label,
                primary_addresses.c.is_geocoding_ready,
            )
            .join(Company, Company.id == ProjectMaster.company_id)
            .outerjoin(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .outerjoin(source_counts, source_counts.c.project_id == ProjectMaster.id)
            .outerjoin(address_counts, address_counts.c.project_id == ProjectMaster.id)
            .outerjoin(
                primary_addresses,
                (primary_addresses.c.project_id == ProjectMaster.id) & (primary_addresses.c.row_num == 1),
            )
            .where(ProjectMaster.deleted_at.is_(None))
            .order_by(Company.name_he.asc(), ProjectMaster.canonical_name.asc())
        )
    ).mappings().all()

    items: list[dict] = []
    for row in rows:
        item = dict(row)
        item["missing_fields"] = _missing_key_fields_from_row(item)
        item["latest_snapshot_age_days"] = _snapshot_age_days(item.get("latest_snapshot_date"))
        item["geometry_is_manual"] = item.get("display_geometry_source") == "manual_override"
        item["address_summary"] = (
            item.get("normalized_display_address")
            or item.get("normalized_address_text")
            or item.get("address_text_raw")
            or item.get("display_address_summary")
            or item.get("city")
        )
        items.append(item)
    return items


async def _report_project_counts(session: AsyncSession) -> tuple[dict[UUID, int], dict[UUID, int]]:
    project_rows = (
        await session.execute(
            select(
                ProjectSnapshot.report_id,
                func.count(func.distinct(ProjectSnapshot.project_id)).label("project_count"),
            )
            .group_by(ProjectSnapshot.report_id)
        )
    ).all()
    snapshot_rows = (
        await session.execute(
            select(ProjectSnapshot.report_id, func.count().label("snapshot_count")).group_by(ProjectSnapshot.report_id)
        )
    ).all()
    return (
        {row.report_id: int(row.project_count) for row in project_rows},
        {row.report_id: int(row.snapshot_count) for row in snapshot_rows},
    )


async def get_coverage_dashboard(session: AsyncSession) -> dict:
    coverage_rows = await _ensure_company_coverage_registry(session, persist=True)
    gap_rows = await _project_gap_rows(session)
    report_name_lookup = {
        row.id: row
        for row in (
            await session.execute(select(Report))
        ).scalars().all()
    }
    _, report_snapshot_counts = await _report_project_counts(session)
    snapshot_totals_by_company = {
        row.company_id: int(row.snapshot_count)
        for row in (
            await session.execute(
                select(
                    ProjectMaster.company_id,
                    func.count(ProjectSnapshot.id).label("snapshot_count"),
                )
                .join(ProjectSnapshot, ProjectSnapshot.project_id == ProjectMaster.id)
                .where(ProjectMaster.deleted_at.is_(None))
                .group_by(ProjectMaster.company_id)
            )
        ).all()
    }
    project_report_ids_by_company: dict[UUID, set[UUID]] = {}
    for report_id, count in report_snapshot_counts.items():
        if count <= 0:
            continue
        report = report_name_lookup.get(report_id)
        if report is None:
            continue
        project_report_ids_by_company.setdefault(report.company_id, set()).add(report_id)

    company_list = (await session.execute(select(Company).order_by(Company.name_he.asc()))).scalars().all()
    unmatched_candidates = int(
        (
            await session.execute(
                select(func.count())
                .select_from(StagingProjectCandidate)
                .where(StagingProjectCandidate.matching_status == "unmatched")
            )
        ).scalar_one()
    )
    ambiguous_candidates = int(
        (
            await session.execute(
                select(func.count())
                .select_from(StagingProjectCandidate)
                .where(StagingProjectCandidate.matching_status == "ambiguous_match")
            )
        ).scalar_one()
    )
    reports_registered = int((await session.execute(select(func.count()).select_from(Report))).scalar_one())
    reports_published_into_canonical = int(
        (
            await session.execute(
                select(func.count(func.distinct(ProjectSnapshot.report_id))).select_from(ProjectSnapshot)
            )
        ).scalar_one()
    )
    total_snapshots = int((await session.execute(select(func.count()).select_from(ProjectSnapshot))).scalar_one())

    field_completeness: list[dict] = []
    for field_name in KEY_COMPLETENESS_FIELDS:
        complete_count = sum(1 for row in gap_rows if field_name not in row["missing_fields"])
        field_completeness.append(
            {
                "field_name": field_name,
                "complete_count": complete_count,
                "missing_count": len(gap_rows) - complete_count,
            }
        )

    company_items: list[dict] = []
    for company in company_list:
        coverage = coverage_rows[company.id]
        company_reports = [report for report in report_name_lookup.values() if report.company_id == company.id]
        company_projects = [row for row in gap_rows if row["company_id"] == company.id]
        latest_registered = report_name_lookup.get(coverage.latest_report_registered_id) if coverage.latest_report_registered_id else None
        latest_ingested = report_name_lookup.get(coverage.latest_report_ingested_id) if coverage.latest_report_ingested_id else None
        company_items.append(
            {
                "company_id": company.id,
                "company_name_he": company.name_he,
                "is_active": coverage.is_active,
                "is_in_scope": coverage.is_in_scope,
                "out_of_scope_reason": coverage.out_of_scope_reason,
                "coverage_priority": coverage.coverage_priority,
                "latest_report_registered_id": coverage.latest_report_registered_id,
                "latest_report_registered_name": latest_registered.filing_reference if latest_registered else None,
                "latest_report_published": coverage.latest_report_published_date,
                "latest_report_ingested_id": coverage.latest_report_ingested_id,
                "latest_report_ingested_name": latest_ingested.filing_reference if latest_ingested else None,
                "historical_coverage_start": coverage.historical_coverage_start,
                "historical_coverage_end": coverage.historical_coverage_end,
                "historical_coverage_status": coverage.historical_coverage_status,
                "backfill_status": coverage.backfill_status,
                "reports_registered": len(company_reports),
                "reports_published_into_canonical": len(project_report_ids_by_company.get(company.id, set())),
                "projects_created": len(company_projects),
                "snapshots_created": snapshot_totals_by_company.get(company.id, 0),
                "projects_missing_key_fields": sum(1 for row in company_projects if row["missing_fields"]),
                "projects_city_only_location": sum(
                    1 for row in company_projects if row.get("location_confidence") in {"city_only", "unknown"}
                ),
                "projects_with_exact_or_approximate_geometry": sum(
                    1 for row in company_projects if row.get("location_confidence") in {"exact", "approximate"}
                ),
                "notes": coverage.notes,
            }
        )

    companies_with_latest_report_ingested = sum(
        1
        for company in company_items
        if company["latest_report_registered_id"] is not None
        and company["latest_report_registered_id"] == company["latest_report_ingested_id"]
    )
    summary = {
        "companies_in_scope": sum(1 for company in company_items if company["is_in_scope"]),
        "companies_with_latest_report_ingested": companies_with_latest_report_ingested,
        "companies_missing_latest_report": sum(
            1
            for company in company_items
            if company["is_in_scope"]
            and company["latest_report_registered_id"] is not None
            and company["latest_report_registered_id"] != company["latest_report_ingested_id"]
        ),
        "reports_registered": reports_registered,
        "reports_published_into_canonical": reports_published_into_canonical,
        "projects_created": len(gap_rows),
        "snapshots_created": total_snapshots,
        "unmatched_candidates": unmatched_candidates,
        "ambiguous_candidates": ambiguous_candidates,
        "projects_missing_key_fields": sum(1 for row in gap_rows if row["missing_fields"]),
        "projects_city_only_location": sum(
            1 for row in gap_rows if row.get("location_confidence") in {"city_only", "unknown"}
        ),
        "projects_with_exact_or_approximate_geometry": sum(
            1 for row in gap_rows if row.get("location_confidence") in {"exact", "approximate"}
        ),
    }
    return {
        "summary": summary,
        "field_completeness": field_completeness,
        "companies": company_items,
    }


async def update_company_coverage(session: AsyncSession, company_id: UUID, payload: dict) -> dict | None:
    coverage_rows = await _ensure_company_coverage_registry(session)
    coverage = coverage_rows.get(company_id)
    if coverage is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    diffs: dict[str, dict[str, object | None]] = {}
    for field_name in [
        "is_active",
        "is_in_scope",
        "out_of_scope_reason",
        "coverage_priority",
        "latest_report_registered_id",
        "latest_report_ingested_id",
        "latest_report_published_date",
        "historical_coverage_start",
        "historical_coverage_end",
        "historical_coverage_status",
        "backfill_status",
        "notes",
    ]:
        if field_name in payload and getattr(coverage, field_name) != payload[field_name]:
            diffs[field_name] = {"before": getattr(coverage, field_name), "after": payload[field_name]}
            setattr(coverage, field_name, payload[field_name])

    if diffs:
        await _record_audit(
            session,
            actor_user_id=admin_user.id,
            action="admin_company_coverage_update",
            entity_type="company_coverage_registry",
            entity_id=company_id,
            diff_json=diffs,
            comment=payload.get("change_reason"),
        )
        await session.commit()
    else:
        await session.rollback()
    return await get_coverage_dashboard(session)


async def list_coverage_reports(session: AsyncSession, filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    await _ensure_company_coverage_registry(session, persist=True)
    coverage_rows = {
        row.company_id: row
        for row in (
            await session.execute(select(CompanyCoverageRegistry))
        ).scalars().all()
    }
    project_counts, snapshot_counts = await _report_project_counts(session)
    companies = {
        row.id: row
        for row in (
            await session.execute(select(Company))
        ).scalars().all()
    }
    reports = (
        await session.execute(
            select(Report).order_by(Report.period_end_date.desc(), Report.publish_date.desc().nullslast(), Report.created_at.desc())
        )
    ).scalars().all()

    items: list[dict] = []
    for report in reports:
        coverage = coverage_rows.get(report.company_id)
        company = companies.get(report.company_id)
        item = {
            "report_id": report.id,
            "company_id": report.company_id,
            "company_name_he": company.name_he if company else "Unknown company",
            "report_name": report.filing_reference,
            "report_type": report.report_type,
            "period_type": report.period_type,
            "period_end_date": report.period_end_date,
            "published_at": report.publish_date,
            "is_in_scope": report.is_in_scope,
            "source_is_official": report.source_is_official,
            "source_label": report.source_label,
            "source_url": report.source_url or report.source_file_path,
            "ingestion_status": report.ingestion_status,
            "linked_project_count": project_counts.get(report.id, 0),
            "linked_snapshot_count": snapshot_counts.get(report.id, 0),
            "is_published_into_canonical": report.id in snapshot_counts,
            "is_latest_registered": bool(coverage and coverage.latest_report_registered_id == report.id),
            "is_latest_ingested": bool(coverage and coverage.latest_report_ingested_id == report.id),
        }
        if filters.get("company_id") and str(report.company_id) != filters["company_id"]:
            continue
        if filters.get("ingestion_status") and report.ingestion_status != filters["ingestion_status"]:
            continue
        if filters.get("scope") == "in_scope" and not report.is_in_scope:
            continue
        if filters.get("scope") == "out_of_scope" and report.is_in_scope:
            continue
        if filters.get("published") == "yes" and not item["is_published_into_canonical"]:
            continue
        if filters.get("published") == "no" and item["is_published_into_canonical"]:
            continue
        items.append(item)
    return items


async def list_coverage_gaps(session: AsyncSession, filters: dict | None = None) -> dict:
    filters = filters or {}
    coverage_rows = await _ensure_company_coverage_registry(session, persist=True)
    rows = await _project_gap_rows(session)
    items: list[dict] = []
    for row in rows:
        coverage = coverage_rows.get(row["company_id"])
        if filters.get("company_id") and str(row["company_id"]) != filters["company_id"]:
            continue
        if filters.get("city") and normalize_text(_safe_text(row["city"])) != normalize_text(filters["city"]):
            continue
        if filters.get("location_confidence") and row.get("location_confidence") != filters["location_confidence"]:
            continue
        if filters.get("backfill_status") and (coverage is None or coverage.backfill_status != filters["backfill_status"]):
            continue
        if filters.get("missing_group") == "location" and row.get("location_confidence") not in {"city_only", "unknown"}:
            continue
        if filters.get("missing_group") == "metrics" and not any(
            field in row["missing_fields"]
            for field in (
                "total_units",
                "marketed_units",
                "sold_units_cumulative",
                "unsold_units",
                "avg_price_per_sqm_cumulative",
                "gross_profit_total_expected",
                "gross_margin_expected_pct",
            )
        ):
            continue
        if filters.get("missing_group") == "stale" and not (
            row.get("latest_snapshot_age_days") is None or row.get("latest_snapshot_age_days", 0) > STALE_SNAPSHOT_DAYS
        ):
            continue
        items.append(
            {
                "project_id": row["project_id"],
                "project_name": row["canonical_name"],
                "company_id": row["company_id"],
                "company_name_he": row["company_name_he"],
                "city": row["city"],
                "location_confidence": row["location_confidence"],
                "location_quality": _location_quality(row["location_confidence"]),
                "latest_snapshot_date": row["latest_snapshot_date"],
                "latest_snapshot_age_days": row["latest_snapshot_age_days"],
                "missing_fields": row["missing_fields"],
                "source_count": row["source_count"],
                "address_count": row["address_count"],
                "is_publicly_visible": row["is_publicly_visible"],
                "backfill_status": coverage.backfill_status if coverage else "not_started",
            }
        )

    return {
        "summary": {
            "total_items": len(items),
            "missing_location": sum(1 for item in items if item["location_confidence"] in {"city_only", "unknown"}),
            "missing_metrics": sum(
                1
                for item in items
                if any(
                    field in item["missing_fields"]
                    for field in (
                        "total_units",
                        "marketed_units",
                        "sold_units_cumulative",
                        "unsold_units",
                        "avg_price_per_sqm_cumulative",
                        "gross_profit_total_expected",
                        "gross_margin_expected_pct",
                    )
                )
            ),
            "stale_or_missing_snapshot": sum(
                1
                for item in items
                if item["latest_snapshot_age_days"] is None or item["latest_snapshot_age_days"] > STALE_SNAPSHOT_DAYS
            ),
        },
        "items": items,
    }


async def list_location_review_projects(session: AsyncSession, filters: dict | None = None) -> dict:
    filters = filters or {}
    coverage_rows = await _ensure_company_coverage_registry(session, persist=True)
    rows = await _project_gap_rows(session)
    items: list[dict] = []
    for row in rows:
        coverage = coverage_rows.get(row["company_id"])
        if row.get("location_confidence") not in {"city_only", "unknown"} and not filters.get("include_all"):
            continue
        if filters.get("company_id") and str(row["company_id"]) != filters["company_id"]:
            continue
        if filters.get("city") and normalize_text(_safe_text(row["city"])) != normalize_text(filters["city"]):
            continue
        if filters.get("location_confidence") and row.get("location_confidence") != filters["location_confidence"]:
            continue
        if filters.get("backfill_status") and (coverage is None or coverage.backfill_status != filters["backfill_status"]):
            continue
        if filters.get("missing_fields") == "yes" and not row["missing_fields"]:
            continue
        items.append(
            {
                "project_id": row["project_id"],
                "project_name": row["canonical_name"],
                "company": {"id": row["company_id"], "name_he": row["company_name_he"]},
                "city": row["city"],
                "neighborhood": row["neighborhood"],
                "location_confidence": row["location_confidence"],
                "location_quality": _location_quality(row["location_confidence"]),
                "geometry_type": row["display_geometry_type"],
                "geometry_source": row["display_geometry_source"],
                "geometry_is_manual": row["geometry_is_manual"],
                "address_count": row["address_count"],
                "primary_address_id": row["address_id"],
                "primary_address_summary": row["address_summary"],
                "geocoding_status": row["geocoding_status"],
                "geocoding_method": row["geocoding_method"],
                "geocoding_source_label": row["geocoding_source_label"],
                "is_geocoding_ready": row["is_geocoding_ready"],
                "latest_snapshot_date": row["latest_snapshot_date"],
                "latest_snapshot_age_days": row["latest_snapshot_age_days"],
                "backfill_status": coverage.backfill_status if coverage else "not_started",
                "missing_location_fields": [
                    field for field in row["missing_fields"] if field in {"city", "neighborhood", "latest_snapshot_date"}
                ],
            }
        )

    return {
        "summary": {
            "total_items": len(items),
            "city_only": sum(1 for item in items if item["location_confidence"] == "city_only"),
            "unknown": sum(1 for item in items if item["location_confidence"] == "unknown"),
            "manual_geometry": sum(1 for item in items if item["geometry_is_manual"]),
            "geocoding_ready": sum(1 for item in items if item["is_geocoding_ready"]),
        },
        "items": items,
    }


async def apply_coverage_bulk_action(session: AsyncSession, payload: dict) -> dict:
    ids = payload.get("ids", [])
    target_type = payload.get("target_type")
    action = payload.get("action")
    admin_user = await _get_placeholder_admin(session)
    applied_count = 0

    if target_type == "company":
        coverage_rows = await _ensure_company_coverage_registry(session)
        for raw_id in ids:
            try:
                company_id = UUID(str(raw_id))
            except ValueError:
                continue
            coverage = coverage_rows.get(company_id)
            if coverage is None:
                continue
            if action == "set_scope":
                coverage.is_in_scope = bool(payload.get("is_in_scope", True))
            elif action == "set_backfill_status" and payload.get("backfill_status"):
                coverage.backfill_status = payload["backfill_status"]
            else:
                continue
            applied_count += 1
            await _record_audit(
                session,
                actor_user_id=admin_user.id,
                action="admin_coverage_bulk_company_update",
                entity_type="company_coverage_registry",
                entity_id=company_id,
                diff_json={"action": action, "payload": payload},
                comment=payload.get("note"),
            )
    elif target_type == "report":
        for raw_id in ids:
            try:
                report_id = UUID(str(raw_id))
            except ValueError:
                continue
            report = (await session.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
            if report is None or action != "set_scope":
                continue
            report.is_in_scope = bool(payload.get("is_in_scope", True))
            applied_count += 1
            await _record_audit(
                session,
                actor_user_id=admin_user.id,
                action="admin_coverage_bulk_report_update",
                entity_type="report",
                entity_id=report_id,
                diff_json={"action": action, "payload": payload},
                comment=payload.get("note"),
            )

    if applied_count:
        await session.commit()
    else:
        await session.rollback()
    return {
        "applied_count": applied_count,
        "target_type": target_type,
        "action": action,
    }


async def export_coverage_rows(session: AsyncSession, export_kind: str, filters: dict | None = None) -> tuple[str, str]:
    filters = filters or {}
    if export_kind == "reports":
        rows = await list_coverage_reports(session, filters)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "company_name_he",
                "report_name",
                "period_end_date",
                "published_at",
                "is_in_scope",
                "ingestion_status",
                "linked_project_count",
                "linked_snapshot_count",
                "is_published_into_canonical",
                "source_label",
                "source_url",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue(), "coverage-reports.csv"

    if export_kind == "location_missing":
        rows = (await list_location_review_projects(session, filters))["items"]
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "project_name",
                "company_name_he",
                "city",
                "location_confidence",
                "geometry_type",
                "geometry_source",
                "geometry_is_manual",
                "primary_address_summary",
                "geocoding_status",
                "geocoding_method",
                "geocoding_source_label",
                "is_geocoding_ready",
                "latest_snapshot_date",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "project_name": row["project_name"],
                    "company_name_he": row["company"]["name_he"],
                    "city": row["city"],
                    "location_confidence": row["location_confidence"],
                    "geometry_type": row["geometry_type"],
                    "geometry_source": row["geometry_source"],
                    "geometry_is_manual": row["geometry_is_manual"],
                    "primary_address_summary": row["primary_address_summary"],
                    "geocoding_status": row["geocoding_status"],
                    "geocoding_method": row["geocoding_method"],
                    "geocoding_source_label": row["geocoding_source_label"],
                    "is_geocoding_ready": row["is_geocoding_ready"],
                    "latest_snapshot_date": row["latest_snapshot_date"],
                }
            )
        return output.getvalue(), "projects-missing-location.csv"

    gap_filters = dict(filters)
    if export_kind == "metrics_missing":
        gap_filters["missing_group"] = "metrics"
    elif export_kind == "gaps" and "missing_group" not in gap_filters:
        gap_filters["missing_group"] = None
    gap_rows = (await list_coverage_gaps(session, gap_filters))["items"]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "project_name",
            "company_name_he",
            "city",
            "location_confidence",
            "latest_snapshot_date",
            "latest_snapshot_age_days",
            "missing_fields",
            "source_count",
            "address_count",
            "is_publicly_visible",
        ],
    )
    writer.writeheader()
    for row in gap_rows:
        writer.writerow({**row, "missing_fields": ", ".join(row["missing_fields"])})
    filename = "coverage-gaps.csv" if export_kind == "gaps" else "projects-missing-key-metrics.csv"
    return output.getvalue(), filename
