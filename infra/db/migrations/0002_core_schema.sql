CREATE TYPE company_public_status_enum AS ENUM ('public', 'delisted', 'merged');
CREATE TYPE company_sector_enum AS ENUM ('residential_developer');
CREATE TYPE report_type_enum AS ENUM ('annual', 'q1', 'q2', 'q3', 'prospectus', 'presentation');
CREATE TYPE report_period_type_enum AS ENUM ('annual', 'quarterly', 'interim');
CREATE TYPE report_status_enum AS ENUM ('uploaded', 'parsed', 'reviewed', 'published', 'failed');
CREATE TYPE asset_domain_enum AS ENUM ('residential_only');
CREATE TYPE project_business_type_enum AS ENUM ('regular_dev', 'govt_program', 'urban_renewal');
CREATE TYPE government_program_type_enum AS ENUM (
  'none',
  'mechir_lamishtaken',
  'mechir_metara',
  'dira_bahanaa',
  'other'
);
CREATE TYPE project_urban_renewal_type_enum AS ENUM (
  'none',
  'pinui_binui',
  'tama_38_1',
  'tama_38_2',
  'other'
);
CREATE TYPE project_deal_type_enum AS ENUM ('ownership', 'combination', 'tmurot', 'jv', 'option', 'other');
CREATE TYPE project_usage_profile_enum AS ENUM (
  'residential_only',
  'residential_commercial',
  'residential_mixed'
);
CREATE TYPE location_confidence_enum AS ENUM ('exact', 'street', 'neighborhood', 'city', 'unknown');
CREATE TYPE classification_confidence_enum AS ENUM ('high', 'medium', 'low');
CREATE TYPE mapping_review_status_enum AS ENUM ('pending', 'reviewed', 'approved', 'rejected');
CREATE TYPE geometry_type_enum AS ENUM ('point', 'line', 'polygon', 'approximate_area');
CREATE TYPE address_source_type_enum AS ENUM ('parser', 'admin', 'geocoder', 'imported');
CREATE TYPE project_status_enum AS ENUM ('planning', 'permit', 'construction', 'marketing', 'completed', 'stalled');
CREATE TYPE permit_status_enum AS ENUM ('none', 'pending', 'granted', 'partial');
CREATE TYPE land_reserve_status_enum AS ENUM ('reserve', 'planning', 'suspended');
CREATE TYPE sensitivity_type_enum AS ENUM ('sale_price', 'construction_cost', 'finance_cost');
CREATE TYPE impact_metric_enum AS ENUM ('revenue', 'profit', 'margin');
CREATE TYPE provenance_entity_type_enum AS ENUM ('project_master', 'snapshot', 'land_reserve', 'address');
CREATE TYPE extraction_method_enum AS ENUM ('table', 'text', 'rule', 'llm', 'admin');
CREATE TYPE review_status_enum AS ENUM ('pending', 'approved', 'corrected', 'rejected');
CREATE TYPE admin_user_role_enum AS ENUM ('admin', 'super_admin');

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name_he TEXT NOT NULL,
  name_en TEXT,
  ticker TEXT,
  public_status company_public_status_enum NOT NULL DEFAULT 'public',
  sector company_sector_enum NOT NULL DEFAULT 'residential_developer',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_companies_name_he ON companies (name_he);
CREATE INDEX idx_companies_ticker ON companies (ticker);

CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  full_name TEXT,
  role admin_user_role_enum NOT NULL DEFAULT 'admin',
  password_hash TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_admin_users_email ON admin_users (email);

CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
  report_type report_type_enum NOT NULL,
  period_type report_period_type_enum NOT NULL,
  period_start_date DATE,
  period_end_date DATE NOT NULL,
  publish_date DATE NOT NULL,
  filing_reference TEXT,
  source_file_path TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  checksum TEXT,
  status report_status_enum NOT NULL DEFAULT 'uploaded',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_reports_company_period ON reports (company_id, report_type, period_end_date, publish_date);
CREATE INDEX idx_reports_company_period_end_date ON reports (company_id, period_end_date DESC);

