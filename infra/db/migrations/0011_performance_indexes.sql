CREATE INDEX IF NOT EXISTS idx_project_master_public_company
    ON project_master (company_id)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_master_public_city
    ON project_master (city)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_master_public_business_type
    ON project_master (project_business_type)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_master_public_government_program
    ON project_master (government_program_type)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_master_public_urban_renewal
    ON project_master (project_urban_renewal_type)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_master_public_company_city
    ON project_master (company_id, city)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_master_public_name_search
    ON project_master (canonical_name)
    WHERE is_publicly_visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_companies_name_he
    ON companies (name_he);

CREATE INDEX IF NOT EXISTS idx_project_aliases_active_name
    ON project_aliases (alias_name)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_project_snapshots_project_date_created
    ON project_snapshots (project_id, snapshot_date DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_project_permit_date
    ON project_snapshots (project_id, permit_status, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_reports_company_period_publish
    ON reports (company_id, period_end_date DESC, publish_date DESC);

CREATE INDEX IF NOT EXISTS idx_project_addresses_project_primary
    ON project_addresses (project_id, is_primary DESC, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_project_addresses_normalized_lookup
    ON project_addresses (normalized_address_text, normalized_city);

CREATE INDEX IF NOT EXISTS idx_field_provenance_report_entity
    ON field_provenance (source_report_id, entity_id, field_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_staging_candidates_company_review
    ON staging_project_candidates (company_id, matching_status, review_status, publish_status);

CREATE INDEX IF NOT EXISTS idx_review_queue_items_status_candidate
    ON review_queue_items (status, candidate_id, report_id);

CREATE INDEX IF NOT EXISTS idx_candidate_match_suggestions_candidate_state
    ON candidate_match_suggestions (candidate_id, match_state, is_selected);
