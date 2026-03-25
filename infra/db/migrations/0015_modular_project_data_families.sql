DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'provenance_entity_type_enum') THEN
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'construction_metrics';
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'planning_detail';
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'completed_inventory_detail';
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'financing_detail';
    END IF;
END
$$;

ALTER TABLE project_snapshots
    ADD COLUMN IF NOT EXISTS detected_data_families JSONB;

ALTER TABLE staging_project_candidates
    ADD COLUMN IF NOT EXISTS detected_data_families JSONB;

CREATE TABLE IF NOT EXISTS project_construction_metrics (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    engineering_completion_rate NUMERIC(5, 2),
    financial_completion_rate NUMERIC(5, 2),
    average_unit_sqm NUMERIC(14, 2),
    sold_area_sqm_period NUMERIC(14, 2),
    sold_area_sqm_cumulative NUMERIC(14, 2),
    signed_area_sqm NUMERIC(14, 2),
    unsold_area_sqm NUMERIC(14, 2),
    planned_construction_start_date DATE,
    planned_construction_end_date DATE,
    planned_marketing_start_date DATE,
    planned_marketing_end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_planning_details (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    planning_status_text TEXT,
    permit_status_text TEXT,
    requested_rights_text TEXT,
    intended_uses TEXT,
    intended_units INTEGER,
    estimated_start_date DATE,
    estimated_completion_date DATE,
    planned_marketing_start_date DATE,
    planning_dependencies TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_completed_inventory_details (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    completed_units INTEGER,
    delivered_units INTEGER,
    unsold_completed_units INTEGER,
    inventory_cost_book_value NUMERIC(16, 2),
    available_for_sale_units INTEGER,
    occupancy_status_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_financing_details (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    financing_institution TEXT,
    facility_amount NUMERIC(16, 2),
    utilization_amount NUMERIC(16, 2),
    unused_capacity NUMERIC(16, 2),
    financing_terms TEXT,
    covenants_summary TEXT,
    non_recourse_flag BOOLEAN,
    surplus_release_conditions TEXT,
    pledged_or_secured_notes TEXT,
    advances_received NUMERIC(16, 2),
    receivables_from_signed_contracts NUMERIC(16, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_construction_metrics_project_snapshot
    ON project_construction_metrics (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_project_planning_details_project_snapshot
    ON project_planning_details (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_project_completed_inventory_details_project_snapshot
    ON project_completed_inventory_details (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_project_financing_details_project_snapshot
    ON project_financing_details (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_detected_data_families
    ON project_snapshots USING GIN (detected_data_families);

CREATE INDEX IF NOT EXISTS idx_staging_candidates_detected_data_families
    ON staging_project_candidates USING GIN (detected_data_families);

UPDATE project_snapshots ps
SET detected_data_families = to_jsonb(ARRAY_REMOVE(ARRAY[
        CASE
            WHEN ps.lifecycle_stage = 'under_construction'
              OR ps.engineering_completion_rate IS NOT NULL
              OR ps.financial_completion_rate IS NOT NULL
              OR ps.average_unit_sqm IS NOT NULL
              OR ps.sold_area_sqm_period IS NOT NULL
              OR ps.sold_area_sqm_cumulative IS NOT NULL
              OR ps.signed_area_sqm IS NOT NULL
              OR ps.unsold_area_sqm IS NOT NULL
              OR ps.planned_construction_start_date IS NOT NULL
              OR ps.planned_construction_end_date IS NOT NULL
            THEN 'construction_metrics'
        END,
        CASE
            WHEN ps.lifecycle_stage = 'planning_advanced'
              OR ps.planning_status IS NOT NULL
              OR ps.estimated_start_date IS NOT NULL
              OR ps.estimated_completion_date IS NOT NULL
            THEN 'planning_metrics'
        END,
        CASE
            WHEN ps.lifecycle_stage IN ('completed_unsold_tail', 'completed_delivered')
              OR ps.project_status = 'completed'
            THEN 'completed_inventory_tail'
        END,
        CASE
            WHEN ps.lifecycle_stage = 'urban_renewal_pipeline'
              OR EXISTS (
                  SELECT 1
                  FROM project_urban_renewal_details pur
                  WHERE pur.snapshot_id = ps.id
              )
            THEN 'urban_renewal_pipeline'
        END,
        CASE
            WHEN ps.lifecycle_stage = 'land_reserve'
              OR EXISTS (
                  SELECT 1
                  FROM project_land_reserve_details plr
                  WHERE plr.snapshot_id = ps.id
              )
            THEN 'land_reserve_details'
        END,
        CASE
            WHEN ps.disclosure_level = 'material_very_high'
              OR EXISTS (
                  SELECT 1
                  FROM project_material_disclosures pmd
                  WHERE pmd.snapshot_id = ps.id
              )
            THEN 'material_project_disclosure'
        END,
        CASE
            WHEN ps.advances_received IS NOT NULL
              OR ps.receivables_from_signed_contracts IS NOT NULL
              OR ps.finance_cost_capitalized IS NOT NULL
              OR EXISTS (
                  SELECT 1
                  FROM project_financing_details pfd
                  WHERE pfd.snapshot_id = ps.id
              )
            THEN 'financing_details'
        END,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM project_sensitivity_scenarios pss
                WHERE pss.snapshot_id = ps.id
            )
            THEN 'sensitivity_scenarios'
        END
    ], NULL))
WHERE ps.detected_data_families IS NULL;

UPDATE staging_project_candidates spc
SET detected_data_families = to_jsonb(ARRAY_REMOVE(ARRAY[
        CASE
            WHEN spc.candidate_section_kind = 'construction'
              OR spc.candidate_lifecycle_stage = 'under_construction'
              OR spc.marketed_units IS NOT NULL
              OR spc.sold_units_cumulative IS NOT NULL
            THEN 'construction_metrics'
        END,
        CASE
            WHEN spc.candidate_section_kind = 'planning'
              OR spc.candidate_lifecycle_stage = 'planning_advanced'
            THEN 'planning_metrics'
        END,
        CASE
            WHEN spc.candidate_section_kind = 'completed'
              OR spc.candidate_lifecycle_stage IN ('completed_unsold_tail', 'completed_delivered')
            THEN 'completed_inventory_tail'
        END,
        CASE
            WHEN spc.candidate_section_kind = 'urban_renewal'
              OR spc.project_business_type = 'urban_renewal'
            THEN 'urban_renewal_pipeline'
        END,
        CASE
            WHEN spc.candidate_section_kind = 'land_reserve'
              OR spc.candidate_lifecycle_stage = 'land_reserve'
            THEN 'land_reserve_details'
        END,
        CASE
            WHEN spc.candidate_section_kind = 'material_project'
              OR spc.candidate_materiality_flag IS TRUE
              OR spc.candidate_disclosure_level = 'material_very_high'
            THEN 'material_project_disclosure'
        END,
        CASE
            WHEN spc.candidate_disclosure_level = 'operational_full'
              OR spc.gross_profit_total_expected IS NOT NULL
              OR spc.gross_margin_expected_pct IS NOT NULL
            THEN 'financing_details'
        END
    ], NULL))
WHERE spc.detected_data_families IS NULL;
