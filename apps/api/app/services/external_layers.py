from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, AdminUser, ExternalLayer, ExternalLayerProjectRelation, ExternalLayerRecord


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


async def list_public_external_layers(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(
                ExternalLayer,
                func.count(ExternalLayerRecord.id).label("record_count"),
            )
            .outerjoin(
                ExternalLayerRecord,
                (ExternalLayerRecord.layer_id == ExternalLayer.id) & (ExternalLayerRecord.is_active.is_(True)),
            )
            .where(ExternalLayer.is_active.is_(True), ExternalLayer.visibility == "public")
            .group_by(ExternalLayer.id)
            .order_by(ExternalLayer.default_on_map.desc(), ExternalLayer.layer_name.asc())
        )
    ).all()

    return [
        {
            "id": layer.id,
            "layer_name": layer.layer_name,
            "source_name": layer.source_name,
            "source_url": layer.source_url,
            "geometry_type": layer.geometry_type,
            "update_cadence": layer.update_cadence,
            "quality_score": layer.quality_score,
            "visibility": layer.visibility,
            "notes": layer.notes,
            "is_active": layer.is_active,
            "default_on_map": layer.default_on_map,
            "record_count": int(record_count or 0),
        }
        for layer, record_count in rows
    ]


async def get_map_external_layer_features(
    session: AsyncSession,
    layer_ids: list[UUID],
    *,
    city: str | None = None,
) -> dict:
    if not layer_ids:
        return {"features": [], "meta": {"selected_layers": 0, "selected_records": 0, "layer_breakdown": {}}}

    rows = (
        await session.execute(
            select(
                ExternalLayer,
                ExternalLayerRecord,
                func.count(ExternalLayerProjectRelation.id).label("relation_count"),
            )
            .join(ExternalLayerRecord, ExternalLayerRecord.layer_id == ExternalLayer.id)
            .outerjoin(
                ExternalLayerProjectRelation,
                ExternalLayerProjectRelation.external_layer_record_id == ExternalLayerRecord.id,
            )
            .where(
                ExternalLayer.id.in_(layer_ids),
                ExternalLayer.is_active.is_(True),
                ExternalLayer.visibility == "public",
                ExternalLayerRecord.is_active.is_(True),
            )
            .group_by(ExternalLayer.id, ExternalLayerRecord.id)
            .order_by(ExternalLayer.layer_name.asc(), ExternalLayerRecord.label.asc().nullslast())
        )
    ).all()

    if city:
        normalized_city = city.strip().lower()
        rows = [
            row
            for row in rows
            if (row[1].city or "").strip().lower() == normalized_city
        ]

    features = [
        {
            "type": "Feature",
            "geometry": record.geometry_geojson,
            "properties": {
                "layer_id": layer.id,
                "layer_name": layer.layer_name,
                "source_name": layer.source_name,
                "external_record_id": record.external_record_id,
                "label": record.label,
                "city": record.city,
                "effective_date": record.effective_date,
                "quality_score": layer.quality_score,
                "properties_json": record.properties_json or {},
                "relation_count": int(relation_count or 0),
            },
        }
        for layer, record, relation_count in rows
    ]

    return {
        "features": features,
        "meta": {
            "selected_layers": len({feature["properties"]["layer_id"] for feature in features}),
            "selected_records": len(features),
            "layer_breakdown": dict(Counter(feature["properties"]["layer_name"] for feature in features)),
        },
    }


async def list_admin_external_layers(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(
                ExternalLayer,
                func.count(func.distinct(ExternalLayerRecord.id)).label("record_count"),
                func.count(func.distinct(ExternalLayerProjectRelation.id)).label("relation_count"),
            )
            .outerjoin(ExternalLayerRecord, ExternalLayerRecord.layer_id == ExternalLayer.id)
            .outerjoin(
                ExternalLayerProjectRelation,
                ExternalLayerProjectRelation.external_layer_record_id == ExternalLayerRecord.id,
            )
            .group_by(ExternalLayer.id)
            .order_by(ExternalLayer.updated_at.desc(), ExternalLayer.layer_name.asc())
        )
    ).all()

    return [
        {
            "id": layer.id,
            "layer_name": layer.layer_name,
            "source_name": layer.source_name,
            "source_url": layer.source_url,
            "geometry_type": layer.geometry_type,
            "update_cadence": layer.update_cadence,
            "quality_score": layer.quality_score,
            "visibility": layer.visibility,
            "notes": layer.notes,
            "is_active": layer.is_active,
            "default_on_map": layer.default_on_map,
            "record_count": int(record_count or 0),
            "relation_count": int(relation_count or 0),
            "updated_at": layer.updated_at,
        }
        for layer, record_count, relation_count in rows
    ]


