DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'external_layer_geometry_type_enum') THEN
    CREATE TYPE external_layer_geometry_type_enum AS ENUM ('point', 'line', 'polygon', 'mixed');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'external_layer_update_cadence_enum') THEN
    CREATE TYPE external_layer_update_cadence_enum AS ENUM ('ad_hoc', 'daily', 'weekly', 'monthly', 'quarterly', 'annual');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'external_layer_visibility_enum') THEN
    CREATE TYPE external_layer_visibility_enum AS ENUM ('public', 'admin_only', 'hidden');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'external_relation_method_enum') THEN
    CREATE TYPE external_relation_method_enum AS ENUM ('address_based', 'geometry_overlap', 'manual_linkage');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'external_relation_status_enum') THEN
    CREATE TYPE external_relation_status_enum AS ENUM ('suggested', 'confirmed', 'rejected');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS external_layers (
  id UUID PRIMARY KEY,
  layer_name TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT,
  geometry_type external_layer_geometry_type_enum NOT NULL DEFAULT 'point',
  update_cadence external_layer_update_cadence_enum NOT NULL DEFAULT 'ad_hoc',
  quality_score NUMERIC(5,2),
  visibility external_layer_visibility_enum NOT NULL DEFAULT 'public',
  notes TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  default_on_map BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS external_layer_records (
  id UUID PRIMARY KEY,
  layer_id UUID NOT NULL REFERENCES external_layers(id) ON DELETE CASCADE,
  external_record_id TEXT NOT NULL,
  label TEXT,
  city TEXT,
  geometry_geojson JSONB,
  display_center_lat NUMERIC(10,7),
  display_center_lng NUMERIC(10,7),
  properties_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  effective_date DATE,
  source_metadata JSONB,
  update_metadata JSONB,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(layer_id, external_record_id)
);

CREATE TABLE IF NOT EXISTS external_layer_project_relations (
  id UUID PRIMARY KEY,
  external_layer_record_id UUID NOT NULL REFERENCES external_layer_records(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
  relation_method external_relation_method_enum NOT NULL,
  confidence_level classification_confidence_enum NOT NULL DEFAULT 'medium',
  relation_status external_relation_status_enum NOT NULL DEFAULT 'suggested',
  notes TEXT,
  metadata_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_external_layers_visibility
  ON external_layers (visibility, is_active, default_on_map);
CREATE INDEX IF NOT EXISTS idx_external_layer_records_layer_city
  ON external_layer_records (layer_id, city, is_active);
CREATE INDEX IF NOT EXISTS idx_external_layer_relations_project
  ON external_layer_project_relations (project_id, relation_status);
