from __future__ import annotations

from dataclasses import dataclass

from app.services.identity_ops import normalize_text


@dataclass(frozen=True, slots=True)
class SectionClassification:
    section_kind: str
    extraction_profile_key: str
    disclosure_level: str
    lifecycle_stage: str | None
    materiality_flag: bool


PROFILE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "material_project_detail",
        (
            "material project",
            "material projects",
            "פרויקט מהותי",
            "פרויקטים מהותיים",
            "אשראי",
            "ליווי פיננסי",
        ),
    ),
    (
        "urban_renewal_pipeline",
        (
            "urban renewal",
            "renewal pipeline",
            "פינוי בינוי",
            "התחדשות עירונית",
            "חתימות דיירים",
        ),
    ),
    (
        "land_reserve",
        (
            "land reserve",
            "land bank",
            "קרקעות",
            "עתודות קרקע",
            "מלאי קרקע",
        ),
    ),
    (
        "completed_inventory",
        (
            "completed",
            "inventory",
            "unsold",
            "completed inventory",
            "מלאי דירות גמורות",
            "דירות גמורות",
        ),
    ),
    (
        "planning_table",
        (
            "planning",
            "permit",
            "pipeline",
            "תכנון",
            "קידום תכנון",
            "היתר",
        ),
    ),
    (
        "construction_table",
        (
            "construction",
            "under construction",
            "בביצוע",
            "בבניה",
            "שיווק",
        ),
    ),
)


SECTION_PROFILE_DEFAULTS: dict[str, tuple[str, str, str | None, bool]] = {
    "construction_table": ("construction", "operational_full", "under_construction", False),
    "planning_table": ("planning", "pipeline_signature", "planning_advanced", False),
    "completed_inventory": ("completed", "inventory_tail", "completed_unsold_tail", False),
    "land_reserve": ("land_reserve", "land_reserve", "land_reserve", False),
    "urban_renewal_pipeline": ("urban_renewal", "pipeline_signature", "urban_renewal_pipeline", False),
    "material_project_detail": ("material_project", "material_very_high", None, True),
}


FAMILY_FIELD_GROUPS: dict[str, set[str]] = {
    "material_disclosure": {
        "material.financing_institution",
        "material.facility_amount",
        "material.utilization_amount",
        "material.unused_capacity",
        "material.financing_terms",
        "material.covenants_summary",
        "material.non_recourse_flag",
        "material.surplus_release_conditions",
        "material.expected_economic_profit",
        "material.accounting_to_economic_bridge",
        "material.pledged_or_secured_notes",
        "material.special_project_notes",
    },
    "sensitivity_scenario": {
        "sensitivity.sales_price_plus_5_effect",
        "sensitivity.sales_price_plus_10_effect",
        "sensitivity.sales_price_minus_5_effect",
        "sensitivity.sales_price_minus_10_effect",
        "sensitivity.construction_cost_plus_5_effect",
        "sensitivity.construction_cost_plus_10_effect",
        "sensitivity.construction_cost_minus_5_effect",
        "sensitivity.construction_cost_minus_10_effect",
        "sensitivity.base_gross_profit_not_yet_recognized",
    },
    "urban_renewal_detail": {
        "urban_renewal.existing_units",
        "urban_renewal.future_units_total",
        "urban_renewal.future_units_marketed_by_company",
        "urban_renewal.future_units_for_existing_tenants",
        "urban_renewal.tenant_signature_rate",
        "urban_renewal.signature_timeline",
        "urban_renewal.average_exchange_ratio_signed",
        "urban_renewal.average_exchange_ratio_unsigned",
        "urban_renewal.tenant_relocation_or_demolition_cost",
        "urban_renewal.execution_dependencies",
        "urban_renewal.planning_status_text",
        "urban_renewal.accounting_treatment_summary",
    },
    "land_reserve_detail": {
        "land_reserve.land_area_sqm",
        "land_reserve.historical_cost",
        "land_reserve.financing_cost",
        "land_reserve.planning_cost",
        "land_reserve.carrying_value",
        "land_reserve.current_planning_status",
        "land_reserve.requested_planning_status",
        "land_reserve.intended_units",
        "land_reserve.intended_uses",
    },
}


def classify_section(section_name: str, raw_label: str | None, excerpt: str | None) -> SectionClassification:
    haystack = normalize_text(" ".join(part for part in [section_name, raw_label or "", excerpt or ""] if part))
    for profile_key, hints in PROFILE_HINTS:
        if any(normalize_text(hint) in haystack for hint in hints):
            section_kind, disclosure_level, lifecycle_stage, materiality_flag = SECTION_PROFILE_DEFAULTS[profile_key]
            return SectionClassification(
                section_kind=section_kind,
                extraction_profile_key=profile_key,
                disclosure_level=disclosure_level,
                lifecycle_stage=lifecycle_stage,
                materiality_flag=materiality_flag,
            )

    return SectionClassification(
        section_kind="summary_only",
        extraction_profile_key="summary_table",
        disclosure_level="minimal_reference",
        lifecycle_stage=None,
        materiality_flag=False,
    )


def infer_candidate_lifecycle_stage(
    *,
    section_kind: str | None,
    project_status: str | None,
    project_business_type: str | None,
    permit_status: str | None,
) -> str | None:
    if section_kind == "land_reserve":
        return "land_reserve"
    if section_kind == "urban_renewal" or project_business_type == "urban_renewal":
        return "urban_renewal_pipeline"
    if section_kind == "completed" or project_status == "completed":
        return "completed_unsold_tail"
    if section_kind == "construction" or project_status in {"construction", "marketing"}:
        return "under_construction"
    if section_kind == "planning" or project_status in {"planning", "permit"} or permit_status in {"pending", "granted", "partial"}:
        return "planning_advanced"
    return None


def infer_candidate_disclosure_level(
    *,
    section_kind: str | None,
    extraction_profile_key: str | None,
    total_units: int | None,
    marketed_units: int | None,
    sold_units_cumulative: int | None,
    gross_margin_expected_pct: object | None,
) -> str | None:
    if extraction_profile_key in SECTION_PROFILE_DEFAULTS:
        return SECTION_PROFILE_DEFAULTS[extraction_profile_key][1]
    if section_kind == "material_project":
        return "material_very_high"
    if section_kind == "land_reserve":
        return "land_reserve"
    if section_kind == "urban_renewal":
        return "pipeline_signature"
    if any(value is not None for value in (gross_margin_expected_pct, marketed_units, sold_units_cumulative)):
        return "operational_full"
    if total_units is not None:
        return "minimal_reference"
    return None
