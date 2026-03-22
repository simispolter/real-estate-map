from collections.abc import AsyncIterator
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.api.v1.endpoints import admin as admin_endpoints
from app.api.v1.endpoints import companies as company_endpoints
from app.api.v1.endpoints import filters as filter_endpoints
from app.api.v1.endpoints import map as map_endpoints
from app.api.v1.endpoints import projects as project_endpoints
from app.db.session import get_db_session
from app.main import app


async def _override_db() -> AsyncIterator[object]:
    yield object()


PROJECT_ID = str(uuid4())
COMPANY_ID = str(uuid4())
ADDRESS_ID = str(uuid4())


def project_detail_payload() -> dict:
    return {
        "identity": {
            "project_id": PROJECT_ID,
            "canonical_name": "Test Project",
            "company": {"id": COMPANY_ID, "name_he": "Test Company"},
        },
        "classification": {
            "project_business_type": "regular_dev",
            "government_program_type": "none",
            "project_urban_renewal_type": "none",
            "project_status": "marketing",
            "permit_status": "pending",
            "classification_confidence": "medium",
            "trust": {
                "project_business_type": {
                    "value_origin_type": "reported",
                    "confidence_level": "high",
                }
            },
        },
        "location": {
            "city": "Tel Aviv",
            "neighborhood": None,
            "district": None,
            "location_confidence": "city_only",
            "location_quality": "city-only",
            "address_summary": "Tel Aviv (city-level)",
            "trust": {
                "city": {
                    "value_origin_type": "reported",
                    "confidence_level": "high",
                }
            },
        },
        "display_geometry": {
            "geometry_type": "city_centroid",
            "geometry_source": "city_registry",
            "location_confidence": "city_only",
            "location_quality": "city-only",
            "geometry_geojson": {"type": "Point", "coordinates": [34.7818, 32.0853]},
            "center_lat": "32.0853",
            "center_lng": "34.7818",
            "address_summary": "Tel Aviv (city-level)",
            "note": "Centroid fallback",
            "city_only": True,
            "has_coordinates": True,
        },
        "latest_snapshot": {
            "snapshot_id": str(uuid4()),
            "snapshot_date": "2025-09-30",
            "project_status": "marketing",
            "permit_status": "pending",
            "total_units": 120,
            "marketed_units": 80,
            "sold_units_cumulative": 60,
            "unsold_units": 20,
            "avg_price_per_sqm_cumulative": "32000.00",
            "gross_profit_total_expected": "125000000.00",
            "gross_margin_expected_pct": "18.50",
            "trust": {
                "permit_status": {
                    "value_origin_type": "inferred",
                    "confidence_level": "medium",
                }
            },
        },
        "derived_metrics": {
            "sell_through_rate": "75.00",
            "known_unsold_units": 20,
            "latest_known_avg_price_per_sqm": "32000.00",
            "known_margin_signal": "moderate",
        },
        "addresses": [
            {
                "id": ADDRESS_ID,
                "address_text_raw": "Main Street 10, Tel Aviv",
                "city": "Tel Aviv",
                "street": "Main Street",
                "house_number_from": 10,
                "house_number_to": 10,
                "lat": "32.1000000",
                "lng": "34.8000000",
                "location_confidence": "approximate",
                "location_quality": "approximate",
                "normalized_address_text": "Main Street 10, Tel Aviv",
                "normalized_city": "Tel Aviv",
                "normalized_street": "Main Street",
                "geometry_source": "reported",
                "geocoding_status": "geocoded",
                "geocoding_provider": "manual",
                "geocoding_note": None,
                "is_primary": True,
                "value_origin_type": "reported",
            }
        ],
        "source_quality": {
            "source_company": "Test Company",
            "source_report_name": "Q3 2025",
            "report_period_end": "2025-09-30",
            "published_at": "2025-11-20",
            "source_url": "https://example.com/report.pdf",
            "source_pages": "14,15",
            "confidence_level": "medium",
            "missing_fields": ["neighborhood"],
            "value_origin_summary": {"reported": 5, "inferred": 1, "unknown": 1},
        },
        "field_provenance": [
            {
                "field_name": "permit_status",
                "raw_value": "pending",
                "normalized_value": "pending",
                "source_page": 14,
                "source_section": "Table",
                "extraction_method": "rule",
                "confidence_score": "80.00",
                "value_origin_type": "inferred",
                "review_status": "approved",
            }
        ],
    }


def test_projects_list_route(monkeypatch):
    async def fake_list_projects(_session, _filters):
        return (
            [
                {
                    "project_id": PROJECT_ID,
                    "canonical_name": "Test Project",
                    "company": {"id": COMPANY_ID, "name_he": "Test Company"},
                    "city": "Tel Aviv",
                    "neighborhood": None,
                    "project_business_type": "regular_dev",
                    "government_program_type": "none",
                    "project_urban_renewal_type": "none",
                    "project_status": "marketing",
                    "permit_status": None,
                    "total_units": 120,
                    "marketed_units": 80,
                    "sold_units_cumulative": 60,
                    "unsold_units": 20,
                    "avg_price_per_sqm_cumulative": "32000.00",
                    "gross_profit_total_expected": None,
                    "gross_margin_expected_pct": None,
                    "latest_snapshot_date": "2025-09-30",
                    "location_confidence": "city_only",
                    "location_quality": "city-only",
                    "display_geometry_type": "city_centroid",
                    "address_summary": "Tel Aviv (city-level)",
                    "sell_through_rate": "75.00",
                }
            ],
            1,
        )

    monkeypatch.setattr(project_endpoints, "list_projects", fake_list_projects)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/projects")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["canonical_name"] == "Test Project"


