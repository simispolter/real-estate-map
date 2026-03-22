from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminUser, ProjectAddress, ProjectMaster


CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "\u05ea\u05dc \u05d0\u05d1\u05d9\u05d1": (32.0853, 34.7818),
    "\u05d9\u05e8\u05d5\u05e9\u05dc\u05d9\u05dd": (31.7683, 35.2137),
    "\u05d0\u05e9\u05d3\u05d5\u05d3": (31.8014, 34.6435),
    "\u05d0\u05e9\u05e7\u05dc\u05d5\u05df": (31.6688, 34.5743),
    "\u05d1\u05ea \u05d9\u05dd": (32.0158, 34.7503),
    "\u05d9\u05d4\u05d5\u05d3": (32.0284, 34.8901),
    "\u05db\u05e4\u05e8 \u05e1\u05d1\u05d0": (32.1740, 34.9078),
    "\u05dc\u05d5\u05d3": (31.9510, 34.8880),
    "\u05e0\u05e9\u05e8": (32.7654, 35.0431),
    "\u05e0\u05ea\u05e0\u05d9\u05d4": (32.3215, 34.8532),
    "\u05e7\u05e8\u05d9\u05d9\u05ea \u05d0\u05d5\u05e0\u05d5": (32.0615, 34.8563),
    "\u05e7\u05e8\u05d9\u05d9\u05ea \u05d1\u05d9\u05d0\u05dc\u05d9\u05e7": (32.8276, 35.0855),
    "\u05e8\u05d7\u05d5\u05d1\u05d5\u05ea": (31.8948, 34.8113),
    "\u05e8\u05de\u05ea \u05d2\u05df": (32.0684, 34.8248),
    "\u05d0\u05d5\u05e4\u05e7\u05d9\u05dd": (31.3141, 34.6203),
    "\u05d1\u05e0\u05d9 \u05e2\u05d9\u05d9\u05e9": (31.7830, 34.7542),
}


def _normalize_part(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.replace(",", " ").split())
    return normalized or None


