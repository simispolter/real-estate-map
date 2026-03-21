ALTER TYPE value_origin_type_enum ADD VALUE IF NOT EXISTS 'manual';
ALTER TYPE value_origin_type_enum ADD VALUE IF NOT EXISTS 'imported';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'report_ingestion_status_enum') THEN
    CREATE TYPE report_ingestion_status_enum AS ENUM (
      'draft',
      'ready_for_staging',
      'in_review',
      'published',
      'rejected'
    );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'candidate_match_status_enum') THEN
    CREATE TYPE candidate_match_status_enum AS ENUM (
      'unmatched',
      'matched_existing_project',
      'new_project_needed',
      'ambiguous_match',
      'ignored'
    );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'staging_publish_status_enum') THEN
    CREATE TYPE staging_publish_status_enum AS ENUM (
      'draft',
      'in_review',
      'partially_approved',
      'published',
      'rejected'
    );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_queue_status_enum') THEN
    CREATE TYPE review_queue_status_enum AS ENUM ('open', 'in_progress', 'done', 'ignored');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_queue_entity_type_enum') THEN
    CREATE TYPE review_queue_entity_type_enum AS ENUM (
      'report',
      'candidate',
      'field_candidate',
      'address_candidate'
    );
  END IF;
END $$;

ALTER TABLE reports
  ALTER COLUMN source_file_path DROP NOT NULL;

ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS source_url TEXT,
  ADD COLUMN IF NOT EXISTS source_is_official BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS source_label TEXT,
  ADD COLUMN IF NOT EXISTS ingestion_status report_ingestion_status_enum NOT NULL DEFAULT 'draft',
  ADD COLUMN IF NOT EXISTS notes TEXT;

ALTER TABLE field_provenance
  ADD COLUMN IF NOT EXISTS review_note TEXT;

UPDATE reports
SET
  source_url = COALESCE(source_url, source_file_path),
  source_is_official = CASE
    WHEN source_file_path ILIKE '%financialreports.eu%' THEN FALSE
    WHEN source_file_path IS NOT NULL THEN TRUE
    ELSE FALSE
  END,
  source_label = COALESCE(
    source_label,
    CASE
      WHEN source_file_path ILIKE '%financialreports.eu%' THEN 'Public filing mirror'
      WHEN source_file_path IS NOT NULL THEN 'Official filing source'
      ELSE 'Manual registry'
    END
  ),
  ingestion_status = CASE
    WHEN status = 'published' THEN 'published'::report_ingestion_status_enum
    WHEN status = 'reviewed' THEN 'in_review'::report_ingestion_status_enum
    ELSE 'draft'::report_ingestion_status_enum
  END;

CREATE INDEX IF NOT EXISTS idx_reports_ingestion_status ON reports (ingestion_status);
CREATE INDEX IF NOT EXISTS idx_reports_source_is_official ON reports (source_is_official);

CREATE TABLE IF NOT EXISTS staging_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id UUID NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
  publish_status staging_publish_status_enum NOT NULL DEFAULT 'draft',
  review_status review_status_enum NOT NULL DEFAULT 'pending',
  notes_internal TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_reports_company_id ON staging_reports (company_id);
CREATE INDEX IF NOT EXISTS idx_staging_reports_publish_status ON staging_reports (publish_status);

CREATE TABLE IF NOT EXISTS staging_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staging_report_id UUID NOT NULL REFERENCES staging_reports(id) ON DELETE CASCADE,
  section_name TEXT NOT NULL,
  raw_label TEXT,
  source_page_from INTEGER,
  source_page_to INTEGER,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_sections_report_id ON staging_sections (staging_report_id);

CREATE TABLE IF NOT EXISTS staging_project_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staging_report_id UUID NOT NULL REFERENCES staging_reports(id) ON DELETE CASCADE,
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
  staging_section_id UUID REFERENCES staging_sections(id) ON DELETE SET NULL,
  matched_project_id UUID REFERENCES project_master(id) ON DELETE SET NULL,
  candidate_project_name TEXT NOT NULL,
  city TEXT,
  neighborhood TEXT,
  project_business_type project_business_type_enum,
  government_program_type government_program_type_enum NOT NULL DEFAULT 'none',
  project_urban_renewal_type project_urban_renewal_type_enum NOT NULL DEFAULT 'none',
  project_status project_status_enum,
  permit_status permit_status_enum,
  total_units INTEGER,
  marketed_units INTEGER,
  sold_units_cumulative INTEGER,
  unsold_units INTEGER,
  avg_price_per_sqm_cumulative NUMERIC(14, 2),
  gross_profit_total_expected NUMERIC(16, 2),
  gross_margin_expected_pct NUMERIC(6, 2),
  location_confidence location_confidence_enum NOT NULL DEFAULT 'unknown',
  value_origin_type value_origin_type_enum NOT NULL DEFAULT 'manual',
  confidence_level classification_confidence_enum NOT NULL DEFAULT 'medium',
  matching_status candidate_match_status_enum NOT NULL DEFAULT 'unmatched',
  publish_status staging_publish_status_enum NOT NULL DEFAULT 'draft',
  review_status review_status_enum NOT NULL DEFAULT 'pending',
  review_notes TEXT,
  diff_summary JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_project_candidates_report_id ON staging_project_candidates (staging_report_id);
