DO $$
BEGIN
    CREATE TYPE coverage_backfill_status_enum AS ENUM (
        'not_started',
        'current_cycle_only',
        'historical_backfill',
        'complete',
        'blocked'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS is_in_scope BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE company_coverage_registry
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS latest_report_registered_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS latest_report_published_date DATE,
    ADD COLUMN IF NOT EXISTS historical_coverage_start DATE,
    ADD COLUMN IF NOT EXISTS historical_coverage_end DATE,
    ADD COLUMN IF NOT EXISTS backfill_status coverage_backfill_status_enum NOT NULL DEFAULT 'not_started';

ALTER TABLE project_addresses
    ADD COLUMN IF NOT EXISTS normalized_display_address TEXT,
    ADD COLUMN IF NOT EXISTS is_geocoding_ready BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS geocoding_method TEXT,
    ADD COLUMN IF NOT EXISTS geocoding_source_label TEXT;

CREATE INDEX IF NOT EXISTS idx_company_coverage_scope_priority
    ON company_coverage_registry (is_active, is_in_scope, coverage_priority, backfill_status);

CREATE INDEX IF NOT EXISTS idx_reports_company_scope_period
    ON reports (company_id, is_in_scope, period_end_date DESC, publish_date DESC);

CREATE INDEX IF NOT EXISTS idx_project_addresses_location_review
    ON project_addresses (project_id, is_primary DESC, geocoding_status, location_confidence, is_geocoding_ready);

CREATE INDEX IF NOT EXISTS idx_project_master_location_review
    ON project_master (location_confidence, company_id, city)
    WHERE deleted_at IS NULL;
