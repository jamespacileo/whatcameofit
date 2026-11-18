ALTER TABLE claim ADD COLUMN registry_candidate_trial_ids TEXT NOT NULL DEFAULT '[]' CHECK (json_type(registry_candidate_trial_ids) = 'array');
