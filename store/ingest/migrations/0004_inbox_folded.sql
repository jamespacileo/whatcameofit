-- The ingest service's own table: runs whose inbox records the daily job has folded into
-- the bulk file, while a row they added to D1's copies of the bulk tables is still there.
-- A lead is held back when the store-side consumer has not yet processed it; the run is
-- remembered here so that a later clearing removes the lead once its work is done.
CREATE TABLE inbox_folded (
  run_id TEXT PRIMARY KEY
) STRICT;