CREATE TABLE project_master (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
  canonical_name TEXT NOT NULL,
  city TEXT,
  neighborhood TEXT,
  district TEXT,
  asset_domain asset_domain_enum NOT NULL DEFAULT 'residential_only',
  project_business_type project_business_type_enum NOT NULL,
  government_program_type government_program_type_enum NOT NULL DEFAULT 'none',
  project_urban_renewal_type project_urban_renewal_type_enum NOT NULL DEFAULT 'none',
  project_deal_type project_deal_type_enum NOT NULL DEFAULT 'ownership',
  project_usage_profile project_usage_profile_enum NOT NULL DEFAULT 'residential_only',
  is_publicly_visible BOOLEAN NOT NULL DEFAULT FALSE,
  location_confidence location_confidence_enum NOT NULL DEFAULT 'unknown',
  classification_confidence classification_confidence_enum NOT NULL DEFAULT 'medium',
  mapping_review_status mapping_review_status_enum NOT NULL DEFAULT 'pending',
  source_conflict_flag BOOLEAN NOT NULL DEFAULT FALSE,
  notes_internal TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT chk_project_master_government_program_consistency
    CHECK (
      (project_business_type = 'govt_program' AND government_program_type <> 'none')
      OR (project_business_type <> 'govt_program' AND government_program_type = 'none')
    ),
  CONSTRAINT chk_project_master_urban_renewal_consistency
    CHECK (
      (project_business_type = 'urban_renewal' AND project_urban_renewal_type <> 'none')
      OR (project_business_type <> 'urban_renewal' AND project_urban_renewal_type = 'none')
      OR (project_business_type = 'urban_renewal' AND project_urban_renewal_type = 'other')
    )
);

CREATE INDEX idx_project_master_company_id ON project_master (company_id);
CREATE INDEX idx_project_master_city ON project_master (city);
CREATE INDEX idx_project_master_neighborhood ON project_master (neighborhood);
CREATE INDEX idx_project_master_project_business_type ON project_master (project_business_type);
CREATE INDEX idx_project_master_visibility ON project_master (is_publicly_visible);
CREATE INDEX idx_project_master_mapping_review_status ON project_master (mapping_review_status);
CREATE INDEX idx_project_master_canonical_name_trgm ON project_master USING GIN (canonical_name gin_trgm_ops);

CREATE TABLE project_addresses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
  address_text_raw TEXT,
  street TEXT,
  house_number_from INTEGER,
  house_number_to INTEGER,
  city TEXT,
  postal_code TEXT,
  lat NUMERIC(10, 7),
  lng NUMERIC(10, 7),
  geom geometry(Geometry, 4326),
  geometry_type geometry_type_enum NOT NULL DEFAULT 'point',
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  location_confidence location_confidence_enum NOT NULL DEFAULT 'unknown',
  source_type address_source_type_enum NOT NULL DEFAULT 'parser',
  assigned_by UUID REFERENCES admin_users(id) ON DELETE SET NULL,
  assigned_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_project_addresses_lat_range CHECK (lat IS NULL OR (lat BETWEEN -90 AND 90)),
  CONSTRAINT chk_project_addresses_lng_range CHECK (lng IS NULL OR (lng BETWEEN -180 AND 180))
);

CREATE INDEX idx_project_addresses_project_id ON project_addresses (project_id);
CREATE INDEX idx_project_addresses_city_street ON project_addresses (city, street);
CREATE INDEX idx_project_addresses_location_confidence ON project_addresses (location_confidence);
CREATE INDEX idx_project_addresses_geom ON project_addresses USING GIST (geom);
CREATE UNIQUE INDEX uq_project_addresses_primary ON project_addresses (project_id) WHERE is_primary;

CREATE TABLE project_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
  report_id UUID NOT NULL REFERENCES reports(id) ON DELETE RESTRICT,
  snapshot_date DATE NOT NULL,
  project_status project_status_enum,
  permit_status permit_status_enum,
  planning_status TEXT,
  signature_rate NUMERIC(5, 2),
  engineering_completion_rate NUMERIC(5, 2),
  financial_completion_rate NUMERIC(5, 2),
  total_units INTEGER,
  marketed_units INTEGER,
  sold_units_period INTEGER,
  sold_units_cumulative INTEGER,
  unsold_units INTEGER,
  sold_area_sqm_period NUMERIC(14, 2),
  sold_area_sqm_cumulative NUMERIC(14, 2),
  unsold_area_sqm NUMERIC(14, 2),
  avg_price_per_sqm_period NUMERIC(14, 2),
  avg_price_per_sqm_cumulative NUMERIC(14, 2),
  recognized_revenue_to_date NUMERIC(16, 2),
  expected_revenue_total NUMERIC(16, 2),
  expected_revenue_signed_contracts NUMERIC(16, 2),
  expected_revenue_unsold_inventory NUMERIC(16, 2),
  gross_profit_total_expected NUMERIC(16, 2),
  gross_profit_recognized NUMERIC(16, 2),
  gross_profit_unrecognized NUMERIC(16, 2),
  gross_margin_expected_pct NUMERIC(6, 2),
  expected_pre_tax_profit NUMERIC(16, 2),
  land_cost NUMERIC(16, 2),
  development_cost NUMERIC(16, 2),
  finance_cost_capitalized NUMERIC(16, 2),
  other_project_costs NUMERIC(16, 2),
  advances_received NUMERIC(16, 2),
  receivables_from_signed_contracts NUMERIC(16, 2),
  estimated_start_date DATE,
  estimated_completion_date DATE,
  needs_admin_review BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_project_snapshots_project_report ON project_snapshots (project_id, report_id);
