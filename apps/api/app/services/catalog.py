from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from collections import Counter
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Company,
    FieldProvenance,
    ProjectAddress,
    ProjectCompletedInventoryDetail,
    ProjectConstructionMetrics,
    ProjectFinancingDetail,
    ProjectLandReserveDetail,
    ProjectMaster,
    ProjectMaterialDisclosure,
    ProjectPlanningDetail,
    ProjectSensitivityScenario,
    ProjectSnapshot,
    ProjectUrbanRenewalDetail,
    Report,
)
from app.services.spatial import city_centroid_geometry
from app.services.spatial import location_quality as spatial_location_quality


ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(slots=True)
class ProjectListFilters:
    q: str | None = None
    city: str | None = None
    company_id: UUID | None = None
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    project_business_type: str | None = None
    government_program_type: str | None = None
    project_urban_renewal_type: str | None = None
    project_status: str | None = None
    permit_status: str | None = None
    location_confidence: str | None = None
    page: int = 1
    page_size: int = 25


@dataclass(slots=True)
class CompanyListFilters:
    q: str | None = None
    city: str | None = None
    sort_by: str = "project_count"


def _latest_snapshot_subquery() -> Select:
    return (
        select(
            ProjectSnapshot.id.label("snapshot_id"),
            ProjectSnapshot.project_id.label("project_id"),
            ProjectSnapshot.report_id.label("report_id"),
            ProjectSnapshot.snapshot_date.label("snapshot_date"),
            ProjectSnapshot.lifecycle_stage.label("lifecycle_stage"),
            ProjectSnapshot.disclosure_level.label("disclosure_level"),
            ProjectSnapshot.source_section_kind.label("source_section_kind"),
            ProjectSnapshot.project_status.label("project_status"),
            ProjectSnapshot.permit_status.label("permit_status"),
            ProjectSnapshot.total_units.label("total_units"),
            ProjectSnapshot.marketed_units.label("marketed_units"),
            ProjectSnapshot.sold_units_cumulative.label("sold_units_cumulative"),
            ProjectSnapshot.unsold_units.label("unsold_units"),
            ProjectSnapshot.avg_price_per_sqm_cumulative.label("avg_price_per_sqm_cumulative"),
            ProjectSnapshot.gross_profit_total_expected.label("gross_profit_total_expected"),
            ProjectSnapshot.gross_margin_expected_pct.label("gross_margin_expected_pct"),
            ProjectSnapshot.detected_data_families.label("detected_data_families"),
            func.row_number()
            .over(
                partition_by=ProjectSnapshot.project_id,
                order_by=(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc()),
            )
            .label("row_num"),
        )
        .subquery()
    )


def _confidence_level(score: Decimal | None) -> str:
    if score is None:
        return "medium"
    if score >= Decimal("90"):
        return "high"
    if score >= Decimal("70"):
        return "medium"
    return "low"


def _location_quality(location_confidence: str | None) -> str:
    return spatial_location_quality(location_confidence)


def _safe_rate(numerator: int | None, denominator: int | None) -> Decimal | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return ((Decimal(numerator) / Decimal(denominator)) * HUNDRED).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _margin_signal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if value >= Decimal("20"):
        return "strong"
    if value >= Decimal("10"):
        return "moderate"
    return "weak"


def _serialize_extension_row(row: object | None, fields: tuple[str, ...]) -> dict[str, object | None] | None:
    if row is None:
        return None
    payload = {field_name: getattr(row, field_name) for field_name in fields if getattr(row, field_name) is not None}
    return payload or None


