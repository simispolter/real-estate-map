CREATE TABLE IF NOT EXISTS project_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project_master(id) ON DELETE CASCADE,
  alias_name TEXT NOT NULL,
  value_origin_type value_origin_type_enum NOT NULL DEFAULT 'manual',
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_project_aliases_project_alias UNIQUE (project_id, alias_name)
);

CREATE INDEX IF NOT EXISTS idx_project_aliases_project_id ON project_aliases (project_id);

ALTER TABLE project_snapshots
  ADD COLUMN IF NOT EXISTS notes_internal TEXT;

DROP TRIGGER IF EXISTS trg_project_aliases_updated_at ON project_aliases;
CREATE TRIGGER trg_project_aliases_updated_at
BEFORE UPDATE ON project_aliases
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
