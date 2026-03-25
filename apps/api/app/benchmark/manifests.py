from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class ExpectedProjectManifest:
    canonical_name: str
    aliases: tuple[str, ...]
    family: str
    lifecycle_stage: str | None
    required_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportBenchmarkManifest:
    report_key: str
    source_file_path: str
    company_name_he: str
    company_name_en: str | None
    ticker: str | None
    report_name: str
    period_end_date: date
    published_at: date | None
    notes: str
    expected_projects: tuple[ExpectedProjectManifest, ...]
    expected_family_counts: dict[str, int]


COMMON_REQUIRED_FIELDS = (
    "canonical_name",
    "candidate_lifecycle_stage",
    "candidate_disclosure_level",
    "source_page",
    "source_section",
    "extraction_profile_key",
)

CONSTRUCTION_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "project_status", "total_units")
PLANNING_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "project_status")
LAND_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "candidate_lifecycle_stage")
MATERIAL_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "candidate_disclosure_level")
COMPLETED_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "project_status", "unsold_units")
URBAN_RENEWAL_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "candidate_lifecycle_stage")


BENCHMARK_MANIFESTS: tuple[ReportBenchmarkManifest, ...] = (
    ReportBenchmarkManifest(
        report_key="aura_2025_annual",
        source_file_path=r"C:\Users\simis\Downloads\P1729852-00.pdf",
        company_name_he="אאורה",
        company_name_en="Aura Investments Ltd",
        ticker="AURA",
        report_name="דוח תקופתי לשנת 2025",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        notes="Analyst-curated benchmark based on the annual-report deep-disclosure project tables only.",
        expected_projects=(
            ExpectedProjectManifest(
                canonical_name="אמפייר רמת גן - מגדל התמרים מגדים",
                aliases=("אמפייר רמת גן", "מגדל התמרים מגדים"),
                family="construction",
                lifecycle_stage="under_construction",
                required_fields=CONSTRUCTION_REQUIRED_FIELDS,
            ),
            ExpectedProjectManifest(
                canonical_name="אאורה פיבקו - בת ים",
                aliases=("אאורה פיבקו", "בת ים"),
                family="construction",
                lifecycle_stage="under_construction",
                required_fields=CONSTRUCTION_REQUIRED_FIELDS,
            ),
            ExpectedProjectManifest(
                canonical_name="גבעתיים אימאג'ין",
                aliases=("גבעתיים אימאגין", "גבעתיים Imagine"),
                family="planning",
                lifecycle_stage="planning_advanced",
                required_fields=PLANNING_REQUIRED_FIELDS,
            ),
            ExpectedProjectManifest(
                canonical_name="מתחם הטייסים - נס ציונה / ההסתדרות",
                aliases=("מתחם הטייסים", "נס ציונה ההסתדרות"),
                family="planning",
                lifecycle_stage="planning_advanced",
                required_fields=PLANNING_REQUIRED_FIELDS,
            ),
        ),
        expected_family_counts={
            "construction": 2,
            "planning": 2,
            "completed_unsold_tail": 0,
            "land_reserve": 0,
            "urban_renewal_pipeline": 0,
            "material_project": 0,
        },
    ),
    ReportBenchmarkManifest(
        report_key="megido_2025_annual",
        source_file_path=r"C:\Users\simis\Downloads\1729842.pdf",
        company_name_he='מגידו י.ק. בע"מ',
        company_name_en="Megido Y.K. Ltd",
        ticker=None,
        report_name="דוח תקופתי לשנת 2025",
        period_end_date=date(2025, 12, 31),
        published_at=date(2026, 3, 22),
        notes="Analyst-curated benchmark from annual-report project, land, and material-financing tables.",
        expected_projects=(
            ExpectedProjectManifest("ערד", ("ערד",), "land_reserve", "land_reserve", LAND_REQUIRED_FIELDS),
            ExpectedProjectManifest("ביטווין", ("ביטווין",), "material_project", None, MATERIAL_REQUIRED_FIELDS),
            ExpectedProjectManifest("עפולה", ("עפולה",), "material_project", None, MATERIAL_REQUIRED_FIELDS),
            ExpectedProjectManifest(
                "ג'סר א-זרקא",
                ("ג'סר א-זרקא - 154 יחידות דיור", "ג'סר א זרקא"),
                "planning",
                "planning_advanced",
                PLANNING_REQUIRED_FIELDS,
            ),
            ExpectedProjectManifest("חיפה", ("חיפה - 406 יחידות דיור", "חיפה"), "land_reserve", "land_reserve", LAND_REQUIRED_FIELDS),
            ExpectedProjectManifest("באר יעקב", ("באר יעקב - 183 יחידות דיור", "באר יעקב"), "land_reserve", "land_reserve", LAND_REQUIRED_FIELDS),
            ExpectedProjectManifest("כפר סבא", ("כפר סבא - 146 יחידות דיור", "כפר סבא"), "land_reserve", "land_reserve", LAND_REQUIRED_FIELDS),
            ExpectedProjectManifest("בית דגן", ("בית דגן - 201 יחידות דיור", "בית דגן"), "land_reserve", "land_reserve", LAND_REQUIRED_FIELDS),
        ),
        expected_family_counts={
            "construction": 0,
            "planning": 1,
            "completed_unsold_tail": 0,
            "land_reserve": 5,
            "urban_renewal_pipeline": 0,
            "material_project": 2,
        },
    ),
    ReportBenchmarkManifest(
        report_key="rotem_shani_2025_annual",
        source_file_path=r"C:\Users\simis\Downloads\1729055.pdf",
        company_name_he='רותם שני יזמות והשקעות בע"מ',
        company_name_en="Rotem Shani Entrepreneurship and Investments Ltd",
        ticker=None,
        report_name="דוח תקופתי לשנת 2025",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        notes="Analyst-curated benchmark focused on the named construction / future-project inventory rows.",
        expected_projects=(
            ExpectedProjectManifest("שדה בוקר 9-5, גבעתיים", ("שדה בוקר 9-5", "גבעתיים"), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
            ExpectedProjectManifest("מתחם הסביון, בית שמש", ("מתחם הסביון בית שמש", "הסביון בית שמש"), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
            ExpectedProjectManifest("הגדוד העברי 14-12, רעננה", ("הגדוד העברי14-12, רעננה", "הגדוד העברי רעננה"), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
        ),
        expected_family_counts={
            "construction": 3,
            "planning": 0,
            "completed_unsold_tail": 0,
            "land_reserve": 0,
            "urban_renewal_pipeline": 0,
            "material_project": 0,
        },
    ),
    ReportBenchmarkManifest(
        report_key="amram_avraham_2024_annual",
        source_file_path=r"C:\Users\simis\Downloads\1653859.pdf",
        company_name_he="עמרם אברהם",
        company_name_en="Amram Avraham",
        ticker=None,
        report_name="דוח תקופתי לשנת 2024",
        period_end_date=date(2024, 12, 31),
        published_at=None,
        notes="Analyst-curated benchmark emphasizing the named flagship and urban-renewal project rows that remain legible in the annual tables.",
        expected_projects=(
            ExpectedProjectManifest("Neo", ("Neo",), "planning", "planning_advanced", PLANNING_REQUIRED_FIELDS),
            ExpectedProjectManifest("ALFA", ("ALFA",), "urban_renewal_pipeline", "urban_renewal_pipeline", URBAN_RENEWAL_REQUIRED_FIELDS),
            ExpectedProjectManifest("אורות", ("אורות",), "urban_renewal_pipeline", "urban_renewal_pipeline", URBAN_RENEWAL_REQUIRED_FIELDS),
            ExpectedProjectManifest("AQUA PORT", ("AQUA PORT", "AQUA PORT, רובע השדה, אילת"), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
            ExpectedProjectManifest("AQUA PARK", ("AQUA PARK", "AQUA PARK, שכונת לכיש"), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
            ExpectedProjectManifest("THE ESTHER", ("THE ESTHER", "קולנוע אסתר, נתניה"), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
        ),
        expected_family_counts={
            "construction": 3,
            "planning": 1,
            "completed_unsold_tail": 0,
            "land_reserve": 0,
            "urban_renewal_pipeline": 2,
            "material_project": 0,
        },
    ),
    ReportBenchmarkManifest(
        report_key="azorim_2024_annual",
        source_file_path=r"C:\Users\simis\Downloads\1652753.pdf",
        company_name_he='אזורים חברה להשקעות בפתוח ובבנין בע"מ',
        company_name_en="Azorim Investments Development and Construction Ltd",
        ticker="AZRM",
        report_name="דוח תקופתי לשנת 2024",
        period_end_date=date(2024, 12, 31),
        published_at=None,
        notes="Analyst-curated benchmark built from the named residential / rental / urban-renewal rows that are explicit enough for project-level review.",
        expected_projects=(
            ExpectedProjectManifest('צומת פת"', ('צומת פת"', "צומת פת"), "planning", "planning_advanced", PLANNING_REQUIRED_FIELDS),
            ExpectedProjectManifest('נופי בן שמן"', ('נופי בן שמן"', "נופי בן שמן"), "planning", "planning_advanced", PLANNING_REQUIRED_FIELDS),
            ExpectedProjectManifest("הרצליה הילס", ("הרצליה הילס",), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
            ExpectedProjectManifest("Hudson 44", ("Hudson 44", "Hudson 44 בעיר יונקרס"), "completed_unsold_tail", "completed_unsold_tail", COMPLETED_REQUIRED_FIELDS),
            ExpectedProjectManifest("מעונות הסטודנטים בבת ים", ("מעונות הסטודנטים בבת ים",), "construction", "under_construction", CONSTRUCTION_REQUIRED_FIELDS),
        ),
        expected_family_counts={
            "construction": 2,
            "planning": 2,
            "completed_unsold_tail": 1,
            "land_reserve": 0,
            "urban_renewal_pipeline": 0,
            "material_project": 0,
        },
    ),
)
