DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'location_confidence_enum') THEN
    ALTER TYPE location_confidence_enum RENAME TO location_confidence_enum_old;
  END IF;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'location_confidence_enum') THEN
    CREATE TYPE location_confidence_enum AS ENUM ('exact', 'approximate', 'city_only', 'unknown');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'spatial_geometry_type_enum') THEN
    CREATE TYPE spatial_geometry_type_enum AS ENUM (
      'exact_point',
      'approximate_point',
      'address_range',
      'polygon',
      'area',
      'city_centroid',
      'unknown'
    );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'geometry_source_enum') THEN
    CREATE TYPE geometry_source_enum AS ENUM (
      'reported',
      'geocoded',
      'manual_override',
      'city_registry',
      'inferred',
      'unknown'
    );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'geocoding_status_enum') THEN
    CREATE TYPE geocoding_status_enum AS ENUM (
      'not_started',
      'normalized',
      'geocoded',
      'failed',
      'manual_override'
    );
  END IF;
END $$;

ALTER TABLE project_master
  ALTER COLUMN location_confidence DROP DEFAULT;
ALTER TABLE project_addresses
  ALTER COLUMN location_confidence DROP DEFAULT;
ALTER TABLE staging_project_candidates
  ALTER COLUMN location_confidence DROP DEFAULT;
ALTER TABLE staging_address_candidates
  ALTER COLUMN location_confidence DROP DEFAULT;

ALTER TABLE project_master
  ALTER COLUMN location_confidence TYPE location_confidence_enum
  USING (
    CASE
      WHEN location_confidence::text = 'exact' THEN 'exact'
      WHEN location_confidence::text IN ('street', 'neighborhood', 'approximate') THEN 'approximate'
      WHEN location_confidence::text IN ('city', 'city_only') THEN 'city_only'
      ELSE 'unknown'
    END
  )::location_confidence_enum;

ALTER TABLE project_addresses
  ALTER COLUMN location_confidence TYPE location_confidence_enum
  USING (
    CASE
      WHEN location_confidence::text = 'exact' THEN 'exact'
      WHEN location_confidence::text IN ('street', 'neighborhood', 'approximate') THEN 'approximate'
      WHEN location_confidence::text IN ('city', 'city_only') THEN 'city_only'
      ELSE 'unknown'
    END
  )::location_confidence_enum;

ALTER TABLE staging_project_candidates
  ALTER COLUMN location_confidence TYPE location_confidence_enum
  USING (
    CASE
      WHEN location_confidence::text = 'exact' THEN 'exact'
      WHEN location_confidence::text IN ('street', 'neighborhood', 'approximate') THEN 'approximate'
      WHEN location_confidence::text IN ('city', 'city_only') THEN 'city_only'
      ELSE 'unknown'
    END
  )::location_confidence_enum;

ALTER TABLE staging_address_candidates
  ALTER COLUMN location_confidence TYPE location_confidence_enum
  USING (
    CASE
      WHEN location_confidence::text = 'exact' THEN 'exact'
      WHEN location_confidence::text IN ('street', 'neighborhood', 'approximate') THEN 'approximate'
      WHEN location_confidence::text IN ('city', 'city_only') THEN 'city_only'
      ELSE 'unknown'
    END
  )::location_confidence_enum;

ALTER TABLE project_master
  ALTER COLUMN location_confidence SET DEFAULT 'unknown';
ALTER TABLE project_addresses
  ALTER COLUMN location_confidence SET DEFAULT 'unknown';
ALTER TABLE staging_project_candidates
  ALTER COLUMN location_confidence SET DEFAULT 'unknown';
ALTER TABLE staging_address_candidates
  ALTER COLUMN location_confidence SET DEFAULT 'unknown';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'location_confidence_enum_old') THEN
    DROP TYPE location_confidence_enum_old;
  END IF;
END $$;

