from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, FieldProvenance, ProjectAddress, ProjectMaster, ProjectSnapshot, Report


ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(slots=True)
class ProjectListFilters:
    q: str | None = None
    city: str | None = None
    company_id: UUID | None = None
    project_business_type: str | None = None
    government_program_type: str | None = None
    project_urban_renewal_type: str | None = None
    permit_status: str | None = None
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
            ProjectSnapshot.project_status.label("project_status"),
            ProjectSnapshot.permit_status.label("permit_status"),
            ProjectSnapshot.total_units.label("total_units"),
            ProjectSnapshot.marketed_units.label("marketed_units"),
            ProjectSnapshot.sold_units_cumulative.label("sold_units_cumulative"),
            ProjectSnapshot.unsold_units.label("unsold_units"),
            ProjectSnapshot.avg_price_per_sqm_cumulative.label("avg_price_per_sqm_cumulative"),
            ProjectSnapshot.gross_profit_total_expected.label("gross_profit_total_expected"),
            ProjectSnapshot.gross_margin_expected_pct.label("gross_margin_expected_pct"),
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
    if location_confidence == "exact":
        return "exact"
    if location_confidence in {"street", "neighborhood"}:
        return "approximate"
    if location_confidence == "city":
        return "city-only"
    return "unknown"


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
        "sell_through_rate": _safe_rate(row["sold_units_cumulative"], row["marketed_units"]),
    }