CREATE INDEX IF NOT EXISTS idx_staging_project_candidates_company_id ON staging_project_candidates (company_id);
CREATE INDEX IF NOT EXISTS idx_staging_project_candidates_matched_project_id ON staging_project_candidates (matched_project_id);
CREATE INDEX IF NOT EXISTS idx_staging_project_candidates_matching_status ON staging_project_candidates (matching_status);
CREATE INDEX IF NOT EXISTS idx_staging_project_candidates_publish_status ON staging_project_candidates (publish_status);

CREATE TABLE IF NOT EXISTS staging_field_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES staging_project_candidates(id) ON DELETE CASCADE,
  field_name TEXT NOT NULL,
  raw_value TEXT,
  normalized_value TEXT,
  source_page INTEGER,
  source_section TEXT,
  value_origin_type value_origin_type_enum NOT NULL DEFAULT 'manual',
  confidence_level classification_confidence_enum NOT NULL DEFAULT 'medium',
  review_status review_status_enum NOT NULL DEFAULT 'pending',
  review_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_field_candidates_candidate_id ON staging_field_candidates (candidate_id);
CREATE INDEX IF NOT EXISTS idx_staging_field_candidates_field_name ON staging_field_candidates (field_name);

CREATE TABLE IF NOT EXISTS staging_address_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES staging_project_candidates(id) ON DELETE CASCADE,
  address_text_raw TEXT,
  street TEXT,
  house_number_from INTEGER,
  house_number_to INTEGER,
  city TEXT,
  lat NUMERIC(10, 7),
  lng NUMERIC(10, 7),
  location_confidence location_confidence_enum NOT NULL DEFAULT 'unknown',
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  value_origin_type value_origin_type_enum NOT NULL DEFAULT 'manual',
  confidence_level classification_confidence_enum NOT NULL DEFAULT 'medium',
  review_status review_status_enum NOT NULL DEFAULT 'pending',
  review_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_address_candidates_candidate_id ON staging_address_candidates (candidate_id);

CREATE TABLE IF NOT EXISTS review_queue_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type review_queue_entity_type_enum NOT NULL,
  entity_id UUID NOT NULL,
  report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
  candidate_id UUID REFERENCES staging_project_candidates(id) ON DELETE CASCADE,
  status review_queue_status_enum NOT NULL DEFAULT 'open',
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_queue_items_status ON review_queue_items (status);
CREATE INDEX IF NOT EXISTS idx_review_queue_items_report_id ON review_queue_items (report_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_items_candidate_id ON review_queue_items (candidate_id);

DROP TRIGGER IF EXISTS trg_staging_reports_updated_at ON staging_reports;
CREATE TRIGGER trg_staging_reports_updated_at
BEFORE UPDATE ON staging_reports
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_staging_sections_updated_at ON staging_sections;
CREATE TRIGGER trg_staging_sections_updated_at
BEFORE UPDATE ON staging_sections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_staging_project_candidates_updated_at ON staging_project_candidates;
CREATE TRIGGER trg_staging_project_candidates_updated_at
BEFORE UPDATE ON staging_project_candidates
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_staging_field_candidates_updated_at ON staging_field_candidates;
CREATE TRIGGER trg_staging_field_candidates_updated_at
BEFORE UPDATE ON staging_field_candidates
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_staging_address_candidates_updated_at ON staging_address_candidates;
CREATE TRIGGER trg_staging_address_candidates_updated_at
BEFORE UPDATE ON staging_address_candidates
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_review_queue_items_updated_at ON review_queue_items;
CREATE TRIGGER trg_review_queue_items_updated_at
BEFORE UPDATE ON review_queue_items
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