def _decimal(value: float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _point_geojson(lat: float | Decimal, lng: float | Decimal) -> dict[str, Any]:
    return {
        "type": "Point",
        "coordinates": [float(lng), float(lat)],
    }


def build_address_summary(address: ProjectAddress) -> str:
    if address.normalized_display_address:
        return address.normalized_display_address

    parts = [address.normalized_street or address.street, address.city]
    if address.house_number_from is not None:
        if address.house_number_to and address.house_number_to != address.house_number_from:
            parts.insert(1, f"{address.house_number_from}-{address.house_number_to}")
        else:
            parts.insert(1, str(address.house_number_from))
    summary = " ".join(part for part in parts if part)
    return summary or address.normalized_address_text or address.address_text_raw or "Unknown address"


def normalize_address_record(address: ProjectAddress) -> dict[str, str | bool | None]:
    normalized_street = _normalize_part(address.street)
    normalized_city = _normalize_part(address.city)
    address_bits = [normalized_street]
    if address.house_number_from is not None:
        if address.house_number_to and address.house_number_to != address.house_number_from:
            address_bits.append(f"{address.house_number_from}-{address.house_number_to}")
        else:
            address_bits.append(str(address.house_number_from))
    if normalized_city:
        address_bits.append(normalized_city)

    normalized_address_text = " ".join(bit for bit in address_bits if bit)
    if not normalized_address_text:
        normalized_address_text = _normalize_part(address.address_text_raw)

    normalized_display_address = normalized_address_text or " ".join(
        bit for bit in [normalized_street, normalized_city] if bit
    )

    return {
        "normalized_address_text": normalized_address_text,
        "normalized_display_address": normalized_display_address,
        "normalized_street": normalized_street,
        "normalized_city": normalized_city,
        "geocoding_query": normalized_address_text or normalized_city,
        "is_geocoding_ready": bool(normalized_city and (normalized_street or address.address_text_raw)),
    }


def location_quality(location_confidence: str | None) -> str:
    if location_confidence == "exact":
        return "exact"
    if location_confidence == "approximate":
        return "approximate"
    if location_confidence == "city_only":
        return "city-only"
    return "unknown"


def city_centroid_geometry(city: str | None) -> dict[str, Any] | None:
    if not city:
        return None
    centroid = CITY_CENTROIDS.get(city)
    if centroid is None:
        return None
    lat, lng = centroid
    return {
        "geometry_type": "city_centroid",
        "geometry_source": "city_registry",
        "location_confidence": "city_only",
        "geometry_geojson": _point_geojson(lat, lng),
        "center_lat": Decimal(str(lat)),
        "center_lng": Decimal(str(lng)),
        "address_summary": city,
        "city_only": True,
    }


def infer_geocoded_confidence(address: ProjectAddress) -> str:
    if address.street and address.house_number_from is not None:
        return "exact"
    if address.street or address.address_text_raw:
        return "approximate"
    if address.city:
        return "city_only"
    return "unknown"


def serialize_display_geometry(project: ProjectMaster) -> dict[str, Any]:
    geometry = project.display_geometry_geojson
    city_only = project.display_geometry_confidence == "city_only"
    has_coordinates = project.display_center_lat is not None and project.display_center_lng is not None
    is_manual_override = project.display_geometry_source == "manual_override"
    return {
        "geometry_type": project.display_geometry_type,
        "geometry_source": project.display_geometry_source,
        "location_confidence": project.display_geometry_confidence,
        "location_quality": location_quality(project.display_geometry_confidence),
        "geometry_geojson": geometry,
        "center_lat": project.display_center_lat,
        "center_lng": project.display_center_lng,
        "address_summary": project.display_address_summary,
        "note": project.display_geometry_note,
        "city_only": city_only,
        "has_coordinates": has_coordinates,
        "is_manual_override": is_manual_override,
        "is_source_derived": not is_manual_override and project.display_geometry_source in {"reported", "city_registry"},
    }


def resolved_display_geometry(project: ProjectMaster) -> dict[str, Any]:
    if project.display_geometry_type != "unknown" and (
        project.display_geometry_geojson is not None
        or (project.display_center_lat is not None and project.display_center_lng is not None)
    ):
        return serialize_display_geometry(project)

    centroid = city_centroid_geometry(project.city)
    if centroid is not None:
        return {
            "geometry_type": centroid["geometry_type"],
            "geometry_source": centroid["geometry_source"],
            "location_confidence": centroid["location_confidence"],
            "location_quality": location_quality(centroid["location_confidence"]),
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

    return serialize_display_geometry(project)


async def sync_project_display_geometry_from_addresses(
    session: AsyncSession,
    project: ProjectMaster,
    *,
    force: bool = False,
) -> None:
    if not force and project.display_geometry_source == "manual_override":
        return

    addresses = (
        await session.execute(
            select(ProjectAddress)
            .where(ProjectAddress.project_id == project.id)
            .order_by(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc())
        )
    ).scalars().all()

    selected = next((address for address in addresses if address.lat is not None and address.lng is not None), None)
    if selected is not None:
        project.display_geometry_type = "exact_point" if selected.location_confidence == "exact" else "approximate_point"
        project.display_geometry_source = selected.geometry_source or "unknown"
        project.display_geometry_confidence = selected.location_confidence
        project.display_geometry_geojson = _point_geojson(selected.lat, selected.lng)
        project.display_center_lat = _decimal(selected.lat)
        project.display_center_lng = _decimal(selected.lng)
        project.display_address_summary = build_address_summary(selected)
        project.display_geometry_note = selected.geocoding_note
        return

    centroid = city_centroid_geometry(project.city or (addresses[0].city if addresses else None))
    if centroid is not None:
        project.display_geometry_type = centroid["geometry_type"]
        project.display_geometry_source = centroid["geometry_source"]
        project.display_geometry_confidence = centroid["location_confidence"]
        project.display_geometry_geojson = centroid["geometry_geojson"]
        project.display_center_lat = centroid["center_lat"]
        project.display_center_lng = centroid["center_lng"]
        project.display_address_summary = centroid["address_summary"]
        project.display_geometry_note = "Derived from the city centroid registry."
        return

    project.display_geometry_type = "unknown"
    project.display_geometry_source = "unknown"
    project.display_geometry_confidence = "unknown"
    project.display_geometry_geojson = None
    project.display_center_lat = None
    project.display_center_lng = None
    project.display_address_summary = project.city
    project.display_geometry_note = "No spatial geometry is currently available."


def _nominatim_geocode(query: str) -> dict[str, Any] | None:
    if not query:
        return None

    request = Request(
        url=f"https://nominatim.openstreetmap.org/search?q={quote_plus(query)}&format=jsonv2&limit=1&countrycodes=il",
        headers={"User-Agent": "real-estat-map/0.1 spatial-admin"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    if not payload:
        return None
    item = payload[0]
    return {
        "lat": float(item["lat"]),
        "lng": float(item["lon"]),
        "display_name": item.get("display_name"),
        "provider": "nominatim",
    }


async def normalize_project_address(
    session: AsyncSession,
    *,
    project: ProjectMaster,
    address: ProjectAddress,
    admin_user: AdminUser,
) -> None:
    normalized = normalize_address_record(address)
    address.normalized_address_text = normalized["normalized_address_text"]
    address.normalized_display_address = normalized["normalized_display_address"]
    address.normalized_street = normalized["normalized_street"]
    address.normalized_city = normalized["normalized_city"]
    address.geocoding_query = normalized["geocoding_query"]
    address.is_geocoding_ready = bool(normalized["is_geocoding_ready"])
    address.geocoding_status = "normalized"
    address.geocoding_method = "address_text"
    address.geocoding_source_label = "Address normalization"
    address.assigned_by = admin_user.id
    address.assigned_at = datetime.now(UTC)
    if address.location_confidence not in {"exact", "approximate", "city_only", "unknown"}:
        address.location_confidence = "unknown"

    if not address.city and project.city:
        address.city = project.city
        address.normalized_city = _normalize_part(project.city)
        address.geocoding_query = normalize_address_record(address)["geocoding_query"]
        address.is_geocoding_ready = bool(address.geocoding_query)


async def geocode_project_address(
    session: AsyncSession,
    *,
    project: ProjectMaster,
    address: ProjectAddress,
    admin_user: AdminUser,
) -> None:
    await normalize_project_address(session, project=project, address=address, admin_user=admin_user)
    result = _nominatim_geocode(address.geocoding_query or "")
    if result is not None:
        address.lat = _decimal(result["lat"])
        address.lng = _decimal(result["lng"])
        address.location_confidence = infer_geocoded_confidence(address)
        address.geometry_source = "geocoded"
        address.geocoding_status = "geocoded"
        address.geocoding_method = "address_text"
        address.geocoding_provider = result["provider"]
        address.geocoding_source_label = "Nominatim OpenStreetMap"
        address.geocoded_at = datetime.now(UTC)
        address.geocoding_note = result["display_name"]
    else:
        address.geocoding_status = "failed"
        address.geocoding_method = "address_text"
        address.geocoding_provider = "nominatim"
        address.geocoding_source_label = "Nominatim OpenStreetMap"
        address.geocoding_note = "No address-level geocode result returned."

    await sync_project_display_geometry_from_addresses(session, project, force=True)


def apply_manual_display_geometry(project: ProjectMaster, payload: dict[str, Any]) -> None:
    geometry_type = payload.get("geometry_type", "unknown")
    geometry_source = payload.get("geometry_source", "manual_override")
    location_confidence = payload.get("location_confidence", "unknown")
    center_lat = payload.get("center_lat")
    center_lng = payload.get("center_lng")
    geometry_geojson = payload.get("geometry_geojson")
    address_summary = payload.get("address_summary")
    note = payload.get("note")

    project.display_geometry_type = geometry_type
    project.display_geometry_source = geometry_source
    project.display_geometry_confidence = location_confidence
    project.display_center_lat = _decimal(center_lat)
    project.display_center_lng = _decimal(center_lng)
    project.display_address_summary = address_summary
    project.display_geometry_note = note

    if geometry_geojson:
        project.display_geometry_geojson = geometry_geojson
    elif geometry_type in {"exact_point", "approximate_point", "city_centroid"} and center_lat is not None and center_lng is not None:
        project.display_geometry_geojson = _point_geojson(center_lat, center_lng)
    else:
        project.display_geometry_geojson = None