def test_project_detail_route(monkeypatch):
    async def fake_get_project_detail(_session, _project_id):
        return project_detail_payload()

    monkeypatch.setattr(project_endpoints, "get_project_detail", fake_get_project_detail)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{PROJECT_ID}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["identity"]["canonical_name"] == "Test Project"
    assert payload["source_quality"]["value_origin_summary"]["inferred"] == 1


def test_companies_list_route(monkeypatch):
    async def fake_list_companies(_session, _filters):
        return [
            {
                "id": COMPANY_ID,
                "name_he": "Test Company",
                "ticker": "TST",
                "project_count": 3,
                "city_count": 2,
                "latest_report_period_end": "2025-09-30",
                "latest_published_at": "2025-11-20",
                "known_unsold_units": 20,
                "projects_with_precise_location_count": 1,
            }
        ]

    monkeypatch.setattr(company_endpoints, "list_companies", fake_list_companies)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/companies")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["project_count"] == 3


def test_filters_metadata_route(monkeypatch):
    async def fake_get_filter_metadata(_session):
        return {
            "companies": [{"id": COMPANY_ID, "label": "Test Company"}],
            "cities": ["Tel Aviv"],
            "project_business_types": ["regular_dev"],
            "government_program_types": ["none"],
            "project_urban_renewal_types": ["none"],
            "permit_statuses": ["pending"],
        }

    monkeypatch.setattr(filter_endpoints, "get_filter_metadata", fake_get_filter_metadata)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/filters/metadata")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cities"] == ["Tel Aviv"]


def test_map_projects_route(monkeypatch):
    async def fake_get_map_projects(_session, _filters):
        return {
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [34.8, 32.1]},
                    "properties": {
                        "project_id": PROJECT_ID,
                        "canonical_name": "Test Project",
                        "company_name": "Test Company",
                        "city": "Tel Aviv",
                        "project_business_type": "regular_dev",
                        "project_status": "marketing",
                        "avg_price_per_sqm_cumulative": "32000.00",
                        "unsold_units": 20,
                        "location_confidence": "approximate",
                        "location_quality": "approximate",
                        "geometry_type": "approximate_point",
                        "geometry_source": "reported",
                        "address_summary": "Main Street 10, Tel Aviv",
                        "city_only": False,
                        "has_coordinates": True,
                    },
                }
            ],
            "meta": {
                "available_projects": 1,
                "projects_with_coordinates": 1,
                "location_quality_breakdown": {"approximate": 1},
                "geometry_type_breakdown": {"approximate_point": 1},
                "city_only_projects": 0,
            },
        }

    monkeypatch.setattr(map_endpoints, "get_map_projects", fake_get_map_projects)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/map/projects")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["meta"]["projects_with_coordinates"] == 1


def test_map_layers_route(monkeypatch):
    async def fake_list_public_external_layers(_session):
        return [
            {
                "id": str(uuid4()),
                "layer_name": "Municipal centroids demo layer",
                "source_name": "Government open data demo slice",
                "source_url": "https://info.data.gov.il/datagov/home",
                "geometry_type": "point",
                "update_cadence": "monthly",
                "quality_score": "68.00",
                "visibility": "public",
                "notes": "Demo layer",
                "is_active": True,
                "default_on_map": False,
                "record_count": 5,
            }
        ]

    monkeypatch.setattr(map_endpoints, "list_public_external_layers", fake_list_public_external_layers)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/map/layers")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["layer_name"] == "Municipal centroids demo layer"


def test_admin_layers_route(monkeypatch):
    async def fake_list_admin_external_layers(_session):
        return [
            {
                "id": str(uuid4()),
                "layer_name": "Municipal centroids demo layer",
                "source_name": "Government open data demo slice",
                "source_url": "https://info.data.gov.il/datagov/home",
                "geometry_type": "point",
                "update_cadence": "monthly",
                "quality_score": "68.00",
                "visibility": "public",
                "notes": "Demo layer",
                "is_active": True,
                "default_on_map": False,
                "record_count": 5,
                "relation_count": 0,
                "updated_at": "2026-03-22T10:00:00Z",
            }
        ]

    monkeypatch.setattr(admin_endpoints, "list_admin_external_layers", fake_list_admin_external_layers)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/layers")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["record_count"] == 5


