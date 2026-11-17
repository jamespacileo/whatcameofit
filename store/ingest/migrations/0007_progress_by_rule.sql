-- The progress tables in the shape the pipeline plans slices in: a set is a rule and the
-- year it was chosen in, a slice is a number within it, and each stage has a count and
-- the time it was reached. The first shape (0006) held nothing yet. Counts, a group's
-- name and times only: no trial, no registry number, no text of a record.
DROP TABLE IF EXISTS progress_slice;
DROP TABLE IF EXISTS progress_set;
CREATE TABLE progress_set (
  rule         TEXT NOT NULL,
  year         INTEGER NOT NULL,
  total_trials INTEGER,
  total_slices INTEGER,
  updated_at   TEXT NOT NULL,
  PRIMARY KEY (rule, year)
) STRICT;
CREATE TABLE progress_slice (
  rule               TEXT NOT NULL,
  year               INTEGER NOT NULL,
  number             INTEGER NOT NULL,     -- the order of loading, 1..N
  grp                TEXT NOT NULL,
  trials             INTEGER NOT NULL CHECK (trials >= 0),
  with_results       INTEGER,
  registry_papers    INTEGER,              -- trials with a paper the registry lists; NULL until that stage ran
  pubmed_asked       INTEGER,
  pubmed_found       INTEGER,
  in_store           INTEGER NOT NULL DEFAULT 0,
  record_at          TEXT,
  registry_papers_at TEXT,
  pubmed_papers_at   TEXT,
  in_store_at        TEXT,
  page_at            TEXT,
  updated_at         TEXT NOT NULL,
  PRIMARY KEY (rule, year, number),
  FOREIGN KEY (rule, year) REFERENCES progress_set (rule, year)
) STRICT;
