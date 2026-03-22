DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alias_source_type_enum') THEN
    CREATE TYPE alias_source_type_enum AS ENUM ('manual', 'source', 'system');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'match_suggestion_state_enum') THEN
    CREATE TYPE match_suggestion_state_enum AS ENUM ('exact', 'likely', 'ambiguous', 'no_match');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'duplicate_review_status_enum') THEN
    CREATE TYPE duplicate_review_status_enum AS ENUM ('open', 'merged', 'dismissed');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'coverage_priority_enum') THEN
    CREATE TYPE coverage_priority_enum AS ENUM ('high', 'medium', 'low');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'historical_coverage_status_enum') THEN
    CREATE TYPE historical_coverage_status_enum AS ENUM ('not_started', 'partial', 'current_only', 'historical_complete');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'snapshot_chronology_status_enum') THEN
    CREATE TYPE snapshot_chronology_status_enum AS ENUM ('ok', 'out_of_order', 'duplicate_date');
  END IF;
END $$;

ALTER TABLE project_aliases
  ADD COLUMN IF NOT EXISTS source_report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS alias_source_type alias_source_type_enum NOT NULL DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE project_master
  ADD COLUMN IF NOT EXISTS merged_into_project_id UUID REFERENCES project_master(id) ON DELETE SET NULL;

ALTER TABLE project_snapshots
  ADD COLUMN IF NOT EXISTS chronology_status snapshot_chronology_status_enum NOT NULL DEFAULT 'ok',
  ADD COLUMN IF NOT EXISTS chronology_notes TEXT;

CREATE TABLE IF NOT EXISTS candidate_match_suggestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES staging_project_candidates(id) ON DELETE CASCADE,
  suggested_project_id UUID REFERENCES project_master(id) ON DELETE CASCADE,
  match_state match_suggestion_state_enum NOT NULL,
  score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  reasons_json JSONB,
  is_selected BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_candidate_match_suggestions UNIQUE (candidate_id, suggested_project_id)
);

CREATE INDEX IF NOT EXISTS idx_candidate_match_suggestions_candidate_id
  ON candidate_match_suggestions (candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_match_suggestions_state
  ON candidate_match_suggestions (match_state, score DESC);

CREATE TABLE IF NOT EXISTS project_duplicate_suggestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
  duplicate_project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
  match_state match_suggestion_state_enum NOT NULL,
  score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  reasons_json JSONB,
  review_status duplicate_review_status_enum NOT NULL DEFAULT 'open',
  reviewed_by UUID REFERENCES admin_users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_project_duplicate_suggestions_self CHECK (project_id <> duplicate_project_id),
  CONSTRAINT uq_project_duplicate_pair UNIQUE (project_id, duplicate_project_id)
);

CREATE INDEX IF NOT EXISTS idx_project_duplicate_suggestions_review_status
  ON project_duplicate_suggestions (review_status, score DESC);

CREATE TABLE IF NOT EXISTS project_merge_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  winner_project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE RESTRICT,
  loser_project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE RESTRICT,
  merged_by UUID REFERENCES admin_users(id) ON DELETE SET NULL,
  merge_reason TEXT,
  summary_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_project_merge_log_distinct CHECK (winner_project_id <> loser_project_id)
);

CREATE INDEX IF NOT EXISTS idx_project_merge_log_winner_project_id
  ON project_merge_log (winner_project_id);
CREATE INDEX IF NOT EXISTS idx_project_merge_log_loser_project_id
  ON project_merge_log (loser_project_id);

CREATE TABLE IF NOT EXISTS company_coverage_registry (
  company_id UUID PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
  is_in_scope BOOLEAN NOT NULL DEFAULT TRUE,
  out_of_scope_reason TEXT,
  coverage_priority coverage_priority_enum NOT NULL DEFAULT 'medium',
  latest_report_ingested_id UUID REFERENCES reports(id) ON DELETE SET NULL,
  historical_coverage_status historical_coverage_status_enum NOT NULL DEFAULT 'not_started',
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_candidate_match_suggestions_updated_at ON candidate_match_suggestions;
CREATE TRIGGER trg_candidate_match_suggestions_updated_at
BEFORE UPDATE ON candidate_match_suggestions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_project_duplicate_suggestions_updated_at ON project_duplicate_suggestions;
CREATE TRIGGER trg_project_duplicate_suggestions_updated_at
BEFORE UPDATE ON project_duplicate_suggestions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_company_coverage_registry_updated_at ON company_coverage_registry;
CREATE TRIGGER trg_company_coverage_registry_updated_at
BEFORE UPDATE ON company_coverage_registry
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