def test_admin_update_flow(monkeypatch):
    seen_payload = {}

    async def fake_update_admin_project(_session, _project_id, payload):
        seen_payload.update(payload)
        project = project_detail_payload()
        project["classification"]["project_business_type"] = payload["project_business_type"]
        return {
            "id": PROJECT_ID,
            "canonical_name": "Test Project",
            "company": {"id": COMPANY_ID, "name_he": "Test Company"},
            "classification": project["classification"],
            "location": project["location"],
            "display_geometry": project["display_geometry"],
            "latest_snapshot": project["latest_snapshot"],
            "addresses": project["addresses"],
            "field_provenance": project["field_provenance"],
            "notes_internal": "Reviewed internally",
            "audit_log": [
                {
                    "id": str(uuid4()),
                    "action": "admin_project_update",
                    "entity_type": "project_master",
                    "entity_id": PROJECT_ID,
                    "diff_json": {"project_business_type": {"before": "regular_dev", "after": payload["project_business_type"]}},
                    "comment": payload.get("change_reason"),
                    "created_at": "2026-03-20T10:00:00Z",
                }
            ],
        }

    monkeypatch.setattr(admin_endpoints, "update_admin_project", fake_update_admin_project)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/admin/projects/{PROJECT_ID}",
            json={
                "project_business_type": "urban_renewal",
                "field_origin_types": {"project_business_type": "reported"},
                "change_reason": "Manual reclassification",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert seen_payload["project_business_type"] == "urban_renewal"
    assert payload["classification"]["project_business_type"] == "urban_renewal"
    assert payload["audit_log"][0]["comment"] == "Manual reclassification"


def test_admin_duplicates_route(monkeypatch):
    async def fake_list_admin_duplicates(_session):
        return [
            {
                "id": str(uuid4()),
                "project_id": PROJECT_ID,
                "project_name": "Test Project A",
                "duplicate_project_id": str(uuid4()),
                "duplicate_project_name": "Test Project B",
                "company_name": "Test Company",
                "city": "Tel Aviv",
                "duplicate_city": "Tel Aviv",
                "match_state": "likely",
                "score": "87.50",
                "reasons_json": {"name_score": 0.91, "city_match": True},
                "review_status": "open",
            }
        ]

    monkeypatch.setattr(admin_endpoints, "list_admin_duplicates", fake_list_admin_duplicates)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/duplicates")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["match_state"] == "likely"
    assert payload["items"][0]["company_name"] == "Test Company"


def test_admin_coverage_route(monkeypatch):
    async def fake_get_admin_coverage_dashboard(_session):
        return {
            "summary": {
                "companies_in_scope": 5,
                "reports_registered": 7,
                "projects_created": 18,
                "snapshots_created": 24,
                "unmatched_candidates": 2,
                "ambiguous_candidates": 1,
                "projects_missing_key_fields": 3,
                "projects_missing_precise_location": 11,
            },
            "companies": [
                {
                    "company_id": COMPANY_ID,
                    "company_name_he": "Test Company",
                    "is_in_scope": True,
                    "out_of_scope_reason": None,
                    "coverage_priority": "high",
                    "latest_report_ingested_id": None,
                    "latest_report_name": "Q3 2025",
                    "historical_coverage_status": "partial",
                    "reports_registered": 2,
                    "projects_created": 3,
                    "snapshots_created": 4,
                    "notes": "Backfill in progress",
                }
            ],
        }

    monkeypatch.setattr(admin_endpoints, "get_admin_coverage_dashboard", fake_get_admin_coverage_dashboard)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/coverage")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["companies_in_scope"] == 5
    assert payload["companies"][0]["coverage_priority"] == "high"


def test_admin_anomalies_route(monkeypatch):
    async def fake_list_admin_anomalies(_session):
        return [
            {
                "id": "sold_gt_marketed:test",
                "anomaly_type": "sold_gt_marketed",
                "severity": "high",
                "project_id": PROJECT_ID,
                "project_name": "Test Project",
                "company_name": "Test Company",
                "snapshot_id": None,
                "report_id": None,
                "source_report_name": None,
                "summary": "Sold units exceed marketed units.",
                "details_json": {"sold_units_cumulative": 10, "marketed_units": 8},
            }
        ]

    monkeypatch.setattr(admin_endpoints, "list_admin_anomalies", fake_list_admin_anomalies)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/anomalies")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["severity"] == "high"


def test_admin_ops_route(monkeypatch):
    async def fake_get_admin_ops_dashboard(_session):
        return {
            "summary": {
                "reports_registered": 7,
                "projects_created": 18,
                "snapshots_created": 24,
                "open_anomalies": 3,
                "parser_failed_runs": 1,
                "ready_to_publish": 2,
            },
            "ingestion_health": {"by_status": {"in_review": 2}},
            "matching_backlog": {"unmatched": 2},
            "publish_backlog": {"ready_to_publish": 2},
            "coverage_completeness": {"companies_in_scope": 5},
            "location_completeness": {"breakdown": {"city_only": 4}},
            "parser_health": {"total_runs": 5, "failed_runs": 1, "recent_runs": []},
            "top_anomalies": [],
        }

    monkeypatch.setattr(admin_endpoints, "get_admin_ops_dashboard", fake_get_admin_ops_dashboard)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/ops")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["parser_failed_runs"] == 1
