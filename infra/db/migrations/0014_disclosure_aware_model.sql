DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_lifecycle_stage_enum') THEN
        CREATE TYPE project_lifecycle_stage_enum AS ENUM (
            'under_construction',
            'completed_unsold_tail',
            'completed_delivered',
            'planning_advanced',
            'urban_renewal_pipeline',
            'land_reserve'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_disclosure_level_enum') THEN
        CREATE TYPE project_disclosure_level_enum AS ENUM (
            'material_very_high',
            'operational_full',
            'inventory_tail',
            'pipeline_signature',
            'land_reserve',
            'minimal_reference'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_section_kind_enum') THEN
        CREATE TYPE source_section_kind_enum AS ENUM (
            'construction',
            'planning',
            'completed',
            'land_reserve',
            'urban_renewal',
            'material_project',
            'summary_only'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'provenance_entity_type_enum') THEN
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'material_disclosure';
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'sensitivity_scenario';
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'urban_renewal_detail';
        ALTER TYPE provenance_entity_type_enum ADD VALUE IF NOT EXISTS 'land_reserve_detail';
    END IF;
END
$$;

ALTER TABLE project_master
    ADD COLUMN IF NOT EXISTS lifecycle_stage project_lifecycle_stage_enum,
    ADD COLUMN IF NOT EXISTS disclosure_level project_disclosure_level_enum;

ALTER TABLE project_snapshots
    ADD COLUMN IF NOT EXISTS lifecycle_stage project_lifecycle_stage_enum,
    ADD COLUMN IF NOT EXISTS disclosure_level project_disclosure_level_enum,
    ADD COLUMN IF NOT EXISTS source_section_kind source_section_kind_enum,
    ADD COLUMN IF NOT EXISTS average_unit_sqm NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS signed_area_sqm NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS recognized_revenue NUMERIC(16, 2),
    ADD COLUMN IF NOT EXISTS expected_cost_total NUMERIC(16, 2),
    ADD COLUMN IF NOT EXISTS recognized_gross_profit NUMERIC(16, 2),
    ADD COLUMN IF NOT EXISTS planned_construction_start_date DATE,
    ADD COLUMN IF NOT EXISTS planned_construction_end_date DATE,
    ADD COLUMN IF NOT EXISTS planned_marketing_start_date DATE,
    ADD COLUMN IF NOT EXISTS planned_marketing_end_date DATE;

ALTER TABLE staging_sections
    ADD COLUMN IF NOT EXISTS section_kind source_section_kind_enum,
    ADD COLUMN IF NOT EXISTS extraction_profile_key TEXT;

ALTER TABLE staging_project_candidates
    ADD COLUMN IF NOT EXISTS candidate_lifecycle_stage project_lifecycle_stage_enum,
    ADD COLUMN IF NOT EXISTS candidate_disclosure_level project_disclosure_level_enum,
    ADD COLUMN IF NOT EXISTS candidate_section_kind source_section_kind_enum,
    ADD COLUMN IF NOT EXISTS candidate_materiality_flag BOOLEAN,
    ADD COLUMN IF NOT EXISTS source_table_name TEXT,
    ADD COLUMN IF NOT EXISTS source_row_label TEXT,
    ADD COLUMN IF NOT EXISTS extraction_profile_key TEXT;

ALTER TABLE staging_field_candidates
    ADD COLUMN IF NOT EXISTS source_table_name TEXT,
    ADD COLUMN IF NOT EXISTS source_row_label TEXT,
    ADD COLUMN IF NOT EXISTS extraction_profile_key TEXT;

CREATE TABLE IF NOT EXISTS project_material_disclosures (
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
    expected_economic_profit NUMERIC(16, 2),
    accounting_to_economic_bridge TEXT,
    pledged_or_secured_notes TEXT,
    special_project_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_sensitivity_scenarios (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    sales_price_plus_5_effect NUMERIC(16, 2),
    sales_price_plus_10_effect NUMERIC(16, 2),
    sales_price_minus_5_effect NUMERIC(16, 2),
    sales_price_minus_10_effect NUMERIC(16, 2),
    construction_cost_plus_5_effect NUMERIC(16, 2),
    construction_cost_plus_10_effect NUMERIC(16, 2),
    construction_cost_minus_5_effect NUMERIC(16, 2),
    construction_cost_minus_10_effect NUMERIC(16, 2),
    base_gross_profit_not_yet_recognized NUMERIC(16, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_urban_renewal_details (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    existing_units INTEGER,
    future_units_total INTEGER,
    future_units_marketed_by_company INTEGER,
    future_units_for_existing_tenants INTEGER,
    tenant_signature_rate NUMERIC(6, 2),
    signature_timeline TEXT,
    average_exchange_ratio_signed NUMERIC(8, 3),
    average_exchange_ratio_unsigned NUMERIC(8, 3),
    tenant_relocation_or_demolition_cost NUMERIC(16, 2),
    execution_dependencies TEXT,
    planning_status_text TEXT,
    accounting_treatment_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_land_reserve_details (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES project_snapshots(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    land_area_sqm NUMERIC(16, 2),
    historical_cost NUMERIC(16, 2),
    financing_cost NUMERIC(16, 2),
    planning_cost NUMERIC(16, 2),
    carrying_value NUMERIC(16, 2),
    current_planning_status TEXT,
    requested_planning_status TEXT,
    intended_units INTEGER,
    intended_uses TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_master_lifecycle_stage
    ON project_master (lifecycle_stage);

CREATE INDEX IF NOT EXISTS idx_project_master_disclosure_level
    ON project_master (disclosure_level);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_lifecycle_stage
    ON project_snapshots (lifecycle_stage);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_disclosure_level
    ON project_snapshots (disclosure_level);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_source_section_kind
    ON project_snapshots (source_section_kind);

CREATE INDEX IF NOT EXISTS idx_staging_candidates_section_profile
    ON staging_project_candidates (candidate_section_kind, extraction_profile_key);

CREATE INDEX IF NOT EXISTS idx_staging_candidates_lifecycle_disclosure
    ON staging_project_candidates (candidate_lifecycle_stage, candidate_disclosure_level);

CREATE INDEX IF NOT EXISTS idx_staging_fields_profile
    ON staging_field_candidates (extraction_profile_key, field_name);

CREATE INDEX IF NOT EXISTS idx_material_disclosures_project_snapshot
    ON project_material_disclosures (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_sensitivity_scenarios_project_snapshot
    ON project_sensitivity_scenarios (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_urban_renewal_details_project_snapshot
    ON project_urban_renewal_details (project_id, snapshot_id);

CREATE INDEX IF NOT EXISTS idx_land_reserve_details_project_snapshot
    ON project_land_reserve_details (project_id, snapshot_id);

UPDATE project_master
SET lifecycle_stage = CASE
        WHEN project_business_type = 'urban_renewal' THEN 'urban_renewal_pipeline'::project_lifecycle_stage_enum
        ELSE lifecycle_stage
    END
WHERE lifecycle_stage IS NULL
  AND project_business_type = 'urban_renewal';

UPDATE project_master
SET lifecycle_stage = CASE
        WHEN EXISTS (
            SELECT 1
            FROM project_snapshots ps
            WHERE ps.project_id = project_master.id
              AND ps.project_status = 'construction'
        ) THEN 'under_construction'::project_lifecycle_stage_enum
        WHEN EXISTS (
            SELECT 1
            FROM project_snapshots ps
            WHERE ps.project_id = project_master.id
              AND ps.project_status = 'completed'
              AND COALESCE(ps.unsold_units, 0) > 0
        ) THEN 'completed_unsold_tail'::project_lifecycle_stage_enum
        WHEN EXISTS (
            SELECT 1
            FROM project_snapshots ps
            WHERE ps.project_id = project_master.id
              AND ps.project_status = 'completed'
        ) THEN 'completed_delivered'::project_lifecycle_stage_enum
        WHEN EXISTS (
            SELECT 1
            FROM project_snapshots ps
            WHERE ps.project_id = project_master.id
              AND ps.project_status IN ('planning', 'permit')
        ) THEN 'planning_advanced'::project_lifecycle_stage_enum
        ELSE lifecycle_stage
    END
WHERE lifecycle_stage IS NULL;

UPDATE project_master
SET disclosure_level = CASE
        WHEN lifecycle_stage = 'land_reserve' THEN 'land_reserve'::project_disclosure_level_enum
        WHEN lifecycle_stage = 'urban_renewal_pipeline' THEN 'pipeline_signature'::project_disclosure_level_enum
        WHEN lifecycle_stage = 'completed_unsold_tail' THEN 'inventory_tail'::project_disclosure_level_enum
        WHEN EXISTS (
            SELECT 1
            FROM field_provenance fp
            WHERE fp.entity_type = 'snapshot'
              AND fp.entity_id IN (
                  SELECT ps.id
                  FROM project_snapshots ps
                  WHERE ps.project_id = project_master.id
              )
              AND fp.field_name IN (
                  'gross_profit_total_expected',
                  'expected_revenue_total',
                  'receivables_from_signed_contracts',
                  'advances_received'
              )
        ) THEN 'operational_full'::project_disclosure_level_enum
        ELSE disclosure_level
    END
WHERE disclosure_level IS NULL;

UPDATE project_snapshots
SET lifecycle_stage = project_master.lifecycle_stage,
    disclosure_level = project_master.disclosure_level
FROM project_master
WHERE project_master.id = project_snapshots.project_id
  AND (project_snapshots.lifecycle_stage IS NULL OR project_snapshots.disclosure_level IS NULL);