async def _snapshot_extension_blocks(session: AsyncSession, project_id: UUID, snapshot_id: UUID) -> dict[str, dict[str, object | None]]:
    construction = (
        await session.execute(
            select(ProjectConstructionMetrics).where(
                ProjectConstructionMetrics.project_id == project_id,
                ProjectConstructionMetrics.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    planning = (
        await session.execute(
            select(ProjectPlanningDetail).where(
                ProjectPlanningDetail.project_id == project_id,
                ProjectPlanningDetail.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    completed_inventory = (
        await session.execute(
            select(ProjectCompletedInventoryDetail).where(
                ProjectCompletedInventoryDetail.project_id == project_id,
                ProjectCompletedInventoryDetail.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    financing = (
        await session.execute(
            select(ProjectFinancingDetail).where(
                ProjectFinancingDetail.project_id == project_id,
                ProjectFinancingDetail.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    material = (
        await session.execute(
            select(ProjectMaterialDisclosure).where(
                ProjectMaterialDisclosure.project_id == project_id,
                ProjectMaterialDisclosure.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    sensitivity = (
        await session.execute(
            select(ProjectSensitivityScenario).where(
                ProjectSensitivityScenario.project_id == project_id,
                ProjectSensitivityScenario.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    urban_renewal = (
        await session.execute(
            select(ProjectUrbanRenewalDetail).where(
                ProjectUrbanRenewalDetail.project_id == project_id,
                ProjectUrbanRenewalDetail.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()
    land_reserve = (
        await session.execute(
            select(ProjectLandReserveDetail).where(
                ProjectLandReserveDetail.project_id == project_id,
                ProjectLandReserveDetail.snapshot_id == snapshot_id,
            )
        )
    ).scalar_one_or_none()

    return {
        key: value
        for key, value in {
            "construction_metrics": _serialize_extension_row(
                construction,
                (
                    "engineering_completion_rate",
                    "financial_completion_rate",
                    "average_unit_sqm",
                    "sold_area_sqm_period",
                    "sold_area_sqm_cumulative",
                    "signed_area_sqm",
                    "unsold_area_sqm",
                    "planned_construction_start_date",
                    "planned_construction_end_date",
                    "planned_marketing_start_date",
                    "planned_marketing_end_date",
                ),
            ),
            "planning_metrics": _serialize_extension_row(
                planning,
                (
                    "planning_status_text",
                    "permit_status_text",
                    "requested_rights_text",
                    "intended_uses",
                    "intended_units",
                    "estimated_start_date",
                    "estimated_completion_date",
                    "planned_marketing_start_date",
                    "planning_dependencies",
                ),
            ),
            "completed_inventory_tail": _serialize_extension_row(
                completed_inventory,
                (
                    "completed_units",
                    "delivered_units",
                    "unsold_completed_units",
                    "inventory_cost_book_value",
                    "available_for_sale_units",
                    "occupancy_status_text",
                ),
            ),
            "financing_details": _serialize_extension_row(
                financing,
                (
                    "financing_institution",
                    "facility_amount",
                    "utilization_amount",
                    "unused_capacity",
                    "financing_terms",
                    "covenants_summary",
                    "non_recourse_flag",
                    "surplus_release_conditions",
                    "pledged_or_secured_notes",
                    "advances_received",
                    "receivables_from_signed_contracts",
                ),
            ),
            "material_project_disclosure": _serialize_extension_row(
                material,
                (
                    "financing_institution",
                    "facility_amount",
                    "utilization_amount",
                    "unused_capacity",
                    "financing_terms",
                    "covenants_summary",
                    "non_recourse_flag",
                    "surplus_release_conditions",
                    "expected_economic_profit",
                    "accounting_to_economic_bridge",
                    "pledged_or_secured_notes",
                    "special_project_notes",
                ),
            ),
            "sensitivity_scenarios": _serialize_extension_row(
                sensitivity,
                (
                    "sales_price_plus_5_effect",
                    "sales_price_plus_10_effect",
                    "sales_price_minus_5_effect",
                    "sales_price_minus_10_effect",
                    "construction_cost_plus_5_effect",
                    "construction_cost_plus_10_effect",
                    "construction_cost_minus_5_effect",
                    "construction_cost_minus_10_effect",
                    "base_gross_profit_not_yet_recognized",
                ),
            ),
            "urban_renewal_pipeline": _serialize_extension_row(
                urban_renewal,
                (
                    "existing_units",
                    "future_units_total",
                    "future_units_marketed_by_company",
                    "future_units_for_existing_tenants",
                    "tenant_signature_rate",
                    "signature_timeline",
                    "average_exchange_ratio_signed",
                    "average_exchange_ratio_unsigned",
                    "tenant_relocation_or_demolition_cost",
                    "execution_dependencies",
                    "planning_status_text",
                    "accounting_treatment_summary",
                ),
            ),
            "land_reserve_details": _serialize_extension_row(
                land_reserve,
                (
                    "land_area_sqm",
                    "historical_cost",
                    "financing_cost",
                    "planning_cost",
                    "carrying_value",
                    "current_planning_status",
                    "requested_planning_status",
                    "intended_units",
                    "intended_uses",
                ),
            ),
        }.items()
        if value
    }


def _trust_map(rows: list[FieldProvenance], fields: list[str]) -> dict[str, dict[str, str]]:
    lookup: dict[str, FieldProvenance] = {}
    for row in rows:
        if row.field_name not in lookup:
            lookup[row.field_name] = row

    return {
        field: {
            "value_origin_type": lookup[field].value_origin_type if field in lookup else "unknown",
            "confidence_level": _confidence_level(lookup[field].confidence_score) if field in lookup else "low",
        }
        for field in fields
    }


def _value_origin_summary(rows: list[FieldProvenance]) -> dict[str, int]:
    counts = Counter(row.value_origin_type for row in rows)
    return {
        "reported": counts.get("reported", 0),
        "manual": counts.get("manual", 0),
        "inferred": counts.get("inferred", 0),
        "unknown": counts.get("unknown", 0),
    }


def _serialize_project_row(row: dict) -> dict:
    return {
        "project_id": row["project_id"],
        "canonical_name": row["canonical_name"],
        "company": {"id": row["company_id"], "name_he": row["company_name_he"]},
        "city": row["city"],
        "neighborhood": row["neighborhood"],
        "lifecycle_stage": row.get("lifecycle_stage"),
        "disclosure_level": row.get("disclosure_level"),
        "project_business_type": row["project_business_type"],
        "government_program_type": row["government_program_type"],
        "project_urban_renewal_type": row["project_urban_renewal_type"],
        "project_status": row["project_status"],
        "permit_status": row["permit_status"],
        "total_units": row["total_units"],
        "marketed_units": row["marketed_units"],
        "sold_units_cumulative": row["sold_units_cumulative"],
        "unsold_units": row["unsold_units"],
        "avg_price_per_sqm_cumulative": row["avg_price_per_sqm_cumulative"],
        "gross_profit_total_expected": row["gross_profit_total_expected"],
        "gross_margin_expected_pct": row["gross_margin_expected_pct"],
        "latest_snapshot_date": row["snapshot_date"],
        "location_confidence": row["location_confidence"],
        "location_quality": _location_quality(row["location_confidence"]),
        "display_geometry_type": row["display_geometry_type"],
        "geometry_is_manual": row.get("display_geometry_source") == "manual_override",
        "address_summary": row["display_address_summary"],
        "sell_through_rate": _safe_rate(row["sold_units_cumulative"], row["marketed_units"]),
    }


def _apply_project_filters(stmt: Select, filters: ProjectListFilters, latest_snapshot) -> Select:
    if filters.q:
        term = f"%{filters.q.strip()}%"
        stmt = stmt.where(
            or_(
                ProjectMaster.canonical_name.ilike(term),
                ProjectMaster.city.ilike(term),
                ProjectMaster.neighborhood.ilike(term),
                ProjectMaster.display_address_summary.ilike(term),
                Company.name_he.ilike(term),
            )
        )
    if filters.city:
        stmt = stmt.where(ProjectMaster.city == filters.city)
    if filters.company_id:
        stmt = stmt.where(ProjectMaster.company_id == filters.company_id)
    if filters.lifecycle_stage:
        stmt = stmt.where(
            func.coalesce(latest_snapshot.c.lifecycle_stage, ProjectMaster.lifecycle_stage) == filters.lifecycle_stage
        )
    if filters.disclosure_level:
        stmt = stmt.where(
            func.coalesce(latest_snapshot.c.disclosure_level, ProjectMaster.disclosure_level) == filters.disclosure_level
        )
    if filters.project_business_type:
        stmt = stmt.where(ProjectMaster.project_business_type == filters.project_business_type)
    if filters.government_program_type:
        stmt = stmt.where(ProjectMaster.government_program_type == filters.government_program_type)
    if filters.project_urban_renewal_type:
        stmt = stmt.where(ProjectMaster.project_urban_renewal_type == filters.project_urban_renewal_type)
    if filters.project_status:
        stmt = stmt.where(latest_snapshot.c.project_status == filters.project_status)
    if filters.permit_status:
        stmt = stmt.where(latest_snapshot.c.permit_status == filters.permit_status)
    if filters.location_confidence:
        stmt = stmt.where(ProjectMaster.location_confidence == filters.location_confidence)
    return stmt


def _serialize_display_geometry_from_row(row: Mapping[str, object]) -> dict[str, object]:
    has_coordinates = row.get("display_center_lat") is not None and row.get("display_center_lng") is not None
    location_confidence = row.get("display_geometry_confidence") or row.get("location_confidence") or "unknown"
    is_manual_override = row.get("display_geometry_source") == "manual_override"
    return {
        "geometry_type": row.get("display_geometry_type") or "unknown",
        "geometry_source": row.get("display_geometry_source") or "unknown",
        "location_confidence": location_confidence,
        "location_quality": _location_quality(location_confidence if isinstance(location_confidence, str) else None),
        "geometry_geojson": row.get("display_geometry_geojson"),
        "center_lat": row.get("display_center_lat"),
        "center_lng": row.get("display_center_lng"),
        "address_summary": row.get("display_address_summary"),
        "note": row.get("display_geometry_note"),
        "city_only": location_confidence == "city_only",
        "has_coordinates": has_coordinates,
        "is_manual_override": is_manual_override,
        "is_source_derived": not is_manual_override and row.get("display_geometry_source") in {"reported", "city_registry"},
    }


def _resolved_display_geometry_from_row(row: Mapping[str, object]) -> dict[str, object]:
    geometry_type = row.get("display_geometry_type")
    if geometry_type != "unknown" and (
        row.get("display_geometry_geojson") is not None
        or (row.get("display_center_lat") is not None and row.get("display_center_lng") is not None)
    ):
        return _serialize_display_geometry_from_row(row)

    centroid = city_centroid_geometry(row.get("city") if isinstance(row.get("city"), str) else None)
    if centroid is not None:
        return {
            "geometry_type": centroid["geometry_type"],
            "geometry_source": centroid["geometry_source"],
            "location_confidence": centroid["location_confidence"],
            "location_quality": _location_quality(centroid["location_confidence"]),
            "geometry_geojson": centroid["geometry_geojson"],
            "center_lat": centroid["center_lat"],
            "center_lng": centroid["center_lng"],
            "address_summary": centroid["address_summary"],
            "note": "Derived at read time from the city centroid registry.",
            "city_only": True,
            "has_coordinates": True,
            "is_manual_override": False,
            "is_source_derived": True,
        }

    return _serialize_display_geometry_from_row(row)


def _latest_report_subquery() -> Select:
    return (
        select(
            Report.company_id.label("company_id"),
            Report.filing_reference.label("filing_reference"),
            Report.period_end_date.label("period_end_date"),
            Report.publish_date.label("publish_date"),
            func.row_number()
            .over(
                partition_by=Report.company_id,
                order_by=(Report.period_end_date.desc(), Report.publish_date.desc().nullslast(), Report.created_at.desc()),
            )
            .label("row_num"),
        )
        .subquery()
    )


async def list_projects(
    session: AsyncSession,
    filters: ProjectListFilters,
) -> tuple[list[dict], int]:
    latest_snapshot = _latest_snapshot_subquery()
    stmt = _apply_project_filters(
        (
        select(
            ProjectMaster.id.label("project_id"),
            ProjectMaster.canonical_name,
            ProjectMaster.city,
            ProjectMaster.neighborhood,
            ProjectMaster.lifecycle_stage,
            ProjectMaster.disclosure_level,
            ProjectMaster.project_business_type,
            ProjectMaster.government_program_type,
            ProjectMaster.project_urban_renewal_type,
            ProjectMaster.location_confidence,
            ProjectMaster.display_geometry_type,
            ProjectMaster.display_geometry_source,
            ProjectMaster.display_address_summary,
            Company.id.label("company_id"),
            Company.name_he.label("company_name_he"),
            latest_snapshot.c.project_status,
            latest_snapshot.c.permit_status,
            latest_snapshot.c.total_units,
            latest_snapshot.c.marketed_units,
            latest_snapshot.c.sold_units_cumulative,
            latest_snapshot.c.unsold_units,
            latest_snapshot.c.avg_price_per_sqm_cumulative,
            latest_snapshot.c.gross_profit_total_expected,
            latest_snapshot.c.gross_margin_expected_pct,
            latest_snapshot.c.snapshot_date,
        )
        .join(Company, Company.id == ProjectMaster.company_id)
        .join(
            latest_snapshot,
            (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
        )
        .where(ProjectMaster.is_publicly_visible.is_(True))
        ),
        filters,
        latest_snapshot,
    )

    total = int((await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
    rows = (
        await session.execute(
            stmt.order_by(Company.name_he.asc(), ProjectMaster.city.asc(), ProjectMaster.canonical_name.asc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
    ).mappings().all()
    return [_serialize_project_row(row) for row in rows], total


async def get_project_detail(session: AsyncSession, project_id: UUID) -> dict | None:
    latest_snapshot = _latest_snapshot_subquery()
    detail = (
        await session.execute(
            select(
                ProjectMaster.id.label("project_id"),
                ProjectMaster.canonical_name,
                ProjectMaster.city,
                ProjectMaster.neighborhood,
                ProjectMaster.district,
                ProjectMaster.lifecycle_stage,
                ProjectMaster.disclosure_level,
                ProjectMaster.project_business_type,
                ProjectMaster.government_program_type,
                ProjectMaster.project_urban_renewal_type,
                ProjectMaster.classification_confidence,
                ProjectMaster.location_confidence,
                ProjectMaster.display_geometry_type,
                ProjectMaster.display_geometry_source,
                ProjectMaster.display_geometry_confidence,
                ProjectMaster.display_geometry_geojson,
                ProjectMaster.display_center_lat,
                ProjectMaster.display_center_lng,
                ProjectMaster.display_address_summary,
                ProjectMaster.display_geometry_note,
                Company.id.label("company_id"),
                Company.name_he.label("company_name_he"),
                latest_snapshot.c.snapshot_id,
                latest_snapshot.c.snapshot_date,
                latest_snapshot.c.lifecycle_stage.label("snapshot_lifecycle_stage"),
                latest_snapshot.c.disclosure_level.label("snapshot_disclosure_level"),
                latest_snapshot.c.source_section_kind.label("snapshot_source_section_kind"),
                latest_snapshot.c.project_status,
                latest_snapshot.c.permit_status,
                latest_snapshot.c.total_units,
                latest_snapshot.c.marketed_units,
                latest_snapshot.c.sold_units_cumulative,
                latest_snapshot.c.unsold_units,
                latest_snapshot.c.avg_price_per_sqm_cumulative,
                latest_snapshot.c.gross_profit_total_expected,
                latest_snapshot.c.gross_margin_expected_pct,
                latest_snapshot.c.detected_data_families,
                Report.id.label("report_id"),
                Report.filing_reference,
                Report.period_end_date,
                Report.publish_date,
                Report.source_url,
                Report.source_file_path,
            )
            .join(Company, Company.id == ProjectMaster.company_id)
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .join(Report, Report.id == latest_snapshot.c.report_id)
            .where(ProjectMaster.id == project_id, ProjectMaster.is_publicly_visible.is_(True))
        )
    ).mappings().first()
    if detail is None:
        return None

    addresses = (
        await session.execute(
            select(ProjectAddress)
            .where(ProjectAddress.project_id == project_id)
            .order_by(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc())
        )
    ).scalars().all()
    address_ids = [address.id for address in addresses]

    provenance = (
        await session.execute(
            select(FieldProvenance)
            .where(
                FieldProvenance.source_report_id == detail["report_id"],
                FieldProvenance.entity_id.in_([detail["project_id"], detail["snapshot_id"], *address_ids]),
            )
            .order_by(FieldProvenance.field_name.asc(), FieldProvenance.created_at.desc())
        )
    ).scalars().all()
    address_provenance_lookup = {
        row.entity_id: row for row in provenance if row.entity_id in address_ids and row.field_name == "address_record"
    }

    pages = sorted({row.source_page for row in provenance if row.source_page is not None})
    missing_fields = sorted({row.field_name for row in provenance if row.value_origin_type == "unknown"})

    display_geometry = _resolved_display_geometry_from_row(detail)
    extension_blocks = await _snapshot_extension_blocks(session, detail["project_id"], detail["snapshot_id"])

    return {
        "identity": {
            "project_id": detail["project_id"],
            "canonical_name": detail["canonical_name"],
            "company": {"id": detail["company_id"], "name_he": detail["company_name_he"]},
        },
        "classification": {
            "lifecycle_stage": detail["lifecycle_stage"],
            "disclosure_level": detail["disclosure_level"],
            "project_business_type": detail["project_business_type"],
            "government_program_type": detail["government_program_type"],
            "project_urban_renewal_type": detail["project_urban_renewal_type"],
            "project_status": detail["project_status"],
            "permit_status": detail["permit_status"],
            "classification_confidence": detail["classification_confidence"],
            "trust": _trust_map(
                provenance,
                [
                    "project_business_type",
                    "government_program_type",
                    "project_urban_renewal_type",
                    "project_status",
                    "permit_status",
                ],
            ),
        },
        "location": {
            "city": detail["city"],
            "neighborhood": detail["neighborhood"],
            "district": detail["district"],
            "location_confidence": detail["location_confidence"],
            "location_quality": _location_quality(detail["location_confidence"]),
            "address_summary": display_geometry["address_summary"],
            "trust": _trust_map(provenance, ["city", "neighborhood", "district", "location_confidence"]),
        },
        "display_geometry": display_geometry,
        "latest_snapshot": {
            "snapshot_id": detail["snapshot_id"],
            "snapshot_date": detail["snapshot_date"],
            "lifecycle_stage": detail["lifecycle_stage"] or detail["snapshot_lifecycle_stage"],
            "disclosure_level": detail["snapshot_disclosure_level"] or detail["disclosure_level"],
            "source_section_kind": detail["snapshot_source_section_kind"],
            "project_status": detail["project_status"],
            "permit_status": detail["permit_status"],
            "total_units": detail["total_units"],
            "marketed_units": detail["marketed_units"],
            "sold_units_cumulative": detail["sold_units_cumulative"],
            "unsold_units": detail["unsold_units"],
            "avg_price_per_sqm_cumulative": detail["avg_price_per_sqm_cumulative"],
            "gross_profit_total_expected": detail["gross_profit_total_expected"],
            "gross_margin_expected_pct": detail["gross_margin_expected_pct"],
            "trust": _trust_map(
                provenance,
                [
                    "total_units",
                    "marketed_units",
                    "sold_units_cumulative",
                    "unsold_units",
                    "avg_price_per_sqm_cumulative",
                    "gross_profit_total_expected",
                    "gross_margin_expected_pct",
                ],
            ),
            "data_families": list(detail["detected_data_families"] or extension_blocks.keys()),
            "extension_blocks": extension_blocks,
        },
        "derived_metrics": {
            "sell_through_rate": _safe_rate(detail["sold_units_cumulative"], detail["marketed_units"]),
            "known_unsold_units": detail["unsold_units"],
            "latest_known_avg_price_per_sqm": detail["avg_price_per_sqm_cumulative"],
            "known_margin_signal": _margin_signal(detail["gross_margin_expected_pct"]),
        },
        "addresses": [
            {
                "id": address.id,
                "address_text_raw": address.address_text_raw,
                "normalized_address_text": address.normalized_address_text,
                "city": address.city,
                "normalized_city": address.normalized_city,
                "street": address.street,
                "normalized_street": address.normalized_street,
                "house_number_from": address.house_number_from,
                "house_number_to": address.house_number_to,
                "lat": address.lat,
                "lng": address.lng,
                "location_confidence": address.location_confidence,
                "location_quality": _location_quality(address.location_confidence),
                "geometry_source": address.geometry_source,
                "normalized_display_address": address.normalized_display_address,
                "is_geocoding_ready": address.is_geocoding_ready,
                "geocoding_status": address.geocoding_status,
                "geocoding_method": address.geocoding_method,
                "geocoding_provider": address.geocoding_provider,
                "geocoding_source_label": address.geocoding_source_label,
                "geocoding_note": address.geocoding_note,
                "is_primary": address.is_primary,
                "value_origin_type": address_provenance_lookup[address.id].value_origin_type
                if address.id in address_provenance_lookup
                else ("reported" if address.source_type == "admin" else "unknown"),
            }
            for address in addresses
        ],
        "source_quality": {
            "source_company": detail["company_name_he"],
            "source_report_name": detail["filing_reference"],
            "report_period_end": detail["period_end_date"],
            "published_at": detail["publish_date"],
            "source_url": detail["source_url"] or detail["source_file_path"],
            "source_pages": ",".join(str(page) for page in pages) if pages else None,
            "confidence_level": detail["classification_confidence"],
            "missing_fields": missing_fields,
            "value_origin_summary": _value_origin_summary(provenance),
        },
        "field_provenance": [
            {
                "field_name": row.field_name,
                "raw_value": row.raw_value,
                "normalized_value": row.normalized_value,
                "source_page": row.source_page,
                "source_section": row.source_section,
                "extraction_method": row.extraction_method,
                "confidence_score": row.confidence_score,
                "value_origin_type": row.value_origin_type,
                "review_status": row.review_status,
                "review_note": row.review_note,
            }
            for row in provenance
        ],
    }


async def get_project_history(session: AsyncSession, project_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            select(ProjectSnapshot, Report.period_end_date)
            .join(Report, Report.id == ProjectSnapshot.report_id)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.snapshot_date.asc(), ProjectSnapshot.created_at.asc())
        )
    ).all()

    snapshots: list[dict] = []
    previous: ProjectSnapshot | None = None
    for snapshot, report_period_end in rows:
        snapshots.append(
            {
                "snapshot_id": snapshot.id,
                "snapshot_date": snapshot.snapshot_date,
                "report_id": snapshot.report_id,
                "report_period_end": report_period_end,
                "project_status": snapshot.project_status,
                "permit_status": snapshot.permit_status,
                "total_units": snapshot.total_units,
                "marketed_units": snapshot.marketed_units,
                "sold_units_cumulative": snapshot.sold_units_cumulative,
                "unsold_units": snapshot.unsold_units,
                "avg_price_per_sqm_cumulative": snapshot.avg_price_per_sqm_cumulative,
                "gross_profit_total_expected": snapshot.gross_profit_total_expected,
                "gross_margin_expected_pct": snapshot.gross_margin_expected_pct,
                "sell_through_rate": _safe_rate(snapshot.sold_units_cumulative, snapshot.marketed_units),
                "sold_units_delta": None
                if previous is None or snapshot.sold_units_cumulative is None or previous.sold_units_cumulative is None
                else snapshot.sold_units_cumulative - previous.sold_units_cumulative,
                "unsold_units_delta": None
                if previous is None or snapshot.unsold_units is None or previous.unsold_units is None
                else snapshot.unsold_units - previous.unsold_units,
            }
        )
        previous = snapshot

    return list(reversed(snapshots))


async def list_companies(session: AsyncSession, filters: CompanyListFilters | None = None) -> list[dict]:
    filters = filters or CompanyListFilters()
    latest_snapshot = _latest_snapshot_subquery()
    latest_report = _latest_report_subquery()
    stmt = (
        select(
            Company.id,
            Company.name_he,
            Company.ticker,
            func.count(ProjectMaster.id).label("project_count"),
            func.count(func.distinct(ProjectMaster.city)).label("city_count"),
            latest_report.c.period_end_date.label("latest_report_period_end"),
            latest_report.c.publish_date.label("latest_published_at"),
            func.coalesce(func.sum(func.coalesce(latest_snapshot.c.unsold_units, 0)), 0).label("known_unsold_units"),
            func.sum(
                case(
                    (ProjectMaster.location_confidence.in_(["exact", "approximate"]), 1),
                    else_=0,
                )
            ).label("projects_with_precise_location_count"),
        )
        .join(ProjectMaster, ProjectMaster.company_id == Company.id)
        .join(
            latest_snapshot,
            (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
        )
        .outerjoin(
            latest_report,
            (latest_report.c.company_id == Company.id) & (latest_report.c.row_num == 1),
        )
        .where(ProjectMaster.is_publicly_visible.is_(True))
        .group_by(
            Company.id,
            Company.name_he,
            Company.ticker,
            latest_report.c.period_end_date,
            latest_report.c.publish_date,
        )
    )

    if filters.q:
        stmt = stmt.where(Company.name_he.ilike(f"%{filters.q.strip()}%"))
    if filters.city:
        stmt = stmt.where(ProjectMaster.city == filters.city)

    order_by = {
        "city_count": (
            func.count(func.distinct(ProjectMaster.city)).desc(),
            Company.name_he.asc(),
        ),
        "latest_report": (
            latest_report.c.period_end_date.desc().nullslast(),
            Company.name_he.asc(),
        ),
        "project_count": (
            func.count(ProjectMaster.id).desc(),
            Company.name_he.asc(),
        ),
    }.get(filters.sort_by, (func.count(ProjectMaster.id).desc(), Company.name_he.asc()))

    rows = (await session.execute(stmt.order_by(*order_by))).mappings().all()
    return [
        {
            "id": row["id"],
            "name_he": row["name_he"],
            "ticker": row["ticker"],
            "project_count": row["project_count"],
            "city_count": row["city_count"],
            "latest_report_period_end": row["latest_report_period_end"],
            "latest_published_at": row["latest_published_at"],
            "known_unsold_units": row["known_unsold_units"],
            "projects_with_precise_location_count": row["projects_with_precise_location_count"] or 0,
        }
        for row in rows
    ]


async def get_company_detail(session: AsyncSession, company_id: UUID) -> dict | None:
    company = (await session.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if company is None:
        return None

    latest_snapshot = _latest_snapshot_subquery()
    projects = (
        await session.execute(
            select(
                ProjectMaster.id,
                ProjectMaster.canonical_name,
                ProjectMaster.city,
                ProjectMaster.project_business_type,
                ProjectMaster.location_confidence,
                latest_snapshot.c.snapshot_date,
                latest_snapshot.c.project_status,
                latest_snapshot.c.permit_status,
                latest_snapshot.c.marketed_units,
                latest_snapshot.c.sold_units_cumulative,
                latest_snapshot.c.unsold_units,
                latest_snapshot.c.avg_price_per_sqm_cumulative,
            )
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .where(ProjectMaster.company_id == company_id, ProjectMaster.is_publicly_visible.is_(True))
            .order_by(ProjectMaster.city.asc(), ProjectMaster.canonical_name.asc())
        )
    ).mappings().all()

    latest_report = (
        await session.execute(
            select(Report)
            .where(Report.company_id == company_id)
            .order_by(Report.period_end_date.desc(), Report.publish_date.desc().nullslast())
            .limit(1)
        )
    ).scalar_one_or_none()

    city_counter = Counter(row["city"] for row in projects if row["city"])
    business_counter = Counter(row["project_business_type"] for row in projects)
    avg_prices = [row["avg_price_per_sqm_cumulative"] for row in projects if row["avg_price_per_sqm_cumulative"] is not None]
    known_unsold_units = sum(row["unsold_units"] or 0 for row in projects)
    precise_locations = sum(1 for row in projects if row["location_confidence"] in {"exact", "approximate"})

    return {
        "id": company.id,
        "name_he": company.name_he,
        "ticker": company.ticker,
        "latest_report_name": latest_report.filing_reference if latest_report else None,
        "latest_report_period_end": latest_report.period_end_date if latest_report else None,
        "latest_published_at": latest_report.publish_date if latest_report else None,
        "project_count": len(projects),
        "city_count": len(city_counter),
        "kpis": {
            "known_unsold_units": known_unsold_units if projects else None,
            "projects_with_precise_location_count": precise_locations,
            "company_city_spread": len(city_counter),
            "latest_known_avg_price_per_sqm": (
                sum(avg_prices) / len(avg_prices) if avg_prices else None
            ),
        },
        "city_coverage": [
            {"city": city, "project_count": project_count}
            for city, project_count in city_counter.most_common()
        ],
        "project_business_type_distribution": [
            {"project_business_type": project_business_type, "project_count": project_count}
            for project_business_type, project_count in business_counter.most_common()
        ],
        "projects": [
            {
                "id": row["id"],
                "canonical_name": row["canonical_name"],
                "city": row["city"],
                "project_business_type": row["project_business_type"],
                "project_status": row["project_status"],
                "permit_status": row["permit_status"],
                "marketed_units": row["marketed_units"],
                "sold_units_cumulative": row["sold_units_cumulative"],
                "unsold_units": row["unsold_units"],
                "latest_snapshot_date": row["snapshot_date"],
                "location_quality": _location_quality(row["location_confidence"]),
            }
            for row in projects
        ],
    }


async def get_company_projects(session: AsyncSession, company_id: UUID) -> list[dict]:
    detail = await get_company_detail(session, company_id)
    return [] if detail is None else detail["projects"]


async def get_filter_metadata(session: AsyncSession) -> dict:
    latest_snapshot = _latest_snapshot_subquery()
    companies = (
        await session.execute(
            select(Company.id, Company.name_he)
            .join(ProjectMaster, ProjectMaster.company_id == Company.id)
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .where(ProjectMaster.is_publicly_visible.is_(True))
            .distinct()
            .order_by(Company.name_he.asc())
        )
    ).mappings().all()
    cities = (
        await session.execute(
            select(ProjectMaster.city)
            .where(ProjectMaster.is_publicly_visible.is_(True), ProjectMaster.city.is_not(None))
            .distinct()
            .order_by(ProjectMaster.city.asc())
        )
    ).scalars().all()
    business_types = (
        await session.execute(
            select(ProjectMaster.project_business_type)
            .where(ProjectMaster.is_publicly_visible.is_(True))
            .distinct()
            .order_by(ProjectMaster.project_business_type.asc())
        )
    ).scalars().all()
    lifecycle_stages = (
        await session.execute(
            select(func.coalesce(latest_snapshot.c.lifecycle_stage, ProjectMaster.lifecycle_stage))
            .select_from(ProjectMaster)
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .where(
                ProjectMaster.is_publicly_visible.is_(True),
                func.coalesce(latest_snapshot.c.lifecycle_stage, ProjectMaster.lifecycle_stage).is_not(None),
            )
            .distinct()
            .order_by(func.coalesce(latest_snapshot.c.lifecycle_stage, ProjectMaster.lifecycle_stage).asc())
        )
    ).scalars().all()
    disclosure_levels = (
        await session.execute(
            select(func.coalesce(latest_snapshot.c.disclosure_level, ProjectMaster.disclosure_level))
            .select_from(ProjectMaster)
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .where(
                ProjectMaster.is_publicly_visible.is_(True),
                func.coalesce(latest_snapshot.c.disclosure_level, ProjectMaster.disclosure_level).is_not(None),
            )
            .distinct()
            .order_by(func.coalesce(latest_snapshot.c.disclosure_level, ProjectMaster.disclosure_level).asc())
        )
    ).scalars().all()
    government_types = (
        await session.execute(
            select(ProjectMaster.government_program_type)
            .where(ProjectMaster.is_publicly_visible.is_(True))
            .distinct()
            .order_by(ProjectMaster.government_program_type.asc())
        )
    ).scalars().all()
    urban_types = (
        await session.execute(
            select(ProjectMaster.project_urban_renewal_type)
            .where(ProjectMaster.is_publicly_visible.is_(True))
            .distinct()
            .order_by(ProjectMaster.project_urban_renewal_type.asc())
        )
    ).scalars().all()
    permit_statuses = (
        await session.execute(
            select(latest_snapshot.c.permit_status)
            .select_from(ProjectMaster)
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .where(ProjectMaster.is_publicly_visible.is_(True), latest_snapshot.c.permit_status.is_not(None))
            .distinct()
            .order_by(latest_snapshot.c.permit_status.asc())
        )
    ).scalars().all()
    project_statuses = (
        await session.execute(
            select(latest_snapshot.c.project_status)
            .select_from(ProjectMaster)
            .join(
                latest_snapshot,
                (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
            )
            .where(ProjectMaster.is_publicly_visible.is_(True), latest_snapshot.c.project_status.is_not(None))
            .distinct()
            .order_by(latest_snapshot.c.project_status.asc())
        )
    ).scalars().all()
    location_confidences = (
        await session.execute(
            select(ProjectMaster.location_confidence)
            .where(ProjectMaster.is_publicly_visible.is_(True), ProjectMaster.location_confidence.is_not(None))
            .distinct()
            .order_by(ProjectMaster.location_confidence.asc())
        )
    ).scalars().all()

    return {
        "companies": [{"id": str(item["id"]), "label": item["name_he"]} for item in companies],
        "cities": cities,
        "lifecycle_stages": lifecycle_stages,
        "disclosure_levels": disclosure_levels,
        "project_business_types": business_types,
        "government_program_types": government_types,
        "project_urban_renewal_types": urban_types,
        "project_statuses": project_statuses,
        "permit_statuses": permit_statuses,
        "location_confidences": location_confidences,
    }


async def get_map_projects(session: AsyncSession, filters: ProjectListFilters) -> dict:
    latest_snapshot = _latest_snapshot_subquery()
    stmt = _apply_project_filters(
        select(
            ProjectMaster.id.label("project_id"),
            ProjectMaster.canonical_name,
            ProjectMaster.city,
            ProjectMaster.neighborhood,
            ProjectMaster.lifecycle_stage,
            ProjectMaster.disclosure_level,
            ProjectMaster.project_business_type,
            ProjectMaster.government_program_type,
            ProjectMaster.project_urban_renewal_type,
            ProjectMaster.location_confidence,
            ProjectMaster.display_geometry_type,
            ProjectMaster.display_geometry_source,
            ProjectMaster.display_geometry_confidence,
            ProjectMaster.display_geometry_geojson,
            ProjectMaster.display_center_lat,
            ProjectMaster.display_center_lng,
            ProjectMaster.display_address_summary,
            ProjectMaster.display_geometry_note,
            Company.id.label("company_id"),
            Company.name_he.label("company_name_he"),
            latest_snapshot.c.snapshot_id,
            latest_snapshot.c.project_status,
            latest_snapshot.c.permit_status,
            latest_snapshot.c.total_units,
            latest_snapshot.c.marketed_units,
            latest_snapshot.c.sold_units_cumulative,
            latest_snapshot.c.unsold_units,
            latest_snapshot.c.avg_price_per_sqm_cumulative,
            latest_snapshot.c.gross_profit_total_expected,
            latest_snapshot.c.gross_margin_expected_pct,
            latest_snapshot.c.snapshot_date,
        )
        .join(Company, Company.id == ProjectMaster.company_id)
        .join(
            latest_snapshot,
            (latest_snapshot.c.project_id == ProjectMaster.id) & (latest_snapshot.c.row_num == 1),
        )
        .where(ProjectMaster.is_publicly_visible.is_(True)),
        filters,
        latest_snapshot,
    ).order_by(Company.name_he.asc(), ProjectMaster.city.asc(), ProjectMaster.canonical_name.asc())
    rows = (await session.execute(stmt)).mappings().all()

    entity_to_project: dict[UUID, UUID] = {}
    for row in rows:
        entity_to_project[row["project_id"]] = row["project_id"]
        if row["snapshot_id"] is not None:
            entity_to_project[row["snapshot_id"]] = row["project_id"]

    provenance_counts_by_project: dict[UUID, Counter[str]] = {row["project_id"]: Counter() for row in rows}
    entity_ids = list(entity_to_project.keys())
    if entity_ids:
        provenance_rows = (
            await session.execute(
                select(
                    FieldProvenance.entity_id,
                    FieldProvenance.value_origin_type,
                    func.count().label("row_count"),
                )
                .where(FieldProvenance.entity_id.in_(entity_ids))
                .group_by(FieldProvenance.entity_id, FieldProvenance.value_origin_type)
            )
        ).all()
        for entity_id, value_origin_type, row_count in provenance_rows:
            project_id = entity_to_project.get(entity_id)
            if project_id is None:
                continue
            provenance_counts_by_project.setdefault(project_id, Counter())[value_origin_type] += int(row_count)

    features = []
    for row in rows:
        item = _serialize_project_row(row)
        display_geometry = _resolved_display_geometry_from_row(row)
        geometry = display_geometry["geometry_geojson"]
        origin_counts = provenance_counts_by_project.get(row["project_id"], Counter())

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "project_id": item["project_id"],
                    "canonical_name": item["canonical_name"],
                    "company_id": row["company_id"],
                    "company_name": item["company"]["name_he"],
                    "city": item["city"],
                    "neighborhood": row["neighborhood"],
                    "lifecycle_stage": item["lifecycle_stage"],
                    "disclosure_level": item["disclosure_level"],
                    "project_business_type": item["project_business_type"],
                    "government_program_type": row["government_program_type"],
                    "project_urban_renewal_type": row["project_urban_renewal_type"],
                    "project_status": item["project_status"],
                    "permit_status": row["permit_status"],
                    "total_units": row["total_units"],
                    "marketed_units": row["marketed_units"],
                    "sold_units_cumulative": row["sold_units_cumulative"],
                    "avg_price_per_sqm_cumulative": item["avg_price_per_sqm_cumulative"],
                    "unsold_units": item["unsold_units"],
                    "gross_profit_total_expected": row["gross_profit_total_expected"],
                    "gross_margin_expected_pct": row["gross_margin_expected_pct"],
                    "latest_snapshot_date": row["snapshot_date"],
                    "geometry_type": display_geometry["geometry_type"],
                    "geometry_source": display_geometry["geometry_source"],
                    "location_confidence": display_geometry["location_confidence"],
                    "location_quality": display_geometry["location_quality"],
                    "address_summary": display_geometry["address_summary"],
                    "center_lat": display_geometry["center_lat"],
                    "center_lng": display_geometry["center_lng"],
                    "city_only": display_geometry["city_only"],
                    "has_coordinates": display_geometry["has_coordinates"],
                    "geometry_is_manual": display_geometry["is_manual_override"],
                    "is_source_derived": display_geometry["is_source_derived"],
                    "reported_count": origin_counts.get("reported", 0),
                    "inferred_count": origin_counts.get("inferred", 0),
                    "manual_count": origin_counts.get("manual", 0),
                },
            }
        )

    quality_counts = Counter(feature["properties"]["location_quality"] for feature in features)
    geometry_type_counts = Counter(feature["properties"]["geometry_type"] for feature in features)
    return {
        "features": features,
        "meta": {
            "available_projects": len(features),
            "projects_with_coordinates": sum(1 for feature in features if feature["properties"]["has_coordinates"]),
            "location_quality_breakdown": dict(quality_counts),
            "geometry_type_breakdown": dict(geometry_type_counts),
            "city_only_projects": sum(1 for feature in features if feature["properties"]["city_only"]),
        },
    }


async def export_projects_csv(session: AsyncSession, filters: ProjectListFilters) -> str:
    items, _ = await list_projects(session, replace(filters, page=1, page_size=1000))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "company",
            "project",
            "city",
            "neighborhood",
            "business_type",
            "government_program_type",
            "urban_renewal_type",
            "permit_status",
            "total_units",
            "marketed_units",
            "sold_units",
            "unsold_units",
            "avg_price_per_sqm",
            "gross_margin_pct",
            "latest_snapshot_date",
            "location_confidence",
            "location_quality",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item["company"]["name_he"],
                item["canonical_name"],
                item["city"],
                item["neighborhood"],
                item["project_business_type"],
                item["government_program_type"],
                item["project_urban_renewal_type"],
                item["permit_status"],
                item["total_units"],
                item["marketed_units"],
                item["sold_units_cumulative"],
                item["unsold_units"],
                item["avg_price_per_sqm_cumulative"],
                item["gross_margin_expected_pct"],
                item["latest_snapshot_date"],
                item["location_confidence"],
                item["location_quality"],
            ]
        )
    return buffer.getvalue()
