from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import parser_pipeline


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
