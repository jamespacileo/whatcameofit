ALTER TABLE claim ADD COLUMN drafted_from TEXT CHECK (drafted_from IN ('article', 'registry', 'operator'));
ALTER TABLE claim ADD COLUMN drafting_trial_ids TEXT NOT NULL DEFAULT '[]' CHECK (
  json_type(drafting_trial_ids) = 'array'
  AND (drafted_from IS 'registry') = (json_array_length(drafting_trial_ids) > 0));
