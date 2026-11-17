-- What the ingest service runs around a merge, and the store-side work queue and slices.
-- Fixed statements with numbered parameters; none of them writes a record of the tracker,
-- which only store/merge.sql does. Each begins with `-- name:` and ends at a lone `;`.

-- name: register_run
-- A run is registered once; registering it again changes nothing.
-- ?1 id, ?2 writer, ?3 device, ?4 request class, ?5 commit, ?6 time (a day for a lookup),
-- ?7 checksum of the records, ?8 Time Travel bookmark (for a run above the set size)
INSERT INTO run (id, writer, device, request_class, commit_sha, registered_at, stated_checksum, restore_bookmark)
VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
ON CONFLICT (id) DO NOTHING
;
-- name: state_steps
-- ?1 run, ?2 a JSON object of step -> version
INSERT INTO run_step (run_id, step, version)
SELECT ?1, key, value FROM json_each(?2) WHERE true
ON CONFLICT DO NOTHING
;
-- name: state_counts
-- ?1 run, ?2 a JSON object of kind -> records handed over
INSERT INTO run_stated (run_id, kind, records)
SELECT ?1, key, value FROM json_each(?2) WHERE true
ON CONFLICT DO NOTHING
;
-- name: stage
-- A chunk of records, as a JSON array of {kind, key, body}; a record without a key fails
-- the table's CHECK and the chunk with it. Records are staged only for a registered run,
-- and a record staged twice is kept once.
-- ?1 run, ?2 the array (under D1's 2 MB a string)
INSERT INTO stg (run_id, kind, key, body)
SELECT r.id, j.value ->> 'kind', j.value ->> 'key', j.value -> 'body'
FROM run r, json_each(?2) j
WHERE r.id = ?1 AND r.status = 'registered'
ON CONFLICT DO NOTHING
;
-- name: report
-- What a merge did, or would do: read after the batch, or after a batch that was undone
-- on purpose for `--report-only`.
SELECT r.status, r.refusal, r.merged_at, m.kind, m.resolved, m.added, m.conflicts,
       m.resolved - m.added - m.conflicts AS matched
FROM run r LEFT JOIN merge_report m ON m.run_id = r.id
WHERE r.id = ?1
;
-- name: discard_run
-- After a report without applying (store/preview.sql): the run and what it staged are
-- dropped, so the store is as it was. A run that was merged or refused is kept.
-- Four statements, sent as one batch; ?1 run
DELETE FROM stg WHERE run_id = ?1 AND (SELECT status FROM run WHERE id = ?1) = 'registered'
;
-- name: discard_run_steps
DELETE FROM run_step WHERE run_id = ?1 AND (SELECT status FROM run WHERE id = ?1) = 'registered'
;
-- name: discard_run_counts
DELETE FROM run_stated WHERE run_id = ?1 AND (SELECT status FROM run WHERE id = ?1) = 'registered'
;
-- name: discard_run_row
DELETE FROM run WHERE id = ?1 AND status = 'registered'
;
-- name: discard_staged
-- A refused run's staged records are dropped.
DELETE FROM stg WHERE run_id = ?1 AND (SELECT status FROM run WHERE id = ?1) <> 'registered'
;

-- name: lease_work
-- Up to ?2 due items of one step are taken for a time, oldest first; an item whose lease
-- lapsed is taken again; two consumers asking at once get different items, D1 running one
-- statement at a time.
-- ?1 step, ?2 how many, ?3 now, ?4 lease end
UPDATE work_item SET lease_until = ?4, attempts = attempts + 1
WHERE (record_kind, record_key, step) IN (
  SELECT record_kind, record_key, step FROM work_item
  WHERE step = ?1 AND state = 'due' AND (lease_until IS NULL OR lease_until < ?3)
  ORDER BY due_since LIMIT ?2)
RETURNING record_kind, record_key, attempts
;
-- name: finish_work
-- ?1 kind, ?2 key, ?3 step
UPDATE work_item SET state = 'done', lease_until = NULL, error = NULL
WHERE record_kind = ?1 AND record_key = ?2 AND step = ?3
;
-- name: fail_work
-- A failed item is due again until it has been tried ?5 times, then left with its error.
-- ?1 kind, ?2 key, ?3 step, ?4 the kind of error, ?5 the most attempts
UPDATE work_item SET state = CASE WHEN attempts >= ?5 THEN 'failed' ELSE 'due' END,
                     lease_until = NULL, error = ?4
WHERE record_kind = ?1 AND record_key = ?2 AND step = ?3
;

-- name: take_slice
-- A slice is given to a device when it is free, lapsed or already that device's, and never
-- when a run has finished it; RETURNING is empty for the device that was refused.
-- ?1 platform, ?2 community, ?3 month, ?4 device, ?5 now, ?6 lapse time
INSERT INTO work_slice (platform, community, month, device, taken_at, lapses_at)
VALUES (?1, ?2, ?3, ?4, ?5, ?6)
ON CONFLICT (platform, community, month) DO UPDATE SET
  device = excluded.device, taken_at = excluded.taken_at, lapses_at = excluded.lapses_at
WHERE work_slice.done_run IS NULL
  AND (work_slice.device IS NULL OR work_slice.device = excluded.device OR work_slice.lapses_at < excluded.taken_at)
RETURNING device
;
-- name: release_slice
-- ?1 platform, ?2 community, ?3 month, ?4 device
UPDATE work_slice SET device = NULL, taken_at = NULL, lapses_at = NULL
WHERE platform = ?1 AND community = ?2 AND month = ?3 AND device = ?4 AND done_run IS NULL
;
