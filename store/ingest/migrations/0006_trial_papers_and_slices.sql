-- Two tables the progressive load of trials needs (decided by the operator on 2026-11-17):
-- the papers found under a trial's number, and how far each slice of trials has come.
-- Both are new, so nothing held is rewritten and no row is written.
--
-- From here on store/schema.sql is the sum of these migrations, not a copy of the first:
-- migration 0001 is as it was applied and is never rewritten. `scripts/generate.mjs
-- --check` applies the migrations in order and holds what they make to store/schema.sql.

-- A paper a literature index lists under a trial's registry number. Kept once per trial,
-- index and paper, with the record as the index gave it (its payload) and when.
CREATE TABLE trial_paper (
  id              INTEGER PRIMARY KEY,
  trial_id        INTEGER NOT NULL REFERENCES registry_trial (id),
  source_name     TEXT NOT NULL,
  pubmed_id       TEXT NOT NULL,
  payload_sha256  TEXT NOT NULL REFERENCES payload (sha256),
  fetched_at      TEXT NOT NULL,
  added_run       TEXT NOT NULL REFERENCES run (id),
  changed_run     TEXT NOT NULL REFERENCES run (id),
  UNIQUE (trial_id, source_name, pubmed_id)
) STRICT;
CREATE INDEX ix_trial_paper_added_run ON trial_paper (added_run);

-- Trials are loaded a slice at a time: the trials one rule selects, of one year, in
-- numbered parts. A row says how far a slice has come, which is what the site's progress
-- reads. A stage is done when its time is set, and no merge takes a slice back a stage.
CREATE TABLE trial_slice (
  rule                TEXT NOT NULL,
  year                INTEGER NOT NULL,
  number              INTEGER NOT NULL,
  grp                 TEXT NOT NULL CHECK (grp IN ('ended with results', 'ended', 'active with results',
                        'active updated', 'active not updated')),
  trials              INTEGER NOT NULL CHECK (trials >= 0),
  with_results        INTEGER NOT NULL CHECK (with_results >= 0),
  registry_papers     INTEGER CHECK (registry_papers >= 0),
  pubmed_asked        INTEGER CHECK (pubmed_asked >= 0),
  pubmed_found        INTEGER CHECK (pubmed_found >= 0),
  in_store            INTEGER NOT NULL DEFAULT 0 CHECK (in_store >= 0),
  record_at           TEXT,
  registry_papers_at  TEXT,
  pubmed_papers_at    TEXT,
  in_store_at         TEXT,
  page_at             TEXT,
  changed_run         TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (rule, year, number)
) STRICT, WITHOUT ROWID;
