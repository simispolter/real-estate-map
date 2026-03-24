from collections.abc import AsyncIterator
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.api.v1.endpoints import admin_ingestion as admin_ingestion_endpoints
from app.db.session import get_db_session
from app.main import app


async def _override_db() -> AsyncIterator[object]:
    yield object()


REPORT_ID = str(uuid4())
STAGING_REPORT_ID = str(uuid4())
COMPANY_ID = str(uuid4())
CANDIDATE_ID = str(uuid4())
PROJECT_ID = str(uuid4())
PARSER_RUN_ID = str(uuid4())


def report_detail_payload() -> dict:
    return {
        "id": REPORT_ID,
        "company_id": COMPANY_ID,
        "company_name_he": "Dimri",
        "report_name": "Q3 2025 Report",
        "report_type": "q3",
        "period_type": "quarterly",
        "period_end_date": "2025-09-30",
        "published_at": "2025-11-20",
        "source_url": "https://example.com/report.pdf",
        "source_file_path": None,
        "source_is_official": True,
        "source_label": "Official IR PDF",
        "ingestion_status": "in_review",
        "notes": "Manual review started",
        "candidate_count": 1,
        "created_at": "2026-03-21T10:00:00Z",
        "updated_at": "2026-03-21T10:30:00Z",
        "staging_report_id": STAGING_REPORT_ID,
        "staging_publish_status": "draft",
        "staging_review_status": "pending",
        "staging_notes_internal": "Needs candidate review",
        "candidates": [
            {
                "id": CANDIDATE_ID,
                "candidate_project_name": "Yam Towers",
                "city": "Ashdod",
                "neighborhood": None,
                "matching_status": "unmatched",
                "publish_status": "draft",
                "confidence_level": "medium",
                "review_status": "pending",
                "matched_project_id": None,
                "matched_project_name": None,
                "review_notes": None,
                "diff_summary": None,
            }
        ],
    }


def candidate_detail_payload() -> dict:
    return {
        "id": CANDIDATE_ID,
        "staging_report_id": STAGING_REPORT_ID,
        "report_id": REPORT_ID,
        "company_id": COMPANY_ID,
        "company_name_he": "Dimri",
        "candidate_project_name": "Yam Towers",
        "city": "Ashdod",
        "neighborhood": None,
        "project_business_type": "regular_dev",
        "government_program_type": "none",
        "project_urban_renewal_type": "none",
        "project_status": "marketing",
        "permit_status": "pending",
        "total_units": 120,
        "marketed_units": 90,
        "sold_units_cumulative": 60,
        "unsold_units": 30,
        "avg_price_per_sqm_cumulative": "31000.00",
        "gross_profit_total_expected": "100000000.00",
        "gross_margin_expected_pct": "18.00",
        "location_confidence": "city_only",
        "value_origin_type": "manual",
        "confidence_level": "medium",
        "matching_status": "matched_existing_project",
        "publish_status": "published",
        "review_status": "approved",
        "review_notes": "Reviewed and published",
        "matched_project_id": PROJECT_ID,
        "matched_project_name": "Yam Towers",
        "field_candidates": [
            {
                "id": str(uuid4()),
                "field_name": "total_units",
                "raw_value": "120",
                "normalized_value": "120",
                "source_page": 12,
                "source_section": "Projects table",
                "value_origin_type": "reported",
                "confidence_level": "high",
                "review_status": "approved",
                "review_notes": "Reported directly",
                "created_at": "2026-03-21T10:00:00Z",
                "updated_at": "2026-03-21T10:30:00Z",
            }
        ],
        "address_candidates": [],
        "match_suggestions": [
            {
                "project_id": PROJECT_ID,
                "canonical_name": "Yam Towers",
                "city": "Ashdod",
                "neighborhood": None,
                "similarity_score": 0.98,
                "match_state": "exact",
                "reasons_json": {"name_score": 0.98, "city_match": True},
            }
        ],
        "compare_rows": [
            {
                "field_name": "total_units",
                "canonical_value": "110",
                "staging_value": "120",
                "raw_source_value": "120",
                "source_page": 12,
                "source_section": "Projects table",
                "value_origin_type": "reported",
                "confidence_level": "high",
                "changed": True,
            }
        ],
        "diff_summary": [
            {
                "field_name": "total_units",
                "previous_value": "110",
                "incoming_value": "120",
                "changed": True,
            }
        ],
        "created_at": "2026-03-21T10:00:00Z",
        "updated_at": "2026-03-21T10:30:00Z",
    }


def test_admin_reports_list_route(monkeypatch):
    async def fake_list_admin_reports(_session):
        return [report_detail_payload() | {"candidates": []}]

    monkeypatch.setattr(admin_ingestion_endpoints, "list_admin_reports", fake_list_admin_reports)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/reports")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["report_name"] == "Q3 2025 Report"
    assert payload["items"][0]["source_is_official"] is True


