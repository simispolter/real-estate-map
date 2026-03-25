ALTER TABLE staging_project_candidates
ADD COLUMN IF NOT EXISTS candidate_quality_score NUMERIC(5,2);

ALTER TABLE staging_project_candidates
ADD COLUMN IF NOT EXISTS family_confidence_score NUMERIC(5,2);
