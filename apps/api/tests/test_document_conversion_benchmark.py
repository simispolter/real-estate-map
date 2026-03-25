from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.benchmark.document_conversion import (  # noqa: E402
    CandidateBenchmarkRecord,
    _backend_score,
    _evaluate_manifest,
    _match_candidate_to_expected,
)
from app.benchmark.manifests import BENCHMARK_MANIFESTS  # noqa: E402


def test_match_candidate_to_expected_uses_aliases():
    manifest = BENCHMARK_MANIFESTS[0]
    matched, score, all_matches = _match_candidate_to_expected("אאורה פיבקו – בת ים", manifest.expected_projects)

    assert matched is not None
    assert matched.canonical_name == "אאורה פיבקו - בת ים"
    assert score >= 0.72
    assert matched.canonical_name in all_matches


def test_evaluate_manifest_counts_recall_and_unexpected_candidates():
    manifest = BENCHMARK_MANIFESTS[2]
    candidates = [
        CandidateBenchmarkRecord(
            id=uuid4(),
            candidate_name="שדה בוקר9-5, גבעתיים",
            family="construction",
            lifecycle_stage="under_construction",
            disclosure_level="operational_full",
            extraction_profile_key="construction_table",
            source_table_name="מלאי בניינים בהקמה",
            source_row_label="שדה בוקר9-5, גבעתיים",
            project_status="construction",
            permit_status=None,
            total_units=120,
            unsold_units=None,
            field_presence={
                "canonical_name",
                "candidate_lifecycle_stage",
                "candidate_disclosure_level",
                "source_page",
                "source_section",
                "extraction_profile_key",
                "project_status",
                "total_units",
            },
        ),
        CandidateBenchmarkRecord(
            id=uuid4(),
            candidate_name="מועמד לא צפוי",
            family="planning",
            lifecycle_stage="planning_advanced",
            disclosure_level="minimal_reference",
            extraction_profile_key="planning_table",
            source_table_name="פרויקט עתידי",
            source_row_label="מועמד לא צפוי",
            project_status=None,
            permit_status=None,
            total_units=None,
            unsold_units=None,
            field_presence={"canonical_name"},
        ),
    ]

    result = _evaluate_manifest(
        manifest,
        "pypdf",
        candidates,
        {"conversion_backend_diagnostics": {"elapsed_ms": 10}, "conversion_table_count": 1},
    )

    assert result["candidate_count"] == 2
    assert result["matched_expected_count"] == 1
    assert result["project_recall"] == round(1 / 3, 4)
    assert "מועמד לא צפוי" in result["unexpected_candidates"]
    assert result["score"] == _backend_score(result)