ALTER TABLE project_master
  ADD COLUMN IF NOT EXISTS display_geometry_type spatial_geometry_type_enum NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS display_geometry_source geometry_source_enum NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS display_geometry_confidence location_confidence_enum NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS display_geometry_geojson JSONB,
  ADD COLUMN IF NOT EXISTS display_center_lat NUMERIC(10, 7),
  ADD COLUMN IF NOT EXISTS display_center_lng NUMERIC(10, 7),
  ADD COLUMN IF NOT EXISTS display_address_summary TEXT,
  ADD COLUMN IF NOT EXISTS display_geometry_note TEXT;

ALTER TABLE project_addresses
  ADD COLUMN IF NOT EXISTS normalized_address_text TEXT,
  ADD COLUMN IF NOT EXISTS normalized_street TEXT,
  ADD COLUMN IF NOT EXISTS normalized_city TEXT,
  ADD COLUMN IF NOT EXISTS geometry_source geometry_source_enum NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS geocoding_status geocoding_status_enum NOT NULL DEFAULT 'not_started',
  ADD COLUMN IF NOT EXISTS geocoding_provider TEXT,
  ADD COLUMN IF NOT EXISTS geocoding_query TEXT,
  ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS geocoding_note TEXT;

UPDATE project_addresses
SET
  normalized_address_text = COALESCE(normalized_address_text, address_text_raw),
  normalized_street = COALESCE(normalized_street, street),
  normalized_city = COALESCE(normalized_city, city),
  geometry_source = CASE
    WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 'reported'::geometry_source_enum
    ELSE geometry_source
  END,
  geocoding_status = CASE
    WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 'geocoded'::geocoding_status_enum
    ELSE geocoding_status
  END,
  geocoding_query = COALESCE(geocoding_query, address_text_raw, city);

UPDATE project_master project
SET
  display_geometry_type = CASE
    WHEN address.lat IS NOT NULL AND address.lng IS NOT NULL AND address.location_confidence = 'exact' THEN 'exact_point'::spatial_geometry_type_enum
    WHEN address.lat IS NOT NULL AND address.lng IS NOT NULL THEN 'approximate_point'::spatial_geometry_type_enum
    WHEN project.city IS NOT NULL THEN 'city_centroid'::spatial_geometry_type_enum
    ELSE 'unknown'::spatial_geometry_type_enum
  END,
  display_geometry_source = CASE
    WHEN address.lat IS NOT NULL AND address.lng IS NOT NULL THEN address.geometry_source
    WHEN project.city IS NOT NULL THEN 'city_registry'::geometry_source_enum
    ELSE 'unknown'::geometry_source_enum
  END,
  display_geometry_confidence = CASE
    WHEN address.lat IS NOT NULL AND address.lng IS NOT NULL THEN address.location_confidence
    WHEN project.city IS NOT NULL THEN 'city_only'::location_confidence_enum
    ELSE 'unknown'::location_confidence_enum
  END,
  display_geometry_geojson = CASE
    WHEN address.lat IS NOT NULL AND address.lng IS NOT NULL THEN jsonb_build_object(
      'type', 'Point',
      'coordinates', jsonb_build_array((address.lng)::numeric, (address.lat)::numeric)
    )
    ELSE display_geometry_geojson
  END,
  display_center_lat = COALESCE(address.lat, display_center_lat),
  display_center_lng = COALESCE(address.lng, display_center_lng),
  display_address_summary = COALESCE(address.normalized_address_text, address.address_text_raw, address.city, project.city),
  display_geometry_note = CASE
    WHEN address.lat IS NOT NULL AND address.lng IS NOT NULL THEN 'Backfilled from the primary address coordinates.'
    WHEN project.city IS NOT NULL THEN 'City centroid should be resolved in the app layer.'
    ELSE 'No stored display geometry.'
  END
FROM (
  SELECT DISTINCT ON (project_id)
    project_id,
    lat,
    lng,
    location_confidence,
    geometry_source,
    normalized_address_text,
    address_text_raw,
    city
  FROM project_addresses
  ORDER BY project_id, is_primary DESC, created_at ASC
) address
WHERE project.id = address.project_id;

CREATE INDEX IF NOT EXISTS idx_project_master_display_geometry_type
  ON project_master (display_geometry_type, display_geometry_confidence);
CREATE INDEX IF NOT EXISTS idx_project_addresses_geocoding_status
  ON project_addresses (geocoding_status, location_confidence);
