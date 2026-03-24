from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditLog,
    AdminUser,
    Company,
    CompanyCoverageRegistry,
    FieldProvenance,
    ProjectAddress,
    ProjectAlias,
    ProjectDuplicateSuggestion,
    ProjectLandReserveDetail,
    ProjectMergeLog,
    ProjectMaster,
    ProjectMaterialDisclosure,
    ProjectSnapshot,
    ProjectSensitivityScenario,
    ProjectUrbanRenewalDetail,
    Report,
    StagingProjectCandidate,
    StagingReport,
)
from app.services.catalog import _confidence_level, _location_quality, _value_origin_summary
from app.services.identity_ops import assess_snapshot_chronology, get_coverage_dashboard, list_duplicate_suggestions, normalize_text
from app.services.spatial import (
    CITY_CENTROIDS,
    apply_manual_display_geometry,
    geocode_project_address,
    normalize_project_address,
    resolved_display_geometry,
    sync_project_display_geometry_from_addresses,
)


PLACEHOLDER_ADMIN_EMAIL = "phase3-admin@local"
BOOTSTRAP_STREETS_BY_CITY: dict[str, list[str]] = {
    "תל אביב": ["אבן גבירול", "דרך השלום", "החשמונאים", "הרצל", "מנחם בגין"],
    "ירושלים": ["יפו", "הנביאים", "הרצל", "כנפי נשרים", "עמק רפאים"],
    "אשדוד": ["בן גוריון", "העצמאות", "מנחם בגין", "רוגוזין", "שדרות ירושלים"],
    "אשקלון": ["בן גוריון", "ההסתדרות", "הרצל", "שדרות ירושלים"],
    "בת ים": ["בלפור", "הקוממיות", "הרצל", "יוספטל", "רוטשילד"],
    "כפר סבא": ["ויצמן", "הגליל", "ז'בוטינסקי", "טשרניחובסקי"],
    "לוד": ["הרצל", "יוספטל", "כצנלסון", "שדרות ירושלים"],
    "נתניה": ["הרצל", "דיזנגוף", "ז'בוטינסקי", "בן יהודה", "ויצמן"],
    "רחובות": ["הרצל", "אופנהיימר", "בילו", "יעקב", "מנוחה ונחלה"],
    "רמת גן": ["אבא הלל", "ביאליק", "הירדן", "ז'בוטינסקי", "בן גוריון"],
}
SNAPSHOT_DIFF_FIELDS = (
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


def _serialize_extension_row(row: object | None, fields: tuple[str, ...]) -> dict[str, object | None] | None:
    if row is None:
        return None
    payload = {field_name: getattr(row, field_name) for field_name in fields if getattr(row, field_name) is not None}
    return payload or None


async def _snapshot_extension_blocks(session: AsyncSession, project_id: UUID, snapshot_id: UUID) -> dict[str, dict[str, object | None]]:
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
            "material_disclosure": _serialize_extension_row(
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
            "sensitivity_scenario": _serialize_extension_row(
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
            "urban_renewal_detail": _serialize_extension_row(
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
            "land_reserve_detail": _serialize_extension_row(
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


def _confidence_score(level: str) -> Decimal:
    return {
        "high": Decimal("95.00"),
        "medium": Decimal("78.00"),
        "low": Decimal("55.00"),
    }.get(level, Decimal("55.00"))


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


def _snapshot_diff(current: ProjectSnapshot, previous: ProjectSnapshot | None) -> dict[str, dict[str, str | bool | None]]:
    diff: dict[str, dict[str, str | bool | None]] = {}
    for field_name in SNAPSHOT_DIFF_FIELDS:
        before = getattr(previous, field_name, None) if previous else None
        after = getattr(current, field_name, None)
        diff[field_name] = {
            "before": None if before is None else str(before),
            "after": None if after is None else str(after),
            "changed": (None if before is None else str(before)) != (None if after is None else str(after)),
        }
    return diff


async def _get_project(session: AsyncSession, project_id: UUID) -> ProjectMaster | None:
    return (await session.execute(select(ProjectMaster).where(ProjectMaster.id == project_id))).scalar_one_or_none()


async def _get_snapshot(session: AsyncSession, snapshot_id: UUID) -> ProjectSnapshot | None:
    return (await session.execute(select(ProjectSnapshot).where(ProjectSnapshot.id == snapshot_id))).scalar_one_or_none()


async def _latest_snapshot_or_none(session: AsyncSession, project_id: UUID) -> ProjectSnapshot | None:
    return (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _snapshot_before(
    session: AsyncSession,
    project_id: UUID,
    snapshot_date: date,
    exclude_snapshot_id: UUID | None = None,
) -> ProjectSnapshot | None:
    stmt = (
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
    )
    if exclude_snapshot_id is not None:
        stmt = stmt.where(ProjectSnapshot.id != exclude_snapshot_id)

    rows = (await session.execute(stmt)).scalars().all()
    for snapshot in rows:
        if snapshot.snapshot_date < snapshot_date:
            return snapshot
    return rows[0] if rows else None


async def _get_or_create_manual_source_report(
    session: AsyncSession,
    *,
    company_id: UUID,
    filing_reference: str,
    reference_date: date,
    note: str,
) -> Report:
    report = (
        await session.execute(
            select(Report).where(
                Report.company_id == company_id,
                Report.filing_reference == filing_reference,
                Report.period_end_date == reference_date,
            )
        )
    ).scalar_one_or_none()
    if report is None:
        report = Report(
            id=uuid4(),
            company_id=company_id,
            report_type="presentation",
            period_type="interim",
            period_end_date=reference_date,
            publish_date=reference_date,
            filing_reference=filing_reference,
            source_url=None,
            source_file_path=None,
            source_is_official=False,
            source_label="Manual admin source",
            ingestion_status="published",
            notes=note,
            parser_version="manual_admin_v1",
            status="reviewed",
        )
        session.add(report)
        await session.flush()
    return report


async def _report_for_project(session: AsyncSession, project: ProjectMaster, reason_label: str) -> Report:
    latest_snapshot = await _latest_snapshot_or_none(session, project.id)
    if latest_snapshot is not None:
        report = (await session.execute(select(Report).where(Report.id == latest_snapshot.report_id))).scalar_one_or_none()
        if report is not None:
            return report

    return await _get_or_create_manual_source_report(
        session,
        company_id=project.company_id,
        filing_reference=f"Manual admin source - {reason_label}",
        reference_date=date.today(),
        note="Auto-created to preserve provenance for direct admin project updates.",
    )


async def _write_provenance(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    field_name: str,
    normalized_value: str | None,
    source_report_id: UUID,
    value_origin_type: str,
    confidence_level: str,
    admin_user_id: UUID,
    source_section: str,
    review_note: str | None,
    source_page: int | None = None,
    raw_value: str | None = None,
    ) -> None:
    session.add(
        FieldProvenance(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            raw_value=raw_value if raw_value is not None else normalized_value,
            normalized_value=normalized_value,
            source_report_id=source_report_id,
            source_page=source_page,
            source_section=source_section,
            extraction_method="admin",
            parser_version="manual_admin_v1",
            confidence_score=_confidence_score(confidence_level),
            value_origin_type=value_origin_type,
            review_status="approved",
            review_note=review_note,
            reviewed_by=admin_user_id,
            reviewed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
    )


async def _record_audit(
    session: AsyncSession,
    *,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
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


async def _serialize_snapshot_summary(session: AsyncSession, snapshot: ProjectSnapshot, previous: ProjectSnapshot | None) -> dict:
    report = (await session.execute(select(Report).where(Report.id == snapshot.report_id))).scalar_one_or_none()
    extension_blocks = await _snapshot_extension_blocks(session, snapshot.project_id, snapshot.id)
    return {
        "id": snapshot.id,
        "report_id": snapshot.report_id,
        "report_name": report.filing_reference if report else None,
        "snapshot_date": snapshot.snapshot_date,
        "lifecycle_stage": snapshot.lifecycle_stage,
        "disclosure_level": snapshot.disclosure_level,
        "source_section_kind": snapshot.source_section_kind,
        "project_status": snapshot.project_status,
        "permit_status": snapshot.permit_status,
        "total_units": snapshot.total_units,
        "marketed_units": snapshot.marketed_units,
        "sold_units_cumulative": snapshot.sold_units_cumulative,
        "unsold_units": snapshot.unsold_units,
        "avg_price_per_sqm_cumulative": snapshot.avg_price_per_sqm_cumulative,
        "gross_profit_total_expected": snapshot.gross_profit_total_expected,
        "gross_margin_expected_pct": snapshot.gross_margin_expected_pct,
        "chronology_status": snapshot.chronology_status,
        "chronology_notes": snapshot.chronology_notes,
        "notes_internal": snapshot.notes_internal,
        "diff_summary": _snapshot_diff(snapshot, previous),
        "extension_blocks": extension_blocks,
    }


async def _project_related_provenance(
    session: AsyncSession,
    project_id: UUID,
    addresses: list[ProjectAddress],
    snapshots: list[ProjectSnapshot],
) -> list[FieldProvenance]:
    entity_ids: list[UUID] = [project_id, *[address.id for address in addresses], *[snapshot.id for snapshot in snapshots]]
    return (
        await session.execute(
            select(FieldProvenance)
            .where(
                FieldProvenance.entity_id.in_(entity_ids),
                FieldProvenance.entity_type.in_(
                    [
                        "project_master",
                        "snapshot",
                        "address",
                        "material_disclosure",
                        "sensitivity_scenario",
                        "urban_renewal_detail",
                        "land_reserve_detail",
                    ]
                ),
            )
            .order_by(FieldProvenance.created_at.desc())
        )
    ).scalars().all()


async def _build_project_detail(session: AsyncSession, project: ProjectMaster) -> dict:
    company = (await session.execute(select(Company).where(Company.id == project.company_id))).scalar_one()
    aliases = (
        await session.execute(
            select(ProjectAlias).where(ProjectAlias.project_id == project.id).order_by(ProjectAlias.created_at.asc())
        )
    ).scalars().all()
    addresses = (
        await session.execute(
            select(ProjectAddress)
            .where(ProjectAddress.project_id == project.id)
            .order_by(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc())
        )
    ).scalars().all()
    snapshots = (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project.id)
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
        )
    ).scalars().all()
    provenance = await _project_related_provenance(session, project.id, addresses, snapshots)

    source_ids = {row.source_report_id for row in provenance}
    source_ids.update(snapshot.report_id for snapshot in snapshots)
    linked_sources = (
        await session.execute(select(Report).where(Report.id.in_(list(source_ids))))
    ).scalars().all() if source_ids else []
    linked_candidates_rows = (
        await session.execute(
            select(StagingProjectCandidate, Report)
            .join(StagingReport, StagingReport.id == StagingProjectCandidate.staging_report_id)
            .join(Report, Report.id == StagingReport.report_id)
            .where(StagingProjectCandidate.matched_project_id == project.id)
            .order_by(StagingProjectCandidate.updated_at.desc())
        )
    ).all()
    audit_ids = [project.id, *[snapshot.id for snapshot in snapshots], *[alias.id for alias in aliases], *[address.id for address in addresses]]
    audit_log = (
        await session.execute(
            select(AdminAuditLog)
            .where(AdminAuditLog.entity_id.in_(audit_ids))
            .order_by(AdminAuditLog.created_at.desc())
        )
    ).scalars().all()

    latest_snapshot = snapshots[0] if snapshots else None
    snapshots_payload: list[dict] = []
    previous_snapshot: ProjectSnapshot | None = None
    for snapshot in reversed(snapshots):
        snapshots_payload.append(await _serialize_snapshot_summary(session, snapshot, previous_snapshot))
        previous_snapshot = snapshot
    snapshots_payload.reverse()

    latest_snapshot_payload = None
    if latest_snapshot is not None:
        extension_blocks = await _snapshot_extension_blocks(session, project.id, latest_snapshot.id)
        latest_snapshot_payload = {
            "snapshot_id": latest_snapshot.id,
            "snapshot_date": latest_snapshot.snapshot_date,
            "lifecycle_stage": latest_snapshot.lifecycle_stage or project.lifecycle_stage,
            "disclosure_level": latest_snapshot.disclosure_level or project.disclosure_level,
            "source_section_kind": latest_snapshot.source_section_kind,
            "project_status": latest_snapshot.project_status,
            "permit_status": latest_snapshot.permit_status,
            "total_units": latest_snapshot.total_units,
            "marketed_units": latest_snapshot.marketed_units,
            "sold_units_cumulative": latest_snapshot.sold_units_cumulative,
            "unsold_units": latest_snapshot.unsold_units,
            "avg_price_per_sqm_cumulative": latest_snapshot.avg_price_per_sqm_cumulative,
            "gross_profit_total_expected": latest_snapshot.gross_profit_total_expected,
            "gross_margin_expected_pct": latest_snapshot.gross_margin_expected_pct,
            "trust": _trust_map(
                [row for row in provenance if row.entity_id == latest_snapshot.id],
                [
                    "permit_status",
                    "project_status",
                    "total_units",
                    "marketed_units",
                    "sold_units_cumulative",
                    "unsold_units",
                    "avg_price_per_sqm_cumulative",
                    "gross_profit_total_expected",
                    "gross_margin_expected_pct",
                ],
            ),
            "extension_blocks": extension_blocks,
        }

    classification_rows = [row for row in provenance if row.entity_id in ([project.id] + ([latest_snapshot.id] if latest_snapshot else []))]
    display_geometry = resolved_display_geometry(project)

    return {
        "id": project.id,
        "canonical_name": project.canonical_name,
        "company": {"id": company.id, "name_he": company.name_he},
        "classification": {
            "lifecycle_stage": project.lifecycle_stage,
            "disclosure_level": project.disclosure_level,
            "project_business_type": project.project_business_type,
            "government_program_type": project.government_program_type,
            "project_urban_renewal_type": project.project_urban_renewal_type,
            "project_status": latest_snapshot.project_status if latest_snapshot else None,
            "permit_status": latest_snapshot.permit_status if latest_snapshot else None,
            "classification_confidence": project.classification_confidence,
            "trust": _trust_map(
                classification_rows,
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
            "city": project.city,
            "neighborhood": project.neighborhood,
            "district": project.district,
            "location_confidence": project.location_confidence,
            "location_quality": _location_quality(project.location_confidence),
            "address_summary": display_geometry["address_summary"],
            "trust": _trust_map(
                [row for row in provenance if row.entity_id == project.id],
                ["city", "neighborhood", "district", "location_confidence"],
            ),
        },
        "display_geometry": display_geometry,
        "latest_snapshot": latest_snapshot_payload,
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
                "parcel_block": address.parcel_block,
                "parcel_number": address.parcel_number,
                "sub_parcel": address.sub_parcel,
                "address_note": address.address_note,
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
                "value_origin_type": next(
                    (row.value_origin_type for row in provenance if row.entity_id == address.id and row.field_name == "address_record"),
                    "unknown",
                ),
            }
            for address in addresses
        ],
        "aliases": [
            {
                "id": alias.id,
                "alias_name": alias.alias_name,
                "value_origin_type": alias.value_origin_type,
                "alias_source_type": alias.alias_source_type,
                "source_report_id": alias.source_report_id,
                "is_active": alias.is_active,
                "notes": alias.notes,
                "created_at": alias.created_at,
                "updated_at": alias.updated_at,
            }
            for alias in aliases
        ],
        "snapshots": snapshots_payload,
        "linked_sources": [
            {
                "report_id": report.id,
                "report_name": report.filing_reference,
                "source_label": report.source_label,
                "source_url": report.source_url or report.source_file_path,
                "ingestion_status": report.ingestion_status,
                "period_end_date": report.period_end_date,
                "published_at": report.publish_date,
            }
            for report in sorted(linked_sources, key=lambda item: (item.period_end_date, item.publish_date or date.min), reverse=True)
        ],
        "linked_candidates": [
            {
                "candidate_id": candidate.id,
                "candidate_project_name": candidate.candidate_project_name,
                "matching_status": candidate.matching_status,
                "publish_status": candidate.publish_status,
                "review_status": candidate.review_status,
                "source_report_id": report.id,
                "source_report_name": report.filing_reference,
            }
            for candidate, report in linked_candidates_rows
        ],
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
        "provenance_summary": _value_origin_summary(provenance),
        "is_publicly_visible": project.is_publicly_visible,
        "source_conflict_flag": project.source_conflict_flag,
        "notes_internal": project.notes_internal,
        "audit_log": [
            {
                "id": row.id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "diff_json": row.diff_json,
                "comment": row.comment,
                "created_at": row.created_at,
            }
            for row in audit_log
        ],
    }


async def list_admin_projects(session: AsyncSession, filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    rows = (
        await session.execute(
            select(ProjectMaster, Company)
            .join(Company, Company.id == ProjectMaster.company_id)
            .where(ProjectMaster.deleted_at.is_(None))
            .order_by(ProjectMaster.canonical_name.asc())
        )
    ).all()

    items: list[dict] = []
    for project, company in rows:
        latest_snapshot = await _latest_snapshot_or_none(session, project.id)
        source_count = int(
            (
                await session.execute(
                    select(func.count(func.distinct(ProjectSnapshot.report_id))).where(ProjectSnapshot.project_id == project.id)
                )
            ).scalar_one()
        )
        address_count = int(
            (
                await session.execute(
                    select(func.count()).select_from(ProjectAddress).where(ProjectAddress.project_id == project.id)
                )
            ).scalar_one()
        )
        item = {
            "id": project.id,
            "canonical_name": project.canonical_name,
            "company": {"id": project.company_id, "name_he": company.name_he},
            "city": project.city,
            "lifecycle_stage": project.lifecycle_stage,
            "disclosure_level": project.disclosure_level,
            "project_business_type": project.project_business_type,
            "government_program_type": project.government_program_type,
            "project_urban_renewal_type": project.project_urban_renewal_type,
            "project_status": latest_snapshot.project_status if latest_snapshot else None,
            "permit_status": latest_snapshot.permit_status if latest_snapshot else None,
            "classification_confidence": project.classification_confidence,
            "location_confidence": project.location_confidence,
            "needs_admin_review": latest_snapshot.needs_admin_review if latest_snapshot else False,
            "latest_snapshot_date": latest_snapshot.snapshot_date if latest_snapshot else None,
            "source_count": source_count,
            "address_count": address_count,
            "is_publicly_visible": project.is_publicly_visible,
            "source_conflict_flag": project.source_conflict_flag,
        }
        if filters.get("q"):
            term = normalize_text(filters["q"])
            aliases = (
                await session.execute(select(ProjectAlias.alias_name).where(ProjectAlias.project_id == project.id))
            ).scalars().all()
            address_bits = (
                await session.execute(
                    select(ProjectAddress.address_text_raw, ProjectAddress.street, ProjectAddress.city).where(
                        ProjectAddress.project_id == project.id
                    )
                )
            ).all()
            searchable = " ".join(
                normalize_text(value)
                for value in [
                    project.canonical_name,
                    company.name_he,
                    project.city or "",
                    project.neighborhood or "",
                    *aliases,
                    *[value for row in address_bits for value in row if value],
                ]
            )
            if term not in searchable:
                continue
        if filters.get("company_id") and str(project.company_id) != filters["company_id"]:
            continue
        if filters.get("city") and (project.city or "").lower() != filters["city"].strip().lower():
            continue
        if filters.get("project_business_type") and project.project_business_type != filters["project_business_type"]:
            continue
        if filters.get("government_program_type") and project.government_program_type != filters["government_program_type"]:
            continue
        if filters.get("project_urban_renewal_type") and project.project_urban_renewal_type != filters["project_urban_renewal_type"]:
            continue
        if filters.get("location_confidence") and project.location_confidence != filters["location_confidence"]:
            continue
        if filters.get("visibility"):
            wanted_visibility = filters["visibility"] == "public"
            if project.is_publicly_visible != wanted_visibility:
                continue
        items.append(item)

    sort_by = filters.get("sort_by", "latest_snapshot")
    sort_key = {
        "company": lambda item: item["company"]["name_he"] or "",
        "city": lambda item: item["city"] or "",
        "source_count": lambda item: item["source_count"],
        "address_count": lambda item: item["address_count"],
        "latest_snapshot": lambda item: item["latest_snapshot_date"] or date.min,
        "canonical_name": lambda item: item["canonical_name"],
    }.get(sort_by, lambda item: item["latest_snapshot_date"] or date.min)
    reverse = sort_by in {"latest_snapshot", "source_count", "address_count"}
    return sorted(items, key=sort_key, reverse=reverse)


async def get_admin_project_detail(session: AsyncSession, project_id: UUID) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None
    return await _build_project_detail(session, project)


async def create_admin_project(session: AsyncSession, payload: dict) -> dict:
    admin_user = await _get_placeholder_admin(session)
    project = ProjectMaster(
        id=uuid4(),
        company_id=payload["company_id"],
        canonical_name=payload["canonical_name"],
        city=payload.get("city"),
        neighborhood=payload.get("neighborhood"),
        asset_domain="residential_only",
        project_business_type=payload["project_business_type"],
        government_program_type=payload.get("government_program_type", "none"),
        project_urban_renewal_type=payload.get("project_urban_renewal_type", "none"),
        project_deal_type="ownership",
        project_usage_profile="residential_only",
        lifecycle_stage=payload.get("lifecycle_stage"),
        disclosure_level=payload.get("disclosure_level"),
        is_publicly_visible=payload.get("is_publicly_visible", False),
        location_confidence=payload.get("location_confidence", "city_only"),
        classification_confidence="medium",
        mapping_review_status="approved",
        source_conflict_flag=payload.get("source_conflict_flag", False),
        notes_internal=payload.get("notes_internal"),
    )
    session.add(project)
    await session.flush()
    await sync_project_display_geometry_from_addresses(session, project, force=True)

    report = await _get_or_create_manual_source_report(
        session,
        company_id=project.company_id,
        filing_reference=f"Manual project entry - {project.canonical_name}",
        reference_date=date.today(),
        note="Auto-created source for direct manual project creation.",
    )
    for field_name in (
        "canonical_name",
        "city",
        "neighborhood",
        "lifecycle_stage",
        "disclosure_level",
        "project_business_type",
        "government_program_type",
        "project_urban_renewal_type",
        "location_confidence",
        "display_geometry_type",
        "display_geometry_source",
        "display_geometry_confidence",
    ):
        value = getattr(project, field_name)
        if value is not None:
            await _write_provenance(
                session,
                entity_type="project_master",
                entity_id=project.id,
                field_name=field_name,
                normalized_value=str(value),
                source_report_id=report.id,
                value_origin_type=payload.get("value_origin_type", "manual"),
                confidence_level="medium",
                admin_user_id=admin_user.id,
                source_section="Direct project creation",
                review_note=payload.get("reviewer_note"),
            )

    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_create",
        entity_type="project_master",
        entity_id=project.id,
        diff_json=payload,
        comment=payload.get("reviewer_note"),
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def update_admin_project(session: AsyncSession, project_id: UUID, payload: dict) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    latest_snapshot = await _latest_snapshot_or_none(session, project_id)
    report = await _report_for_project(session, project, project.canonical_name)
    reason = payload.get("change_reason")
    diffs: dict[str, dict[str, object | None]] = {}
    field_origin_types = payload.get("field_origin_types", {})

    for field_name in [
        "canonical_name",
        "company_id",
        "lifecycle_stage",
        "disclosure_level",
        "project_business_type",
        "government_program_type",
        "project_urban_renewal_type",
        "city",
        "neighborhood",
        "location_confidence",
        "is_publicly_visible",
        "source_conflict_flag",
        "notes_internal",
    ]:
        if field_name in payload and getattr(project, field_name) != payload[field_name]:
            diffs[field_name] = {"before": getattr(project, field_name), "after": payload[field_name]}
            setattr(project, field_name, payload[field_name])
            if field_name != "notes_internal":
                await _write_provenance(
                    session,
                    entity_type="project_master",
                    entity_id=project.id,
                    field_name=field_name,
                    normalized_value=None if payload[field_name] is None else str(payload[field_name]),
                    source_report_id=report.id,
                    value_origin_type=field_origin_types.get(field_name, "manual"),
                    confidence_level="medium",
                    admin_user_id=admin_user.id,
                    source_section="Direct admin project edit",
                    review_note=reason,
                )

    if latest_snapshot is not None:
        for field_name in ["permit_status", "project_status"]:
            if field_name in payload and getattr(latest_snapshot, field_name) != payload[field_name]:
                diffs[field_name] = {"before": getattr(latest_snapshot, field_name), "after": payload[field_name]}
                setattr(latest_snapshot, field_name, payload[field_name])
                await _write_provenance(
                    session,
                    entity_type="snapshot",
                    entity_id=latest_snapshot.id,
                    field_name=field_name,
                    normalized_value=None if payload[field_name] is None else str(payload[field_name]),
                    source_report_id=report.id,
                    value_origin_type=field_origin_types.get(field_name, "manual"),
                    confidence_level="medium",
                    admin_user_id=admin_user.id,
                    source_section="Direct admin project edit",
                    review_note=reason,
                )

    if any(field in payload for field in ["city", "location_confidence"]) and project.display_geometry_source != "manual_override":
        await sync_project_display_geometry_from_addresses(session, project, force=True)

    if diffs:
        await _record_audit(
            session,
            actor_user_id=admin_user.id,
            action="admin_project_update",
            entity_type="project_master",
            entity_id=project.id,
            diff_json=diffs,
            comment=reason,
        )
        await session.commit()
    else:
        await session.rollback()

    return await _build_project_detail(session, project)


async def add_project_alias(session: AsyncSession, project_id: UUID, payload: dict) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    report = await _report_for_project(session, project, project.canonical_name)
    reason = payload.get("reviewer_note")
    alias_name = payload["alias_name"].strip()
    if not alias_name:
        return await _build_project_detail(session, project)

    existing_alias = (
        await session.execute(
            select(ProjectAlias).where(ProjectAlias.project_id == project.id, ProjectAlias.alias_name == alias_name)
        )
    ).scalar_one_or_none()
    if existing_alias is None:
        alias = ProjectAlias(
            id=uuid4(),
            project_id=project.id,
            alias_name=alias_name,
            value_origin_type=payload.get("value_origin_type", "manual"),
            alias_source_type=payload.get("alias_source_type", "manual"),
            source_report_id=payload.get("source_report_id"),
            is_active=payload.get("is_active", True),
            notes=payload.get("notes"),
        )
        session.add(alias)
        await session.flush()
    else:
        alias = existing_alias
        alias.value_origin_type = payload.get("value_origin_type", alias.value_origin_type)
        alias.alias_source_type = payload.get("alias_source_type", alias.alias_source_type)
        alias.source_report_id = payload.get("source_report_id", alias.source_report_id)
        alias.is_active = payload.get("is_active", alias.is_active)
        alias.notes = payload.get("notes", alias.notes)

    diff_json: dict[str, object] = {"alias_name": alias_name, "make_preferred": payload.get("make_preferred", False)}
    if payload.get("make_preferred") and project.canonical_name != alias_name:
        previous_name = project.canonical_name
        old_canonical_alias = (
            await session.execute(
                select(ProjectAlias).where(ProjectAlias.project_id == project.id, ProjectAlias.alias_name == previous_name)
            )
        ).scalar_one_or_none()
        if old_canonical_alias is None:
            session.add(
                ProjectAlias(
                    id=uuid4(),
                    project_id=project.id,
                    alias_name=previous_name,
                    value_origin_type="manual",
                    alias_source_type="system",
                    is_active=True,
                    notes="Auto-created when alias was promoted to canonical name.",
                )
            )
        project.canonical_name = alias_name
        await _write_provenance(
            session,
            entity_type="project_master",
            entity_id=project.id,
            field_name="canonical_name",
            normalized_value=alias_name,
            source_report_id=report.id,
            value_origin_type=payload.get("value_origin_type", "manual"),
            confidence_level="medium",
            admin_user_id=admin_user.id,
            source_section="Admin alias management",
            review_note=reason,
        )
        diff_json["previous_canonical_name"] = previous_name

    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_alias_add",
        entity_type="project_alias",
        entity_id=alias.id,
        diff_json=diff_json,
        comment=reason,
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def delete_project_alias(session: AsyncSession, project_id: UUID, alias_id: UUID, reviewer_note: str | None) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None
    alias = (
        await session.execute(
            select(ProjectAlias).where(ProjectAlias.id == alias_id, ProjectAlias.project_id == project_id)
        )
    ).scalar_one_or_none()
    if alias is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    alias_name = alias.alias_name
    await session.delete(alias)
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_alias_delete",
        entity_type="project_alias",
        entity_id=alias_id,
        diff_json={"alias_name": alias_name},
        comment=reviewer_note,
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def list_project_snapshots(session: AsyncSession, project_id: UUID) -> list[dict] | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None
    snapshots = (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
        )
    ).scalars().all()
    items: list[dict] = []
    previous_snapshot: ProjectSnapshot | None = None
    for snapshot in reversed(snapshots):
        items.append(await _serialize_snapshot_summary(session, snapshot, previous_snapshot))
        previous_snapshot = snapshot
    items.reverse()
    return items


def _normalize_reference_term(value: str | None) -> str:
    return normalize_text(value or "")


async def list_admin_location_reference(
    session: AsyncSession,
    *,
    city: str | None = None,
    q: str | None = None,
) -> dict:
    city_rows = (
        await session.execute(
            select(ProjectMaster.city)
            .where(ProjectMaster.city.is_not(None), ProjectMaster.deleted_at.is_(None))
            .distinct()
        )
    ).scalars().all()
    address_city_rows = (
        await session.execute(
            select(ProjectAddress.normalized_city, ProjectAddress.city)
            .where(or_(ProjectAddress.normalized_city.is_not(None), ProjectAddress.city.is_not(None)))
            .distinct()
        )
    ).all()
    cities = {
        value.strip()
        for value in city_rows
        if isinstance(value, str) and value.strip()
    }
    for normalized_city, raw_city in address_city_rows:
        for value in (normalized_city, raw_city):
            if isinstance(value, str) and value.strip():
                cities.add(value.strip())
    cities.update(CITY_CENTROIDS.keys())
    cities.update(BOOTSTRAP_STREETS_BY_CITY.keys())

    search_term = _normalize_reference_term(q)
    sorted_cities = sorted(
        [
            value
            for value in cities
            if not search_term or search_term in _normalize_reference_term(value)
        ]
    )

    streets_stmt = select(ProjectAddress.normalized_street, ProjectAddress.street).where(
        or_(ProjectAddress.normalized_street.is_not(None), ProjectAddress.street.is_not(None))
    )
    if city:
        normalized_city = city.strip()
        streets_stmt = streets_stmt.where(
            or_(ProjectAddress.normalized_city == normalized_city, ProjectAddress.city == normalized_city)
        )

    street_rows = (await session.execute(streets_stmt.distinct())).all()
    streets = {
        value.strip()
        for normalized_street, raw_street in street_rows
        for value in (normalized_street, raw_street)
        if isinstance(value, str) and value.strip()
    }
    if city and city.strip() in BOOTSTRAP_STREETS_BY_CITY:
        streets.update(BOOTSTRAP_STREETS_BY_CITY[city.strip()])
    sorted_streets = sorted(
        [
            value
            for value in streets
            if not search_term or search_term in _normalize_reference_term(value)
        ]
    )

    return {
        "cities": sorted_cities[:200],
        "streets": sorted_streets[:200],
    }


async def create_project_snapshot(session: AsyncSession, project_id: UUID, payload: dict) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    report_id = payload.get("report_id")
    if report_id:
        report = (await session.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    else:
        report = await _get_or_create_manual_source_report(
            session,
            company_id=project.company_id,
            filing_reference=f"Manual snapshot - {project.canonical_name}",
            reference_date=payload["snapshot_date"],
            note="Auto-created source for direct manual snapshot creation.",
        )
    if report is None:
        return None

    existing_snapshot = (
        await session.execute(
            select(ProjectSnapshot).where(ProjectSnapshot.project_id == project_id, ProjectSnapshot.report_id == report.id)
        )
    ).scalar_one_or_none()
    if existing_snapshot is not None:
        return await update_snapshot(session, existing_snapshot.id, payload)

    same_period_snapshot = (
        await session.execute(
            select(ProjectSnapshot).where(
                ProjectSnapshot.project_id == project_id,
                ProjectSnapshot.snapshot_date == payload["snapshot_date"],
            )
        )
    ).scalar_one_or_none()
    if same_period_snapshot is not None:
        return await update_snapshot(session, same_period_snapshot.id, payload)

    chronology_status, chronology_notes = await assess_snapshot_chronology(
        session,
        project.id,
        payload["snapshot_date"],
        report.id,
    )
    snapshot = ProjectSnapshot(
        id=uuid4(),
        project_id=project_id,
        report_id=report.id,
        snapshot_date=payload["snapshot_date"],
        lifecycle_stage=payload.get("lifecycle_stage") or project.lifecycle_stage,
        disclosure_level=payload.get("disclosure_level") or project.disclosure_level,
        source_section_kind=payload.get("source_section_kind"),
        total_units=payload.get("total_units"),
        marketed_units=payload.get("marketed_units"),
        sold_units_cumulative=payload.get("sold_units_cumulative"),
        unsold_units=payload.get("unsold_units"),
        avg_price_per_sqm_cumulative=payload.get("avg_price_per_sqm_cumulative"),
        gross_profit_total_expected=payload.get("gross_profit_total_expected"),
        gross_margin_expected_pct=payload.get("gross_margin_expected_pct"),
        permit_status=payload.get("permit_status"),
        project_status=payload.get("project_status"),
        chronology_status=chronology_status,
        chronology_notes=chronology_notes,
        notes_internal=payload.get("notes_internal"),
        needs_admin_review=False,
    )
    session.add(snapshot)
    await session.flush()

    for field_name in [*SNAPSHOT_DIFF_FIELDS, "lifecycle_stage", "disclosure_level", "source_section_kind"]:
        value = getattr(snapshot, field_name, None)
        if value is not None:
            await _write_provenance(
                session,
                entity_type="snapshot",
                entity_id=snapshot.id,
                field_name=field_name,
                normalized_value=str(value),
                source_report_id=report.id,
                value_origin_type=payload.get("value_origin_type", "manual"),
                confidence_level=payload.get("confidence_level", "medium"),
                admin_user_id=admin_user.id,
                source_section="Direct snapshot creation",
                review_note=payload.get("reviewer_note"),
            )

    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_snapshot_create",
        entity_type="snapshot",
        entity_id=snapshot.id,
        diff_json=payload,
        comment=payload.get("reviewer_note"),
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def update_snapshot(session: AsyncSession, snapshot_id: UUID, payload: dict) -> dict | None:
    snapshot = await _get_snapshot(session, snapshot_id)
    if snapshot is None:
        return None
    project = await _get_project(session, snapshot.project_id)
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    reason = payload.get("reviewer_note")
    report = None
    if payload.get("report_id"):
        report = (await session.execute(select(Report).where(Report.id == payload["report_id"]))).scalar_one_or_none()
    if report is None:
        report = (await session.execute(select(Report).where(Report.id == snapshot.report_id))).scalar_one_or_none()
    if report is None:
        report = await _get_or_create_manual_source_report(
            session,
            company_id=project.company_id,
            filing_reference=f"Manual snapshot - {project.canonical_name}",
            reference_date=payload.get("snapshot_date") or snapshot.snapshot_date,
            note="Auto-created source for direct manual snapshot update.",
        )

    chronology_status, chronology_notes = await assess_snapshot_chronology(
        session,
        project.id,
        payload.get("snapshot_date") or snapshot.snapshot_date,
        report.id,
        exclude_snapshot_id=snapshot.id,
    )
    previous_snapshot = await _snapshot_before(
        session,
        project.id,
        payload.get("snapshot_date") or snapshot.snapshot_date,
        exclude_snapshot_id=snapshot.id,
    )
    diffs: dict[str, dict[str, object | None]] = {}
    updatable_fields = [
        "snapshot_date",
        "report_id",
        "lifecycle_stage",
        "disclosure_level",
        "source_section_kind",
        "total_units",
        "marketed_units",
        "sold_units_cumulative",
        "unsold_units",
        "avg_price_per_sqm_cumulative",
        "gross_profit_total_expected",
        "gross_margin_expected_pct",
        "permit_status",
        "project_status",
        "notes_internal",
    ]
    for field_name in updatable_fields:
        if field_name not in payload:
            continue
        next_value = report.id if field_name == "report_id" and report is not None else payload[field_name]
        if getattr(snapshot, field_name) != next_value:
            diffs[field_name] = {"before": getattr(snapshot, field_name), "after": next_value}
            setattr(snapshot, field_name, next_value)
            if field_name in SNAPSHOT_DIFF_FIELDS:
                await _write_provenance(
                    session,
                    entity_type="snapshot",
                    entity_id=snapshot.id,
                    field_name=field_name,
                    normalized_value=None if next_value is None else str(next_value),
                    source_report_id=report.id,
                    value_origin_type=payload.get("value_origin_type", "manual"),
                    confidence_level=payload.get("confidence_level", "medium"),
                    admin_user_id=admin_user.id,
                    source_section="Direct snapshot edit",
                    review_note=reason,
                )

    snapshot.chronology_status = chronology_status
    snapshot.chronology_notes = chronology_notes

    if diffs:
        diffs["diff_summary"] = _snapshot_diff(snapshot, previous_snapshot)
        diffs["chronology_status"] = {"before": None, "after": chronology_status}
        await _record_audit(
            session,
            actor_user_id=admin_user.id,
            action="admin_snapshot_update",
            entity_type="snapshot",
            entity_id=snapshot.id,
            diff_json=diffs,
            comment=reason,
        )
        await session.commit()
    else:
        await session.rollback()

    return await _build_project_detail(session, project)


async def upsert_project_address(
    session: AsyncSession,
    project_id: UUID,
    payload: dict,
    *,
    address_id: UUID | None = None,
) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    report = await _report_for_project(session, project, project.canonical_name)
    reason = payload.get("change_reason")
    if address_id is not None:
        address = (
            await session.execute(
                select(ProjectAddress).where(ProjectAddress.id == address_id, ProjectAddress.project_id == project_id)
            )
        ).scalar_one_or_none()
        if address is None:
            return None
        action = "admin_project_address_update"
    else:
        address = ProjectAddress(
            id=uuid4(),
            project_id=project_id,
            source_type="admin",
            assigned_by=admin_user.id,
            assigned_at=datetime.now(UTC),
        )
        session.add(address)
        action = "admin_project_address_create"

    diffs: dict[str, dict[str, object | None]] = {}
    for field_name in [
        "address_text_raw",
        "street",
        "house_number_from",
        "house_number_to",
        "city",
        "parcel_block",
        "parcel_number",
        "sub_parcel",
        "address_note",
        "lat",
        "lng",
        "location_confidence",
        "is_primary",
        "normalized_display_address",
        "geocoding_method",
        "geocoding_source_label",
    ]:
        if field_name in payload and getattr(address, field_name) != payload[field_name]:
            diffs[field_name] = {"before": getattr(address, field_name), "after": payload[field_name]}
            setattr(address, field_name, payload[field_name])

    if payload.get("lat") is not None and payload.get("lng") is not None:
        address.geometry_source = "manual_override"
        address.geocoding_status = "manual_override"
        address.geocoding_method = payload.get("geocoding_method") or "manual_point"
        address.geocoding_provider = "admin"
        address.geocoding_source_label = payload.get("geocoding_source_label") or "Admin manual override"
        address.geocoding_note = "Coordinates were set manually in admin."
    elif address.geometry_source == "unknown" and address.source_type == "admin":
        address.geometry_source = "reported"

    if payload.get("is_primary"):
        other_addresses = (
            await session.execute(select(ProjectAddress).where(ProjectAddress.project_id == project_id, ProjectAddress.id != address.id))
        ).scalars().all()
        for other in other_addresses:
            other.is_primary = False

    await normalize_project_address(session, project=project, address=address, admin_user=admin_user)
    if payload.get("normalized_display_address"):
        address.normalized_display_address = payload["normalized_display_address"]
    if payload.get("geocoding_method"):
        address.geocoding_method = payload["geocoding_method"]
    if payload.get("geocoding_source_label"):
        address.geocoding_source_label = payload["geocoding_source_label"]
    await session.flush()
    await sync_project_display_geometry_from_addresses(session, project, force=True)
    await _write_provenance(
        session,
        entity_type="address",
        entity_id=address.id,
        field_name="address_record",
        normalized_value=address.normalized_address_text or address.city or address.street or address.address_text_raw,
        raw_value=address.address_text_raw,
        source_report_id=report.id,
        value_origin_type=payload.get("value_origin_type", "manual"),
        confidence_level="medium",
        admin_user_id=admin_user.id,
        source_section="Admin address management",
        review_note=reason,
    )
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action=action,
        entity_type="address",
        entity_id=address.id,
        diff_json=diffs or payload,
        comment=reason,
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def delete_project_address(session: AsyncSession, project_id: UUID, address_id: UUID, reason: str) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None

    address = (
        await session.execute(
            select(ProjectAddress).where(ProjectAddress.id == address_id, ProjectAddress.project_id == project_id)
        )
    ).scalar_one_or_none()
    if address is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    await session.execute(delete(FieldProvenance).where(FieldProvenance.entity_type == "address", FieldProvenance.entity_id == address.id))
    await session.delete(address)
    await session.flush()
    await sync_project_display_geometry_from_addresses(session, project, force=True)
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_address_delete",
        entity_type="address",
        entity_id=address_id,
        diff_json={"project_id": str(project_id)},
        comment=reason,
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def normalize_admin_project_address(session: AsyncSession, project_id: UUID, address_id: UUID) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None
    address = (
        await session.execute(
            select(ProjectAddress).where(ProjectAddress.id == address_id, ProjectAddress.project_id == project_id)
        )
    ).scalar_one_or_none()
    if address is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    await normalize_project_address(session, project=project, address=address, admin_user=admin_user)
    await session.flush()
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_address_normalize",
        entity_type="address",
        entity_id=address.id,
        diff_json={
            "normalized_address_text": address.normalized_address_text,
            "normalized_street": address.normalized_street,
            "normalized_city": address.normalized_city,
            "geocoding_query": address.geocoding_query,
        },
        comment="Normalized address for geocoding workflow",
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def geocode_admin_project_address(session: AsyncSession, project_id: UUID, address_id: UUID) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None
    address = (
        await session.execute(
            select(ProjectAddress).where(ProjectAddress.id == address_id, ProjectAddress.project_id == project_id)
        )
    ).scalar_one_or_none()
    if address is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    await geocode_project_address(session, project=project, address=address, admin_user=admin_user)
    await session.flush()
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_address_geocode",
        entity_type="address",
        entity_id=address.id,
        diff_json={
            "lat": None if address.lat is None else str(address.lat),
            "lng": None if address.lng is None else str(address.lng),
            "location_confidence": address.location_confidence,
            "geocoding_status": address.geocoding_status,
            "geometry_source": address.geometry_source,
        },
        comment=address.geocoding_note,
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def update_project_display_geometry(session: AsyncSession, project_id: UUID, payload: dict) -> dict | None:
    project = await _get_project(session, project_id)
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    report = await _report_for_project(session, project, project.canonical_name)
    before = resolved_display_geometry(project)
    apply_manual_display_geometry(project, payload)
    await session.flush()
    for field_name in [
        "display_geometry_type",
        "display_geometry_source",
        "display_geometry_confidence",
        "display_center_lat",
        "display_center_lng",
        "display_address_summary",
    ]:
        value = getattr(project, field_name)
        if value is not None:
            await _write_provenance(
                session,
                entity_type="project_master",
                entity_id=project.id,
                field_name=field_name,
                normalized_value=str(value),
                source_report_id=report.id,
                value_origin_type="manual",
                confidence_level="medium",
                admin_user_id=admin_user.id,
                source_section="Admin display geometry override",
                review_note=payload.get("change_reason"),
            )
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_display_geometry_update",
        entity_type="project_master",
        entity_id=project.id,
        diff_json={"before": before, "after": resolved_display_geometry(project)},
        comment=payload.get("change_reason"),
    )
    await session.commit()
    return await _build_project_detail(session, project)


async def list_intake_candidates(session: AsyncSession, filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    rows = (
        await session.execute(
            select(StagingProjectCandidate, Company, Report, ProjectMaster)
            .join(Company, Company.id == StagingProjectCandidate.company_id)
            .join(StagingReport, StagingReport.id == StagingProjectCandidate.staging_report_id)
            .join(Report, Report.id == StagingReport.report_id)
            .outerjoin(ProjectMaster, ProjectMaster.id == StagingProjectCandidate.matched_project_id)
            .order_by(StagingProjectCandidate.updated_at.desc(), StagingProjectCandidate.created_at.desc())
        )
    ).all()
    items = [
        {
            "id": candidate.id,
            "candidate_project_name": candidate.candidate_project_name,
            "company": {"id": company.id, "name_he": company.name_he},
            "city": candidate.city,
            "source_report_id": report.id,
            "source_report_name": report.filing_reference,
            "matching_status": candidate.matching_status,
            "confidence_level": candidate.confidence_level,
            "review_status": candidate.review_status,
            "publish_status": candidate.publish_status,
            "matched_project_id": matched_project.id if matched_project else None,
            "matched_project_name": matched_project.canonical_name if matched_project else None,
        }
        for candidate, company, report, matched_project in rows
    ]
    if filters.get("q"):
        term = normalize_text(filters["q"])
        items = [
            item
            for item in items
            if term
            in normalize_text(
                " ".join(
                    [
                        item["candidate_project_name"],
                        item["company"]["name_he"],
                        item["city"] or "",
                        item["source_report_name"] or "",
                        item["matched_project_name"] or "",
                    ]
                )
            )
        ]
    return items


async def list_admin_duplicates(session: AsyncSession) -> list[dict]:
    return await list_duplicate_suggestions(session)


async def merge_admin_projects(session: AsyncSession, winner_project_id: UUID, loser_project_id: UUID, merge_reason: str) -> dict | None:
    winner = await _get_project(session, winner_project_id)
    loser = await _get_project(session, loser_project_id)
    if winner is None or loser is None or winner.id == loser.id:
        return None

    admin_user = await _get_placeholder_admin(session)

    existing_alias_names = {
        alias.alias_name
        for alias in (
            await session.execute(select(ProjectAlias).where(ProjectAlias.project_id == winner.id))
        ).scalars().all()
    }
    loser_aliases = (
        await session.execute(select(ProjectAlias).where(ProjectAlias.project_id == loser.id))
    ).scalars().all()
    if loser.canonical_name not in existing_alias_names:
        session.add(
            ProjectAlias(
                id=uuid4(),
                project_id=winner.id,
                alias_name=loser.canonical_name,
                value_origin_type="manual",
                alias_source_type="system",
                is_active=True,
                notes=f"Created from merged project {loser.id}",
            )
        )
        existing_alias_names.add(loser.canonical_name)

    for alias in loser_aliases:
        if alias.alias_name not in existing_alias_names:
            alias.project_id = winner.id
            existing_alias_names.add(alias.alias_name)

    existing_address_keys = {
        (address.address_text_raw, address.street, address.city)
        for address in (
            await session.execute(select(ProjectAddress).where(ProjectAddress.project_id == winner.id))
        ).scalars().all()
    }
    loser_addresses = (
        await session.execute(select(ProjectAddress).where(ProjectAddress.project_id == loser.id))
    ).scalars().all()
    moved_address_ids: list[str] = []
    for address in loser_addresses:
        key = (address.address_text_raw, address.street, address.city)
        if key not in existing_address_keys:
            address.project_id = winner.id
            moved_address_ids.append(str(address.id))
            existing_address_keys.add(key)

    existing_report_ids = {
        snapshot.report_id
        for snapshot in (
            await session.execute(select(ProjectSnapshot).where(ProjectSnapshot.project_id == winner.id))
        ).scalars().all()
    }
    conflicting_snapshot_ids: list[str] = []
    loser_snapshots = (
        await session.execute(select(ProjectSnapshot).where(ProjectSnapshot.project_id == loser.id))
    ).scalars().all()
    for snapshot in loser_snapshots:
        if snapshot.report_id in existing_report_ids:
            conflicting_snapshot_ids.append(str(snapshot.id))
            continue
        snapshot.project_id = winner.id
        existing_report_ids.add(snapshot.report_id)

    staging_candidates = (
        await session.execute(
            select(StagingProjectCandidate).where(StagingProjectCandidate.matched_project_id == loser.id)
        )
    ).scalars().all()
    for candidate in staging_candidates:
        candidate.matched_project_id = winner.id

    loser.merged_into_project_id = winner.id
    loser.deleted_at = datetime.now(UTC)
    loser.is_publicly_visible = False
    loser.notes_internal = "\n".join(
        value
        for value in [
            loser.notes_internal or "",
            f"Merged into {winner.canonical_name} ({winner.id}) on {datetime.now(UTC).date().isoformat()}: {merge_reason}",
        ]
        if value
    )

    merge_summary = {
        "winner_project_id": str(winner.id),
        "loser_project_id": str(loser.id),
        "moved_address_ids": moved_address_ids,
        "conflicting_snapshot_ids": conflicting_snapshot_ids,
        "relinked_candidate_ids": [str(candidate.id) for candidate in staging_candidates],
    }
    merge_log = ProjectMergeLog(
        id=uuid4(),
        winner_project_id=winner.id,
        loser_project_id=loser.id,
        merged_by=admin_user.id,
        merge_reason=merge_reason,
        summary_json=merge_summary,
        created_at=datetime.now(UTC),
    )
    session.add(merge_log)

    duplicate_rows = (
        await session.execute(
            select(ProjectDuplicateSuggestion).where(
                ProjectDuplicateSuggestion.review_status == "open",
                (
                    (ProjectDuplicateSuggestion.project_id == winner.id)
                    & (ProjectDuplicateSuggestion.duplicate_project_id == loser.id)
                )
                | (
                    (ProjectDuplicateSuggestion.project_id == loser.id)
                    & (ProjectDuplicateSuggestion.duplicate_project_id == winner.id)
                ),
            )
        )
    ).scalars().all()
    for row in duplicate_rows:
        row.review_status = "merged"
        row.reviewed_by = admin_user.id
        row.reviewed_at = datetime.now(UTC)

    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_project_merge",
        entity_type="project_master",
        entity_id=winner.id,
        diff_json=merge_summary,
        comment=merge_reason,
    )
    await session.commit()
    return await _build_project_detail(session, winner)


async def get_admin_coverage_dashboard(session: AsyncSession) -> dict:
    return await get_coverage_dashboard(session)


async def update_company_coverage(session: AsyncSession, company_id: UUID, payload: dict) -> dict | None:
    company = (await session.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if company is None:
        return None

    coverage = (
        await session.execute(select(CompanyCoverageRegistry).where(CompanyCoverageRegistry.company_id == company_id))
    ).scalar_one_or_none()
    if coverage is None:
        coverage = CompanyCoverageRegistry(company_id=company_id)
        session.add(coverage)
        await session.flush()

    admin_user = await _get_placeholder_admin(session)
    diffs: dict[str, dict[str, object | None]] = {}
    for field_name in [
        "is_in_scope",
        "out_of_scope_reason",
        "coverage_priority",
        "latest_report_ingested_id",
        "historical_coverage_status",
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
            comment=payload.get("notes"),
        )
        await session.commit()
    else:
        await session.rollback()
    return await get_coverage_dashboard(session)


async def get_intake_candidate_detail(session: AsyncSession, candidate_id: UUID) -> dict | None:
    from app.services.ingestion import get_candidate_detail

    return await get_candidate_detail(session, candidate_id)
