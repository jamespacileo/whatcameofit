-- The ingest service's own table, not part of store/schema.sql: the inbox of the bulk
-- tier (design.md decision 20). The bulk kinds are not kept in D1; their truth is the
-- bulk file, whose one writer is the daily job. A record of a bulk kind that a run hands
-- over (a reader's lead, its share, its reading, a trial found for it) is kept here as it
-- was staged, in the same batch as the run's merge, until the daily job has read it,
-- folded it into the bulk file and cleared it.
CREATE TABLE inbox (
  seq    INTEGER PRIMARY KEY AUTOINCREMENT,   -- the order records arrived in; the reader's cursor
  run_id TEXT NOT NULL,
  kind   TEXT NOT NULL,
  key    TEXT NOT NULL,
  body   TEXT NOT NULL
) STRICT;
CREATE INDEX ix_inbox_run ON inbox (run_id);
