-- The ingest service's own tables: how far the backfill of a set of trials has come, as
-- the pipeline reports it, slice by slice. Counts and a slice's own id only: no trial, no
-- registry number, no text of a record.
CREATE TABLE progress_set (
  name         TEXT PRIMARY KEY,
  total_trials INTEGER,
  total_slices INTEGER,
  updated_at   TEXT NOT NULL
) STRICT;
CREATE TABLE progress_slice (
  set_name        TEXT NOT NULL REFERENCES progress_set (name),
  slice           TEXT NOT NULL,
  position        INTEGER NOT NULL,
  trials          INTEGER NOT NULL CHECK (trials >= 0),
  record          INTEGER NOT NULL DEFAULT 0,
  registry_papers INTEGER NOT NULL DEFAULT 0,
  pubmed_papers   INTEGER NOT NULL DEFAULT 0,
  in_store        INTEGER NOT NULL DEFAULT 0,
  page            INTEGER NOT NULL DEFAULT 0,
  started_at      TEXT,
  updated_at      TEXT NOT NULL,
  PRIMARY KEY (set_name, slice)
) STRICT;
