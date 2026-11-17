-- rebuilds: payload
--
-- FOR AN EMPTY STORE ONLY. Applied to the loaded preview database on 2026-11-17 it ran
-- 38 seconds and was stopped: "D1 DB exceeded its CPU time limit and was reset" (code
-- 7429). Nothing was lost. A migration is one transaction, and one transaction over a
-- whole loaded table does not finish on D1; D1's local engine has no such limit, which
-- is why the test of this file on a loaded local database passes. The cut-over empties
-- or replaces a store before migrations and refuses this one while the store holds rows
-- (the line above is how it knows).
--
-- A payload of up to 524,288 bytes is kept in its row; the bound was 16,384 characters.
-- Decided on 2026-11-17 after the first cut-over to the preview: 3,211 payloads went to R2
-- one object at a time and took 659 of its 810 seconds; at this bound about 37 do.
--
-- SQLite cannot change a CHECK, so the table is made again. Other tables reference it by
-- name, and a rename would take their references with it, so the new table must be made
-- under the same name: the rows are copied aside, the table is dropped and made again
-- with the new bound, and the rows are copied back. Foreign keys are deferred meanwhile
-- (D1 documents the pragma for this and checks when the transaction ends); by then every
-- row that was referenced is there again, so nothing is unmet. No row that references a
-- payload is touched.
--
-- Two other ways were tried on D1's local engine on 2026-11-17, with rows referencing the
-- table, and both were refused and rolled back whole: dropping the table and renaming a
-- copy into its place, and renaming the table aside with `legacy_alter_table`.
--
-- Each copy is in sixteen statements, one for each first digit of the checksum. That
-- keeps a statement short and does not help the transaction, which is what D1 limits.
-- On an empty database it writes no row.
--
-- The next change of this kind is not to be written this way: copy in batches across
-- several migrations, each a small transaction, or design it so the table need not be
-- made again (a bound held by a trigger can be changed by dropping the trigger).
PRAGMA defer_foreign_keys = on;
CREATE TABLE payload_aside (
  sha256     TEXT PRIMARY KEY,
  bytes      INTEGER NOT NULL,
  body       TEXT,
  r2_key     TEXT,
  added_run  TEXT NOT NULL
) STRICT;
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 < '1';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '1' AND sha256 < '2';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '2' AND sha256 < '3';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '3' AND sha256 < '4';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '4' AND sha256 < '5';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '5' AND sha256 < '6';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '6' AND sha256 < '7';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '7' AND sha256 < '8';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '8' AND sha256 < '9';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= '9' AND sha256 < 'a';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= 'a' AND sha256 < 'b';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= 'b' AND sha256 < 'c';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= 'c' AND sha256 < 'd';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= 'd' AND sha256 < 'e';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= 'e' AND sha256 < 'f';
INSERT INTO payload_aside (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload WHERE sha256 >= 'f';
DROP TABLE payload;
CREATE TABLE payload (
  sha256     TEXT PRIMARY KEY CHECK (length(sha256) = 64),
  bytes      INTEGER NOT NULL CHECK (bytes > 0),
  body       TEXT CHECK (body IS NULL OR length(CAST(body AS BLOB)) <= 524288),
  r2_key     TEXT,
  added_run  TEXT NOT NULL REFERENCES run (id),
  CHECK ((body IS NULL) <> (r2_key IS NULL))
) STRICT;
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 < '1';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '1' AND sha256 < '2';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '2' AND sha256 < '3';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '3' AND sha256 < '4';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '4' AND sha256 < '5';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '5' AND sha256 < '6';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '6' AND sha256 < '7';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '7' AND sha256 < '8';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '8' AND sha256 < '9';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= '9' AND sha256 < 'a';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= 'a' AND sha256 < 'b';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= 'b' AND sha256 < 'c';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= 'c' AND sha256 < 'd';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= 'd' AND sha256 < 'e';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= 'e' AND sha256 < 'f';
INSERT INTO payload (sha256, bytes, body, r2_key, added_run) SELECT sha256, bytes, body, r2_key, added_run FROM payload_aside WHERE sha256 >= 'f';
DROP TABLE payload_aside;
CREATE INDEX ix_payload_added_run ON payload (added_run);
