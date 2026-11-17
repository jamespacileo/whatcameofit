-- The ingest service's own table: each fold of the inbox the daily job has recorded, with
-- the delta object in the bucket that holds what was folded. The inbox is cleared no
-- further than the furthest fold recorded here, and a fold is recorded only when its
-- delta object is in the bucket, so no record leaves D1 before it is safe in R2.
CREATE TABLE inbox_fold (
  object      TEXT PRIMARY KEY,     -- bulk/<build id>/delta-...
  through     INTEGER NOT NULL,     -- the last inbox record the delta holds
  bytes       INTEGER NOT NULL,     -- the object's size when it was recorded
  recorded_at TEXT NOT NULL
) STRICT;