CREATE INDEX idx_project_snapshots_project_date ON project_snapshots (project_id, snapshot_date DESC);
CREATE INDEX idx_project_snapshots_report_id ON project_snapshots (report_id);
CREATE INDEX idx_project_snapshots_project_status ON project_snapshots (project_status);
CREATE INDEX idx_project_snapshots_permit_status ON project_snapshots (permit_status);

CREATE TABLE land_reserves (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
  related_project_id UUID REFERENCES project_master(id) ON DELETE SET NULL,
  reserve_name TEXT NOT NULL,
  city TEXT,
  neighborhood TEXT,
  reserve_status land_reserve_status_enum NOT NULL DEFAULT 'reserve',
  planned_units INTEGER,
  land_area_sqm NUMERIC(16, 2),
  deal_type project_deal_type_enum,
  notes TEXT,
  is_publicly_visible BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_land_reserves_company_id ON land_reserves (company_id);
CREATE INDEX idx_land_reserves_city ON land_reserves (city);
CREATE INDEX idx_land_reserves_related_project_id ON land_reserves (related_project_id);

CREATE TABLE project_sensitivities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id UUID NOT NULL REFERENCES project_snapshots(id) ON DELETE CASCADE,
  sensitivity_type sensitivity_type_enum NOT NULL,
  delta_pct NUMERIC(6, 2) NOT NULL,
  impact_value NUMERIC(16, 2) NOT NULL,
  impact_metric impact_metric_enum NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_project_sensitivities_snapshot_id ON project_sensitivities (snapshot_id);
CREATE INDEX idx_project_sensitivities_type ON project_sensitivities (sensitivity_type);

CREATE TABLE field_provenance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type provenance_entity_type_enum NOT NULL,
  entity_id UUID NOT NULL,
  field_name TEXT NOT NULL,
  raw_value TEXT,
  normalized_value TEXT,
  source_report_id UUID NOT NULL REFERENCES reports(id) ON DELETE RESTRICT,
  source_page INTEGER,
  source_section TEXT,
  extraction_method extraction_method_enum NOT NULL,
  parser_version TEXT,
  confidence_score NUMERIC(5, 2),
  review_status review_status_enum NOT NULL DEFAULT 'pending',
  reviewed_by UUID REFERENCES admin_users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_field_provenance_entity_lookup ON field_provenance (entity_type, entity_id);
CREATE INDEX idx_field_provenance_source_report_id ON field_provenance (source_report_id);
CREATE INDEX idx_field_provenance_field_name ON field_provenance (field_name);
CREATE INDEX idx_field_provenance_review_status ON field_provenance (review_status);

CREATE TABLE admin_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES admin_users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  diff_json JSONB,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_admin_audit_log_actor_user_id ON admin_audit_log (actor_user_id);
CREATE INDEX idx_admin_audit_log_entity_lookup ON admin_audit_log (entity_type, entity_id);
CREATE INDEX idx_admin_audit_log_created_at ON admin_audit_log (created_at DESC);

CREATE TRIGGER trg_companies_updated_at
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_admin_users_updated_at
BEFORE UPDATE ON admin_users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_reports_updated_at
BEFORE UPDATE ON reports
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_project_master_updated_at
BEFORE UPDATE ON project_master
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_project_addresses_updated_at
BEFORE UPDATE ON project_addresses
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_project_snapshots_updated_at
BEFORE UPDATE ON project_snapshots
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_land_reserves_updated_at
BEFORE UPDATE ON land_reserves
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_project_sensitivities_updated_at
BEFORE UPDATE ON project_sensitivities
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
