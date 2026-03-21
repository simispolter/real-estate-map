from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, AdminAuditLog, AdminUser, FieldProvenance, ProjectAddress, ProjectMaster, ProjectSnapshot, Report
from app.services.catalog import get_project_detail


PLACEHOLDER_ADMIN_EMAIL = "phase3-admin@local"


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


async def list_admin_projects(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(ProjectMaster, ProjectSnapshot, Report, Company)
            .join(ProjectSnapshot, ProjectSnapshot.project_id == ProjectMaster.id)
            .join(Report, Report.id == ProjectSnapshot.report_id)
            .join(Company, Company.id == ProjectMaster.company_id)
            .where(ProjectMaster.deleted_at.is_(None))
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectMaster.canonical_name.asc())
        )
    ).all()

    seen: set[UUID] = set()
    items: list[dict] = []
    for project, snapshot, _report, company in rows:
        if project.id in seen:
            continue
        seen.add(project.id)
        items.append(
            {
                "id": project.id,
                "canonical_name": project.canonical_name,
                "company": {"id": project.company_id, "name_he": company.name_he},
                "city": project.city,
                "project_business_type": project.project_business_type,
                "permit_status": snapshot.permit_status,
                "classification_confidence": project.classification_confidence,
                "location_confidence": project.location_confidence,
                "needs_admin_review": snapshot.needs_admin_review,
                "latest_snapshot_date": snapshot.snapshot_date.isoformat(),
            }
        )
    return items


