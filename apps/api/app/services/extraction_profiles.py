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
    confidence_score: float = 0.0


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
            "קובננטים",
            "עודפים",
            "non recourse",
            "surplus",
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
            "יחס החלפה",
            "tenant signature",
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
            "זכויות בניה",
            "זכויות בנייה",
            "carrying value",
        ),
    ),
    (
        "completed_inventory",
        (
            "completed inventory",
            "completed",
            "inventory",
            "unsold",
            "מלאי דירות גמורות",
            "דירות גמורות",
            "אוכלס",
            "מאוכלס",
            "לא מכורות",
            "לא מכור",
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
            "עתידי",
            "ייזום",
            "בהליכי תכנון",
        ),
    ),
    (
        "construction_table",
        (
            "construction",
            "under construction",
            "בביצוע",
            "בבנייה",
            "בבניה",
            "בשיווק",
            "בהקמה",
            "שיווק והקמה",
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
    "construction_metrics": {
        "construction.engineering_completion_rate",
        "construction.financial_completion_rate",
        "construction.average_unit_sqm",
        "construction.sold_area_sqm_period",
        "construction.sold_area_sqm_cumulative",
        "construction.signed_area_sqm",
        "construction.unsold_area_sqm",
        "construction.planned_construction_start_date",
        "construction.planned_construction_end_date",
        "construction.planned_marketing_start_date",
        "construction.planned_marketing_end_date",
    },
    "planning_metrics": {
        "planning.planning_status_text",
        "planning.permit_status_text",
        "planning.requested_rights_text",
        "planning.intended_uses",
        "planning.intended_units",
        "planning.estimated_start_date",
        "planning.estimated_completion_date",
        "planning.planned_marketing_start_date",
        "planning.planning_dependencies",
    },
    "material_project_disclosure": {
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
    "sensitivity_scenarios": {
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
    "urban_renewal_pipeline": {
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
    "land_reserve_details": {
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
    "completed_inventory_tail": {
        "completed_inventory.completed_units",
        "completed_inventory.delivered_units",
        "completed_inventory.unsold_completed_units",
        "completed_inventory.inventory_cost_book_value",
        "completed_inventory.available_for_sale_units",
        "completed_inventory.occupancy_status_text",
    },
    "financing_details": {
        "finance.financing_institution",
        "finance.facility_amount",
        "finance.utilization_amount",
        "finance.unused_capacity",
        "finance.financing_terms",
        "finance.covenants_summary",
        "finance.non_recourse_flag",
        "finance.surplus_release_conditions",
        "finance.pledged_or_secured_notes",
        "finance.advances_received",
        "finance.receivables_from_signed_contracts",
    },
}


def _tableish_signal(excerpt: str) -> bool:
    return (
        excerpt.count("|") >= 1
        or excerpt.count("%") >= 2
        or excerpt.count("יח") >= 2
        or excerpt.count("units") >= 2
        or excerpt.count("אלפי ש") >= 1
    )


def classify_section(section_name: str, raw_label: str | None, excerpt: str | None) -> SectionClassification:
    normalized_name = normalize_text(section_name or "")
    normalized_label = normalize_text(raw_label or "")
    normalized_excerpt = normalize_text(excerpt or "")
    haystack = " ".join(part for part in (normalized_name, normalized_label, normalized_excerpt) if part)

    best_profile_key: str | None = None
    best_score = 0.0

    for profile_key, hints in PROFILE_HINTS:
        score = 0.0

        for hint in hints:
            normalized_hint = normalize_text(hint)
            if not normalized_hint:
                continue
            if normalized_hint in normalized_label:
                score += 2.4
            elif normalized_hint in normalized_name:
                score += 1.8
            elif normalized_hint in normalized_excerpt:
                score += 0.7

        if profile_key == "completed_inventory" and ("unsold" in haystack or "לא מכור" in haystack):
            score += 0.6
        if profile_key == "planning_table" and ("permit" in haystack or "תכנון" in haystack):
            score += 0.4
        if profile_key == "construction_table" and (
            "construction" in haystack or "בנייה" in haystack or "בניה" in haystack
        ):
            score += 0.4
        if profile_key == "land_reserve" and ("קרקע" in haystack or "land" in haystack):
            score += 0.4
        if profile_key == "material_project_detail" and (
            "covenant" in haystack or "קובננט" in haystack or "עודפים" in haystack
        ):
            score += 0.6

        if score > best_score:
            best_profile_key = profile_key
            best_score = score

    if best_profile_key and best_score >= 1.4 and (bool(raw_label) or _tableish_signal(normalized_excerpt) or best_score >= 2.2):
        section_kind, disclosure_level, lifecycle_stage, materiality_flag = SECTION_PROFILE_DEFAULTS[best_profile_key]
        confidence = min(round(best_score / 4.5, 4), 1.0)
        return SectionClassification(
            section_kind=section_kind,
            extraction_profile_key=best_profile_key,
            disclosure_level=disclosure_level,
            lifecycle_stage=lifecycle_stage,
            materiality_flag=materiality_flag,
            confidence_score=confidence,
        )

    return SectionClassification(
        section_kind="summary_only",
        extraction_profile_key="summary_table",
        disclosure_level="minimal_reference",
        lifecycle_stage=None,
        materiality_flag=False,
        confidence_score=0.0,
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


def infer_data_families(
    *,
    lifecycle_stage: str | None,
    disclosure_level: str | None,
    section_kind: str | None,
    project_business_type: str | None,
    metric_presence: dict[str, bool] | None = None,
    extension_family_keys: set[str] | None = None,
) -> list[str]:
    metric_presence = metric_presence or {}
    extension_family_keys = extension_family_keys or set()
    families: list[str] = []

    def add(value: str) -> None:
        if value not in families:
            families.append(value)

    if (
        lifecycle_stage == "under_construction"
        or section_kind == "construction"
        or metric_presence.get("has_construction_fields")
        or metric_presence.get("has_sales_metrics")
    ):
        add("construction_metrics")

    if (
        lifecycle_stage == "planning_advanced"
        or section_kind == "planning"
        or metric_presence.get("has_planning_fields")
    ):
        add("planning_metrics")

    if (
        lifecycle_stage in {"completed_unsold_tail", "completed_delivered"}
        or section_kind == "completed"
        or metric_presence.get("has_completed_inventory_fields")
    ):
        add("completed_inventory_tail")

    if (
        lifecycle_stage == "urban_renewal_pipeline"
        or section_kind == "urban_renewal"
        or project_business_type == "urban_renewal"
        or "urban_renewal_pipeline" in extension_family_keys
    ):
        add("urban_renewal_pipeline")

    if (
        lifecycle_stage == "land_reserve"
        or section_kind == "land_reserve"
        or "land_reserve_details" in extension_family_keys
    ):
        add("land_reserve_details")

    if (
        disclosure_level == "material_very_high"
        or section_kind == "material_project"
        or "material_project_disclosure" in extension_family_keys
    ):
        add("material_project_disclosure")

    if "sensitivity_scenarios" in extension_family_keys or metric_presence.get("has_sensitivity_fields"):
        add("sensitivity_scenarios")

    if (
        "financing_details" in extension_family_keys
        or metric_presence.get("has_financing_fields")
        or disclosure_level in {"material_very_high", "operational_full"}
    ):
        add("financing_details")

    return families