async def list_projects(
    session: AsyncSession,
    filters: ProjectListFilters,
) -> tuple[list[dict], int]:
    latest_snapshot = _latest_snapshot_subquery()
    stmt = (
        select(
            ProjectMaster.id.label("project_id"),
            ProjectMaster.canonical_name,
            ProjectMaster.city,
            ProjectMaster.neighborhood,
            ProjectMaster.project_business_type,
            ProjectMaster.government_program_type,
            ProjectMaster.project_urban_renewal_type,
            ProjectMaster.location_confidence,
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
    )

    if filters.q:
        term = f"%{filters.q.strip()}%"
        stmt = stmt.where(
            or_(
                ProjectMaster.canonical_name.ilike(term),
                ProjectMaster.city.ilike(term),
                Company.name_he.ilike(term),
            )
        )
    if filters.city:
        stmt = stmt.where(ProjectMaster.city == filters.city)
    if filters.company_id:
        stmt = stmt.where(ProjectMaster.company_id == filters.company_id)
    if filters.project_business_type:
        stmt = stmt.where(ProjectMaster.project_business_type == filters.project_business_type)
    if filters.government_program_type:
        stmt = stmt.where(ProjectMaster.government_program_type == filters.government_program_type)
    if filters.project_urban_renewal_type:
        stmt = stmt.where(ProjectMaster.project_urban_renewal_type == filters.project_urban_renewal_type)
    if filters.permit_status:
        stmt = stmt.where(latest_snapshot.c.permit_status == filters.permit_status)

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
                ProjectMaster.project_business_type,
                ProjectMaster.government_program_type,
                ProjectMaster.project_urban_renewal_type,
                ProjectMaster.classification_confidence,
                ProjectMaster.location_confidence,
                Company.id.label("company_id"),
                Company.name_he.label("company_name_he"),
                latest_snapshot.c.snapshot_id,
                latest_snapshot.c.snapshot_date,
                latest_snapshot.c.project_status,
                latest_snapshot.c.permit_status,
                latest_snapshot.c.total_units,
                latest_snapshot.c.marketed_units,
                latest_snapshot.c.sold_units_cumulative,
                latest_snapshot.c.unsold_units,
                latest_snapshot.c.avg_price_per_sqm_cumulative,
                latest_snapshot.c.gross_profit_total_expected,
                latest_snapshot.c.gross_margin_expected_pct,
                Report.id.label("report_id"),
                Report.filing_reference,
                Report.period_end_date,
                Report.publish_date,
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

    return {
        "identity": {
            "project_id": detail["project_id"],
            "canonical_name": detail["canonical_name"],
            "company": {"id": detail["company_id"], "name_he": detail["company_name_he"]},
        },
        "classification": {
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
            "trust": _trust_map(provenance, ["city", "neighborhood", "district", "location_confidence"]),
        },
        "latest_snapshot": {
            "snapshot_id": detail["snapshot_id"],
            "snapshot_date": detail["snapshot_date"],
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
                "city": address.city,
                "street": address.street,
                "house_number_from": address.house_number_from,
                "house_number_to": address.house_number_to,
                "lat": address.lat,
                "lng": address.lng,
                "location_confidence": address.location_confidence,
                "location_quality": _location_quality(address.location_confidence),
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
            "source_url": detail["source_file_path"],
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
    rows = (
        await session.execute(
            select(Company.id)
            .join(ProjectMaster, ProjectMaster.company_id == Company.id)
            .where(ProjectMaster.is_publicly_visible.is_(True))
            .distinct()
        )
    ).scalars().all()

    companies: list[dict] = []
    for company_id in rows:
        detail = await get_company_detail(session, company_id)
        if detail is None:
            continue
        if filters.q and filters.q.lower() not in detail["name_he"].lower():
            continue
        if filters.city and filters.city not in {item["city"] for item in detail["city_coverage"]}:
            continue
        companies.append(
            {
                "id": detail["id"],
                "name_he": detail["name_he"],
                "ticker": detail["ticker"],
                "project_count": detail["project_count"],
                "city_count": detail["city_count"],
                "latest_report_period_end": detail["latest_report_period_end"],
                "latest_published_at": detail["latest_published_at"],
                "known_unsold_units": detail["kpis"]["known_unsold_units"],
                "projects_with_precise_location_count": detail["kpis"]["projects_with_precise_location_count"],
            }
        )

    sort_key = {
        "city_count": lambda item: item["city_count"],
        "latest_report": lambda item: item["latest_report_period_end"] or "",
        "project_count": lambda item: item["project_count"],
    }.get(filters.sort_by, lambda item: item["project_count"])
    return sorted(companies, key=sort_key, reverse=True)


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
    precise_locations = sum(1 for row in projects if row["location_confidence"] in {"exact", "street"})

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
    companies = await list_companies(session)
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
            select(ProjectSnapshot.permit_status)
            .join(ProjectMaster, ProjectMaster.id == ProjectSnapshot.project_id)
            .where(ProjectMaster.is_publicly_visible.is_(True), ProjectSnapshot.permit_status.is_not(None))
            .distinct()
            .order_by(ProjectSnapshot.permit_status.asc())
        )
    ).scalars().all()

    return {
        "companies": [{"id": str(item["id"]), "label": item["name_he"]} for item in companies],
        "cities": cities,
        "project_business_types": business_types,
        "government_program_types": government_types,
        "project_urban_renewal_types": urban_types,
        "permit_statuses": permit_statuses,
    }


async def get_map_projects(session: AsyncSession, filters: ProjectListFilters) -> dict:
    items, _ = await list_projects(session, replace(filters, page=1, page_size=500))
    features = []
    for item in items:
        address = (
            await session.execute(
                select(ProjectAddress)
                .where(ProjectAddress.project_id == item["project_id"])
                .order_by(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        geometry = None
        if address and address.lat is not None and address.lng is not None:
            geometry = {
                "type": "Point",
                "coordinates": [float(address.lng), float(address.lat)],
            }

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "project_id": item["project_id"],
                    "canonical_name": item["canonical_name"],
                    "company_name": item["company"]["name_he"],
                    "city": item["city"],
                    "project_business_type": item["project_business_type"],
                    "project_status": item["project_status"],
                    "avg_price_per_sqm_cumulative": item["avg_price_per_sqm_cumulative"],
                    "unsold_units": item["unsold_units"],
                    "location_confidence": item["location_confidence"],
                    "location_quality": item["location_quality"],
                },
            }
        )

    quality_counts = Counter(feature["properties"]["location_quality"] for feature in features)
    return {
        "features": features,
        "meta": {
            "available_projects": len(features),
            "projects_with_coordinates": quality_counts.get("exact", 0) + quality_counts.get("approximate", 0),
            "location_quality_breakdown": dict(quality_counts),
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
