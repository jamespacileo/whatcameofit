-- rebuilds: work_entry
-- The wider outcome check requires a table rebuild. No table references work_entry.
ALTER TABLE work_entry RENAME TO old_work_entry;
CREATE TABLE work_entry (
  record_kind      TEXT NOT NULL,
  record_key       TEXT NOT NULL,
  step             TEXT NOT NULL,
  step_version     INTEGER NOT NULL,
  outcome          TEXT NOT NULL CHECK (outcome IN ('done', 'nothing_found', 'later', 'needs_fix', 'failed')),
  reason           TEXT,
  reason_values    TEXT CHECK (reason_values IS NULL OR json_type(reason_values) = 'object'),
  not_before       TEXT,
  first_put_off_at TEXT,
  attempts         INTEGER NOT NULL CHECK (attempts >= 0),
  requests_used    INTEGER NOT NULL CHECK (requests_used >= 0),
  fingerprint      TEXT NOT NULL,
  stale            INTEGER NOT NULL DEFAULT 0 CHECK (stale IN (0, 1)),
  error            TEXT,
  last_attempt_at  TEXT NOT NULL,
  changed_run      TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (record_kind, record_key, step, step_version),
  CHECK ((outcome = 'later') = (not_before IS NOT NULL)),
  CHECK (outcome NOT IN ('later', 'needs_fix') OR reason IS NOT NULL),
  CHECK ((outcome = 'failed') = (error IS NOT NULL))
) STRICT, WITHOUT ROWID;
INSERT INTO work_entry (record_kind, record_key, step, step_version, outcome, attempts,
                        requests_used, fingerprint, stale, error, last_attempt_at, changed_run)
SELECT record_kind, record_key, step, step_version, outcome, attempts,
       requests_used, fingerprint, stale, error, last_attempt_at, changed_run
FROM old_work_entry;
DROP TABLE old_work_entry;
