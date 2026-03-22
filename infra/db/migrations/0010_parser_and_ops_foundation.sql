DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'parser_run_status_enum') THEN
    CREATE TYPE parser_run_status_enum AS ENUM ('queued', 'running', 'succeeded', 'partial', 'failed');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS parser_run_logs (
  id UUID PRIMARY KEY,
  report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  staging_report_id UUID REFERENCES staging_reports(id) ON DELETE SET NULL,
  status parser_run_status_enum NOT NULL DEFAULT 'queued',
  parser_version TEXT NOT NULL,
  source_label TEXT,
  source_reference TEXT,
  source_checksum TEXT,
  sections_found INTEGER NOT NULL DEFAULT 0,
  candidate_count INTEGER NOT NULL DEFAULT 0,
  field_candidate_count INTEGER NOT NULL DEFAULT 0,
  address_candidate_count INTEGER NOT NULL DEFAULT 0,
  warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  errors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  diagnostics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE staging_sections
  ADD COLUMN IF NOT EXISTS parser_run_id UUID REFERENCES parser_run_logs(id) ON DELETE SET NULL;

ALTER TABLE staging_project_candidates
  ADD COLUMN IF NOT EXISTS parser_run_id UUID REFERENCES parser_run_logs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_parser_run_logs_report
  ON parser_run_logs (report_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_parser_run_logs_status
  ON parser_run_logs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_staging_sections_parser_run
  ON staging_sections (parser_run_id);

CREATE INDEX IF NOT EXISTS idx_staging_project_candidates_parser_run
  ON staging_project_candidates (parser_run_id);