async def get_admin_project_detail(session: AsyncSession, project_id: UUID) -> dict | None:
    detail = await get_project_detail(session, project_id)
    if detail is None:
        return None

    project = (
        await session.execute(select(ProjectMaster).where(ProjectMaster.id == project_id))
    ).scalar_one()
    audit_log = (
        await session.execute(
            select(AdminAuditLog)
            .where(AdminAuditLog.entity_id == project_id)
            .order_by(AdminAuditLog.created_at.desc())
        )
    ).scalars().all()

    return {
        "id": project.id,
        "canonical_name": project.canonical_name,
        "company": detail["identity"]["company"],
        "classification": detail["classification"],
        "location": detail["location"],
        "latest_snapshot": detail["latest_snapshot"],
        "addresses": detail["addresses"],
        "field_provenance": detail["field_provenance"],
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


async def _latest_snapshot(session: AsyncSession, project_id: UUID) -> ProjectSnapshot:
    return (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one()


async def _latest_report(session: AsyncSession, project_id: UUID) -> Report:
    snapshot = await _latest_snapshot(session, project_id)
    return (await session.execute(select(Report).where(Report.id == snapshot.report_id))).scalar_one()


async def _write_provenance(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    field_name: str,
    normalized_value: str | None,
    source_report_id: UUID,
    value_origin_type: str,
    admin_user_id: UUID,
    source_section: str,
) -> None:
    session.add(
        FieldProvenance(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            raw_value=normalized_value,
            normalized_value=normalized_value,
            source_report_id=source_report_id,
            source_page=None,
            source_section=source_section,
            extraction_method="admin",
            parser_version="admin_review_v1",
            confidence_score=Decimal("100.00") if value_origin_type == "reported" else Decimal("80.00"),
            value_origin_type=value_origin_type,
            review_status="approved",
            reviewed_by=admin_user_id,
            reviewed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
    )


async def update_admin_project(
    session: AsyncSession,
    project_id: UUID,
    payload: dict,
) -> dict | None:
    project = (
        await session.execute(select(ProjectMaster).where(ProjectMaster.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        return None

    snapshot = await _latest_snapshot(session, project_id)
    report = await _latest_report(session, project_id)
    admin_user = await _get_placeholder_admin(session)
    reason = payload.get("change_reason")
    diffs: dict[str, dict[str, str | None]] = {}
    non_nullable_project_fields = {
        "project_business_type",
        "government_program_type",
        "project_urban_renewal_type",
        "location_confidence",
    }

    project_fields = ["project_business_type", "government_program_type", "project_urban_renewal_type", "city", "neighborhood", "location_confidence", "notes_internal"]
    snapshot_fields = ["permit_status"]

    for field_name in project_fields:
        if field_name in payload and not (field_name in non_nullable_project_fields and payload[field_name] is None) and getattr(project, field_name) != payload[field_name]:
            diffs[field_name] = {
                "before": getattr(project, field_name),
                "after": payload[field_name],
            }
            setattr(project, field_name, payload[field_name])
            if field_name != "notes_internal":
                await _write_provenance(
                    session,
                    entity_type="project_master",
                    entity_id=project.id,
                    field_name=field_name,
                    normalized_value=str(payload[field_name]),
                    source_report_id=report.id,
                    value_origin_type=payload.get("field_origin_types", {}).get(field_name, "reported"),
                    admin_user_id=admin_user.id,
                    source_section="Admin review override",
                )

    for field_name in snapshot_fields:
        if field_name in payload and getattr(snapshot, field_name) != payload[field_name]:
            diffs[field_name] = {
                "before": getattr(snapshot, field_name),
                "after": payload[field_name],
            }
            setattr(snapshot, field_name, payload[field_name])
            await _write_provenance(
                session,
                entity_type="snapshot",
                entity_id=snapshot.id,
                field_name=field_name,
                normalized_value=str(payload[field_name]) if payload[field_name] is not None else None,
                source_report_id=report.id,
                value_origin_type=payload.get("field_origin_types", {}).get(field_name, "inferred"),
                admin_user_id=admin_user.id,
                source_section="Admin review override",
            )

    if diffs:
        session.add(
            AdminAuditLog(
                id=uuid4(),
                actor_user_id=admin_user.id,
                action="admin_project_update",
                entity_type="project_master",
                entity_id=project.id,
                diff_json=diffs,
                comment=reason,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()
    else:
        await session.rollback()

    return await get_admin_project_detail(session, project_id)


async def upsert_project_address(
    session: AsyncSession,
    project_id: UUID,
    payload: dict,
    address_id: UUID | None = None,
) -> dict | None:
    project = (
        await session.execute(select(ProjectMaster).where(ProjectMaster.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    report = await _latest_report(session, project_id)
    reason = payload.get("change_reason")

    if address_id is None:
        address = ProjectAddress(
            id=uuid4(),
            project_id=project_id,
            source_type="admin",
            assigned_by=admin_user.id,
            assigned_at=datetime.now(UTC),
        )
        session.add(address)
    else:
        address = (
            await session.execute(
                select(ProjectAddress).where(ProjectAddress.id == address_id, ProjectAddress.project_id == project_id)
            )
        ).scalar_one_or_none()
        if address is None:
            return None

    before = {
        "address_text_raw": address.address_text_raw,
        "street": address.street,
        "house_number_from": address.house_number_from,
        "house_number_to": address.house_number_to,
        "city": address.city,
        "lat": address.lat,
        "lng": address.lng,
        "location_confidence": address.location_confidence,
        "is_primary": address.is_primary,
    }

    for field_name in ["address_text_raw", "street", "house_number_from", "house_number_to", "city", "lat", "lng", "location_confidence", "is_primary"]:
        if field_name in payload:
            setattr(address, field_name, payload[field_name])

    if payload.get("is_primary"):
        other_addresses = (
            await session.execute(
                select(ProjectAddress).where(ProjectAddress.project_id == project_id, ProjectAddress.id != address.id)
            )
        ).scalars().all()
        for other_address in other_addresses:
            other_address.is_primary = False

    await session.flush()
    await _write_provenance(
        session,
        entity_type="address",
        entity_id=address.id,
        field_name="address_record",
        normalized_value=address.city or address.street or address.address_text_raw,
        source_report_id=report.id,
        value_origin_type=payload.get("value_origin_type", "reported"),
        admin_user_id=admin_user.id,
        source_section="Admin address override",
    )
    session.add(
        AdminAuditLog(
            id=uuid4(),
            actor_user_id=admin_user.id,
            action="admin_address_upsert",
            entity_type="project_address",
            entity_id=address.id,
            diff_json={"before": before, "after": {
                "address_text_raw": address.address_text_raw,
                "street": address.street,
                "house_number_from": address.house_number_from,
                "house_number_to": address.house_number_to,
                "city": address.city,
                "lat": address.lat,
                "lng": address.lng,
                "location_confidence": address.location_confidence,
                "is_primary": address.is_primary,
            }},
            comment=reason,
            created_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return await get_admin_project_detail(session, project_id)


async def delete_project_address(
    session: AsyncSession,
    project_id: UUID,
    address_id: UUID,
    reason: str | None,
) -> dict | None:
    address = (
        await session.execute(
            select(ProjectAddress).where(ProjectAddress.id == address_id, ProjectAddress.project_id == project_id)
        )
    ).scalar_one_or_none()
    if address is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    session.add(
        AdminAuditLog(
            id=uuid4(),
            actor_user_id=admin_user.id,
            action="admin_address_delete",
            entity_type="project_address",
            entity_id=address.id,
            diff_json={"before": {"city": address.city, "street": address.street, "is_primary": address.is_primary}, "after": None},
            comment=reason,
            created_at=datetime.now(UTC),
        )
    )
    await session.execute(delete(ProjectAddress).where(ProjectAddress.id == address_id))
    await session.commit()
    return await get_admin_project_detail(session, project_id)
