-- The ingest service's own bookkeeping. Not a record of the tracker and not part of
-- store/schema.sql: only the service reads or writes it.
--
-- One row for each chunk of records a run handed over, written in the same batch as the
-- chunk's records, so the two are stored together or not at all. Before a merge the
-- service makes the run's checksum from these and holds it to the one the writer stated
-- (`run.stated_checksum`). The rows go when the run is merged, refused or dropped.
CREATE TABLE ingest_chunk (
  run_id   TEXT NOT NULL,
  sha256   TEXT NOT NULL CHECK (length(sha256) = 64),
  records  INTEGER NOT NULL CHECK (records >= 0),
  PRIMARY KEY (run_id, sha256)
) STRICT, WITHOUT ROWID;
