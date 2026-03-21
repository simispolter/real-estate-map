CREATE TYPE value_origin_type_enum AS ENUM ('reported', 'inferred', 'unknown');

ALTER TABLE field_provenance
ADD COLUMN value_origin_type value_origin_type_enum NOT NULL DEFAULT 'reported';

UPDATE field_provenance
SET value_origin_type = CASE
  WHEN normalized_value IS NULL THEN 'unknown'::value_origin_type_enum
  ELSE 'reported'::value_origin_type_enum
END;