async def get_admin_external_layer_detail(session: AsyncSession, layer_id: UUID) -> dict | None:
    layer = (await session.execute(select(ExternalLayer).where(ExternalLayer.id == layer_id))).scalar_one_or_none()
    if layer is None:
        return None

    records = (
        await session.execute(
            select(
                ExternalLayerRecord,
                func.count(ExternalLayerProjectRelation.id).label("relation_count"),
            )
            .outerjoin(
                ExternalLayerProjectRelation,
                ExternalLayerProjectRelation.external_layer_record_id == ExternalLayerRecord.id,
            )
            .where(ExternalLayerRecord.layer_id == layer_id)
            .group_by(ExternalLayerRecord.id)
            .order_by(ExternalLayerRecord.city.asc().nullslast(), ExternalLayerRecord.label.asc().nullslast())
        )
    ).all()

    relation_rows = (
        await session.execute(
            select(ExternalLayerProjectRelation.relation_method)
            .join(ExternalLayerRecord, ExternalLayerRecord.id == ExternalLayerProjectRelation.external_layer_record_id)
            .where(ExternalLayerRecord.layer_id == layer_id)
        )
    ).scalars().all()

    return {
        "id": layer.id,
        "layer_name": layer.layer_name,
        "source_name": layer.source_name,
        "source_url": layer.source_url,
        "geometry_type": layer.geometry_type,
        "update_cadence": layer.update_cadence,
        "quality_score": layer.quality_score,
        "visibility": layer.visibility,
        "notes": layer.notes,
        "is_active": layer.is_active,
        "default_on_map": layer.default_on_map,
        "record_count": len(records),
        "relation_count": sum(int(relation_count or 0) for _, relation_count in records),
        "updated_at": layer.updated_at,
        "records": [
            {
                "id": record.id,
                "external_record_id": record.external_record_id,
                "label": record.label,
                "city": record.city,
                "effective_date": record.effective_date,
                "properties_json": record.properties_json or {},
                "update_metadata": record.update_metadata,
                "relation_count": int(relation_count or 0),
            }
            for record, relation_count in records
        ],
        "relation_method_breakdown": dict(Counter(relation_rows)),
    }


async def create_admin_external_layer(session: AsyncSession, payload: dict) -> dict:
    admin_user = await _get_placeholder_admin(session)
    layer = ExternalLayer(id=uuid4(), **payload)
    session.add(layer)
    await session.flush()
    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_external_layer_create",
        entity_type="external_layer",
        entity_id=layer.id,
        diff_json=payload,
        comment="Created external layer registry record.",
    )
    await session.commit()
    return await get_admin_external_layer_detail(session, layer.id)  # type: ignore[return-value]


async def update_admin_external_layer(session: AsyncSession, layer_id: UUID, payload: dict) -> dict | None:
    layer = (await session.execute(select(ExternalLayer).where(ExternalLayer.id == layer_id))).scalar_one_or_none()
    if layer is None:
        return None

    admin_user = await _get_placeholder_admin(session)
    before = {
        "layer_name": layer.layer_name,
        "source_name": layer.source_name,
        "source_url": layer.source_url,
        "geometry_type": layer.geometry_type,
        "update_cadence": layer.update_cadence,
        "quality_score": layer.quality_score,
        "visibility": layer.visibility,
        "notes": layer.notes,
        "is_active": layer.is_active,
        "default_on_map": layer.default_on_map,
    }
    for field_name, value in payload.items():
        setattr(layer, field_name, value)

    await _record_audit(
        session,
        actor_user_id=admin_user.id,
        action="admin_external_layer_update",
        entity_type="external_layer",
        entity_id=layer.id,
        diff_json={"before": before, "after": payload},
        comment="Updated external layer registry record.",
    )
    await session.commit()
    return await get_admin_external_layer_detail(session, layer.id)
