ALTER TABLE project_addresses
    ADD COLUMN IF NOT EXISTS parcel_block TEXT,
    ADD COLUMN IF NOT EXISTS parcel_number TEXT,
    ADD COLUMN IF NOT EXISTS sub_parcel TEXT,
    ADD COLUMN IF NOT EXISTS address_note TEXT;

CREATE INDEX IF NOT EXISTS idx_project_addresses_city_street_lookup
    ON project_addresses (normalized_city, normalized_street);

CREATE INDEX IF NOT EXISTS idx_project_addresses_parcel_lookup
    ON project_addresses (city, parcel_block, parcel_number);
