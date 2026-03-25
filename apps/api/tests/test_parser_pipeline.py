from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import parser_pipeline
from app.services.extraction_profiles import classify_section


def test_segment_sections_creates_page_scoped_sections():
    sections = parser_pipeline._segment_sections(
        [
            "Residential Projects\nYam Towers Ashdod",
            "Management Discussion",
        ]
    )

    assert len(sections) == 2
    assert sections[0].section_name == "Residential Projects"
    assert sections[0].source_page_from == 1


def test_extract_metric_and_status_from_window_text():
    raw_value, normalized_value, origin = parser_pipeline._extract_metric(
        'דירות שנמכרו 120 | מחיר ממוצע למ"ר 31,000 | gross margin 18.5%',
        "sold_units_cumulative",
    )
    status_value, status_origin = parser_pipeline._extract_status("הפרויקט נמצא בשיווק ובבנייה", "project_status")

    assert raw_value == "120"
    assert normalized_value == 120
    assert origin == "reported"
    assert status_value in {"marketing", "construction"}
    assert status_origin == "inferred"


def test_extract_project_labels_from_section_lines():
    labels = parser_pipeline._extract_project_labels(
        """
        Project Givati - Givatayim | 220 units | marketing
        Ben Gurion, Ramla | Phase A | 270 units
        Table of contents
        """
    )

    assert "Givati - Givatayim" in labels


def test_extract_project_labels_suppresses_obvious_noise_rows():
    labels = parser_pipeline._extract_project_labels(
        """
        ליום 31.12.2025
        סה"כ 420
        Project Givati - Givatayim | 220 units | marketing
        """,
        section_kind="construction",
    )

    assert labels == ["Givati - Givatayim"]


def test_extract_project_labels_merges_multiline_project_rows():
    labels = parser_pipeline._extract_project_labels(
        """
        Neo
        240 units | planning permit
        """,
        section_kind="planning",
    )

    assert "Neo" in labels


def test_classify_section_distinguishes_completed_inventory_from_planning():
    classification = classify_section(
        "מלאי דירות גמורות ולא מכורות",
        "דירות גמורות",
        "אוכלסו אך טרם נמכרו במלואן",
    )

    assert classification.section_kind == "completed"
    assert classification.confidence_score > 0


def test_build_candidate_drafts_avoids_total_row_bleed():
    sections = [
        parser_pipeline.ExtractedSection(
            section_name="פרויקטים בביצוע",
            raw_label="טבלת פרויקטים",
            source_page_from=1,
            source_page_to=1,
            text="""
            Project Givati - Givatayim | 220 units | marketing
            סה"כ 220
            Project Savyon - Beit Shemesh | 180 units | construction
            """,
        )
    ]
    persisted_sections = [
        SimpleNamespace(
            section_name="פרויקטים בביצוע",
            section_kind="construction",
            raw_label="טבלת פרויקטים",
            extraction_profile_key="construction_table",
            source_page_from=1,
        )
    ]

    drafts, suppressed_rows, diagnostics = parser_pipeline._build_candidate_drafts(
        sections=sections,
        persisted_sections=persisted_sections,
        candidate_sources=[],
        known_cities=[],
    )

    assert [draft.candidate_name for draft in drafts] == ["Givati - Givatayim", "Savyon - Beit Shemesh"]
    assert any(row.reason == "aggregate_total_row" for row in suppressed_rows)
    assert diagnostics["suppressed_row_total"] >= 1


def test_build_candidate_drafts_handles_new_issuer_without_aliases():
    sections = [
        parser_pipeline.ExtractedSection(
            section_name="עתודות קרקע",
            raw_label="קרקעות למגורים",
            source_page_from=1,
            source_page_to=1,
            text="""
            באר יעקב | 183 יח"ד | planning
            בהתאם לזכויות הבניה הקיימות או העתידיות
            """,
        )
    ]
    persisted_sections = [
        SimpleNamespace(
            section_name="עתודות קרקע",
            section_kind="land_reserve",
            raw_label="קרקעות למגורים",
            extraction_profile_key="land_reserve",
            source_page_from=1,
        )
    ]

    drafts, suppressed_rows, _ = parser_pipeline._build_candidate_drafts(
        sections=sections,
        persisted_sections=persisted_sections,
        candidate_sources=[],
        known_cities=["באר יעקב"],
    )

    assert [draft.candidate_name for draft in drafts] == ["באר יעקב"]
    assert drafts[0].candidate_section_kind == "land_reserve"
    assert drafts[0].confidence_level in {"medium", "high"}
    assert any(row.reason == "prose_fragment" for row in suppressed_rows)


def test_segment_report_chunks_merges_consecutive_same_family_pages():
    chunks = parser_pipeline.segment_report_chunks(
        [
            "9.2 פרויקטים בהקמה\nProject A | 120 units",
            "9.2 פרויקטים בהקמה\nProject B | 90 units",
            "10.1 פרויקטים בתכנון\nProject C | 140 units",
        ]
    )

    assert len(chunks) == 2
    assert chunks[0].section_kind == "construction"
    assert chunks[0].source_page_from == 1
    assert chunks[0].source_page_to == 2
    assert chunks[1].section_kind == "planning"


def test_high_recall_label_extraction_keeps_numeric_tail_project_names():
    label = parser_pipeline._project_label_from_line_high_recall(
        '24% 44,221 185,475 21.4 185,475 135,513 128,240 445,252 573,492 חופשי שוק חדרה סיטי אאורה',
        section_kind="construction",
        known_cities=[],
    )

    assert label == "חדרה סיטי אאורה"