def test_admin_report_create_route(monkeypatch):
    async def fake_create_admin_report(_session, payload):
        created = report_detail_payload()
        created["report_name"] = payload["report_name"]
        return created

    monkeypatch.setattr(admin_ingestion_endpoints, "create_admin_report", fake_create_admin_report)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/admin/reports",
            json={
                "company_id": COMPANY_ID,
                "report_name": "Annual 2025",
                "report_type": "annual",
                "period_type": "annual",
                "period_end_date": "2025-12-31",
                "published_at": "2026-03-01",
                "source_url": "https://example.com/annual.pdf",
                "source_is_official": True,
                "ingestion_status": "draft",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_name"] == "Annual 2025"
    assert payload["staging_report_id"] == STAGING_REPORT_ID


def test_admin_candidate_publish_route(monkeypatch):
    async def fake_publish_candidate(_session, _candidate_id, reviewer_note):
        published = candidate_detail_payload()
        published["review_notes"] = reviewer_note
        return published

    monkeypatch.setattr(admin_ingestion_endpoints, "publish_candidate", fake_publish_candidate)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/admin/candidates/{CANDIDATE_ID}/publish",
            json={"reviewer_note": "Approved after manual compare"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["publish_status"] == "published"
    assert payload["matched_project_id"] == PROJECT_ID
    assert payload["review_notes"] == "Approved after manual compare"


def test_admin_report_extract_route(monkeypatch):
    async def fake_run_report_extraction(_session, _report_id):
        extracted = report_detail_payload()
        extracted["candidate_count"] = 3
        return extracted

    monkeypatch.setattr(admin_ingestion_endpoints, "run_report_extraction", fake_run_report_extraction)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.post(f"/api/v1/admin/reports/{REPORT_ID}/extract")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_count"] == 3


def test_admin_report_parser_runs_route(monkeypatch):
    async def fake_list_report_parser_runs(_session, _report_id):
        return [
            {
                "id": PARSER_RUN_ID,
                "report_id": REPORT_ID,
                "staging_report_id": STAGING_REPORT_ID,
                "status": "succeeded",
                "parser_version": "rule_parser_v1",
                "source_label": "Official PDF",
                "source_reference": "https://example.com/report.pdf",
                "source_checksum": "abc123",
                "sections_found": 7,
                "candidate_count": 2,
                "field_candidate_count": 8,
                "address_candidate_count": 0,
                "warnings": [],
                "errors": [],
                "diagnostics": {"page_count": 12},
                "started_at": "2026-03-22T10:00:00Z",
                "finished_at": "2026-03-22T10:01:00Z",
                "created_at": "2026-03-22T10:00:00Z",
                "updated_at": "2026-03-22T10:01:00Z",
            }
        ]

    monkeypatch.setattr(admin_ingestion_endpoints, "list_report_parser_runs", fake_list_report_parser_runs)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get(f"/api/v1/admin/reports/{REPORT_ID}/parser-runs")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["parser_version"] == "rule_parser_v1"
    assert payload["items"][0]["sections_found"] == 7


def test_admin_report_qa_route(monkeypatch):
    async def fake_get_admin_report_qa(_session, _report_id):
        return {
            "report_id": REPORT_ID,
            "summary": {
                "total_candidates": 4,
                "projects_detected": 4,
                "matched_existing_projects": 2,
                "new_projects_needed": 1,
                "ambiguous_candidates": 1,
                "rejected_or_ignored_candidates": 0,
                "published_candidates": 0,
                "missing_key_field_total": 6,
                "latest_parser_sections_found": 8,
                "latest_parser_candidate_count": 4,
            },
            "lifecycle_stage_distribution": [{"key": "under_construction", "count": 2}],
            "disclosure_level_distribution": [{"key": "operational_full", "count": 2}],
            "family_coverage": [
                {
                    "section_kind": "construction",
                    "section_count": 2,
                    "candidate_count": 2,
                    "matched_existing_count": 2,
                    "new_project_count": 0,
                    "ambiguous_count": 0,
                    "ignored_count": 0,
                }
            ],
            "missing_key_fields": [{"field_name": "gross_profit_total_expected", "missing_count": 2}],
            "latest_parser_run": {
                "id": PARSER_RUN_ID,
                "report_id": REPORT_ID,
                "staging_report_id": STAGING_REPORT_ID,
                "status": "succeeded",
                "parser_version": "rule_parser_v1",
                "source_label": "Official PDF",
                "source_reference": "C:/pilot/report.pdf",
                "source_checksum": "abc123",
                "sections_found": 8,
                "candidate_count": 4,
                "field_candidate_count": 12,
                "address_candidate_count": 0,
                "warnings": [],
                "errors": [],
                "diagnostics": {"section_kind_counts": {"construction": 2}},
                "started_at": "2026-03-22T10:00:00Z",
                "finished_at": "2026-03-22T10:01:00Z",
                "created_at": "2026-03-22T10:00:00Z",
                "updated_at": "2026-03-22T10:01:00Z",
            },
        }

    monkeypatch.setattr(admin_ingestion_endpoints, "get_admin_report_qa", fake_get_admin_report_qa)
    app.dependency_overrides[get_db_session] = _override_db

    with TestClient(app) as client:
        response = client.get(f"/api/v1/admin/reports/{REPORT_ID}/qa")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_candidates"] == 4
    assert payload["family_coverage"][0]["section_kind"] == "construction"
