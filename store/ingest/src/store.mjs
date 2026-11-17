// The write path, as functions of the D1 binding: register a run, stage, merge, report,
// report without applying. No rule of the tracker is here. Every record enters the store
// by the statements of store/merge.sql, bundled unchanged (src/sql.generated.mjs) and sent
// as one D1 batch, which D1 applies as one transaction. The site's Worker can call these
// in-process for a reader's lookup; the HTTP routes in index.mjs are for everyone else.
import { INGEST, MERGE, PREVIEW } from "./sql.generated.mjs";
import { runChecksum } from "./hash.mjs";

const run1 = (db, sql, run) => db.prepare(sql).bind(...(sql.includes("?1") ? [run] : []));

// A time as the store keeps it, the one form every writer uses, because the merge
// compares times as text: UTC to the microsecond with its offset. A reader's lookup
// leaves only the day.
export const stamp = (date) => date.toISOString().slice(0, 23) + "000+00:00";
export const now = (lookup = false) => (lookup ? new Date().toISOString().slice(0, 10) : stamp(new Date()));

export async function getRun(db, id) {
  return db.prepare("SELECT id, writer, device, request_class, commit_sha, registered_at, stated_checksum, status, refusal, merged_at FROM run WHERE id = ?1").bind(id).first();
}

// What a run stated when it was registered: its steps and its counts.
export async function stated(db, id) {
  const [steps, counts] = await db.batch([
    db.prepare("SELECT step AS name, version AS n FROM run_step WHERE run_id = ?1").bind(id),
    db.prepare("SELECT kind AS name, records AS n FROM run_stated WHERE run_id = ?1").bind(id),
  ]);
  const object = ({ results }) => Object.fromEntries(results.map((row) => [row.name, row.n]));
  return { steps: object(steps), counts: object(counts) };
}

// A run is registered once, with its steps and counts. The caller has seen that no run
// has this id; one that is already there is not written to again (index.mjs).
export async function registerRun(db, run) {
  const lookup = run.writer === "lookup";
  await db.batch([
    db.prepare(INGEST.register_run).bind(run.id, run.writer, run.device ?? null, run.request_class ?? null, run.commit, now(lookup), run.checksum, null),
    db.prepare(INGEST.state_steps).bind(run.id, JSON.stringify(run.steps)),
    db.prepare(INGEST.state_counts).bind(run.id, JSON.stringify(run.counts)),
  ]);
  return getRun(db, run.id);
}

// Which of these claims the store already holds approved and released from audit.
export async function released(db, slugs) {
  const { results } = await db.prepare(
    "SELECT DISTINCT j.value AS slug FROM json_each(?1) j JOIN claim_key k ON k.slug = j.value JOIN claim c ON c.id = k.claim_id "
    + "WHERE c.review_state = 'approved' AND c.awaiting_audit_at IS NULL").bind(JSON.stringify(slugs)).all();
  return new Set(results.map((row) => row.slug));
}

// One chunk: its records and the note of its checksum, together or not at all. `text` is
// the JSON list written out again from the value the door checked, never the bytes that
// arrived: SQLite and JavaScript read a repeated key differently, so the bytes could say
// one thing to the door and another to the store. It is bound as one string. False when the run is not waiting for
// records: the statement stores nothing for a run never registered, merged or refused.
export async function stageChunk(db, run, text, checksum, records) {
  const [staged, noted] = await db.batch([
    db.prepare(INGEST.stage).bind(run, text),
    db.prepare("INSERT INTO ingest_chunk (run_id, sha256, records) SELECT id, ?2, ?3 FROM run WHERE id = ?1 AND status = 'registered' ON CONFLICT DO NOTHING").bind(run, checksum, records),
  ]);
  const waiting = await db.prepare("SELECT 1 AS ok FROM run WHERE id = ?1 AND status = 'registered'").bind(run).first();
  return { accepted: Boolean(waiting), staged: staged.meta.changes ?? 0, again: (noted.meta.changes ?? 0) === 0 };
}

// Whether the chunks that arrived are the ones the writer stated.
export async function checksumHolds(db, run) {
  const { results } = await db.prepare("SELECT sha256 FROM ingest_chunk WHERE run_id = ?1").bind(run.id).all();
  return (await runChecksum(results.map((row) => row.sha256))) === run.stated_checksum;
}

export async function report(db, id) {
  const { results } = await db.prepare(INGEST.report).bind(id).all();
  if (!results.length) return null;
  const kinds = {};
  for (const row of results) {
    if (row.kind) kinds[row.kind] = { resolved: row.resolved, added: row.added, conflicts: row.conflicts, matched: row.matched };
  }
  return { status: results[0].status, refusal: results[0].refusal, merged_at: results[0].merged_at, report: kinds };
}

const forget = (db, id) => db.prepare("DELETE FROM ingest_chunk WHERE run_id = ?1").bind(id);

// The merge: every statement of store/merge.sql, in order, as one batch. All of it or none.
//   merged       applied now, or before (`again`): the second time adds and changes nothing
//   refused      the merge refused the run (an older step version) and says why
//   undone       a statement failed, so D1 rolled the whole batch back; the run still waits
//   not_merged   the chunks that arrived are not the ones stated; nothing was tried
export async function merge(db, id) {
  const run = await getRun(db, id);
  if (!run) return null;
  if (run.status === "merged") return { ...(await report(db, id)), again: true };
  if (run.status === "registered") {
    if (!(await checksumHolds(db, run))) {
      return { status: "not_merged", reason: "checksum_mismatch", detail: "the records that arrived are not the ones the run stated", report: {} };
    }
    try {
      await db.batch(MERGE.map((sql) => run1(db, sql, id)));
    } catch (error) {
      return { status: "undone", ...why(error), report: {} };
    }
  }
  const after = await report(db, id);
  if (after.status === "refused") await db.batch([db.prepare(INGEST.discard_staged).bind(id), forget(db, id)]);
  else if (after.status === "merged") await forget(db, id).run();
  return { ...after, again: false };
}

// What undid a batch: the constraint SQLite names, never a value from a record.
function why(error) {
  const text = String(error?.message || error);
  if (text.includes("reconciled")) return { reason: "counts_do_not_reconcile", detail: "a record's parent is not in the store, or the records are not as many as the run stated" };
  const constraint = /(CHECK|FOREIGN KEY|UNIQUE|NOT NULL) constraint failed(: [A-Za-z0-9_.,()<>=' ]{0,200})?/.exec(text);
  return { reason: "constraint", detail: constraint ? constraint[0] : "a statement of the merge failed" };
}

// What the report without applying cannot see (design.md decision 10).
export const NOT_CHECKED = [
  "what only a CHECK or a foreign key refuses, such as a reader share with a time of day or a payload never handed over: the merge refuses those",
  "a run that names one claim by a present and a former slug for the same record, or whose actions depend on one another beyond a clear before a publication: the count is not exact for those",
];

// The report without the merge: store/preview.sql as one batch, which writes nothing that
// stays, then the run and what it staged are dropped, so the store is as it was.
export async function preview(db, id) {
  const run = await getRun(db, id);
  if (!run) return null;
  if (run.status !== "registered") return { status: run.status, previewed: false };
  const holds = await checksumHolds(db, run);
  const results = await db.batch(PREVIEW.map((sql) => run1(db, sql, id)));
  const kinds = {};
  let refusal = null, reconciles = true;
  const stated = [];
  for (const { results: rows } of results) {
    for (const row of rows || []) {
      if ("refusal" in row) refusal = row.refusal;
      else if ("stated" in row) stated.push(row);
      else kinds[row.kind] = { resolved: row.resolved, added: row.added, conflicts: row.conflicts, matched: row.resolved - row.added - row.conflicts };
    }
  }
  for (const row of stated) reconciles &&= row.stated === row.staged && row.staged === (kinds[row.kind]?.resolved ?? 0);
  await discard(db, id);
  return { status: "previewed", previewed: true, would_refuse: refusal, checksum_holds: holds, reconciles: reconciles && !refusal, report: refusal ? {} : kinds, not_checked: NOT_CHECKED };
}

// Drops a run that was never merged or refused, with what it staged.
export async function discard(db, id) {
  await db.batch([
    ...["discard_run", "discard_run_steps", "discard_run_counts"].map((name) => db.prepare(INGEST[name]).bind(id)),
    db.prepare("DELETE FROM ingest_chunk WHERE run_id = ?1 AND (SELECT status FROM run WHERE id = ?1) = 'registered'").bind(id),
    db.prepare(INGEST.discard_run_row).bind(id),
  ]);
}

// Which steps have work due, so the consumer can be woken once for each.
export async function dueSteps(db) {
  const { results } = await db.prepare("SELECT DISTINCT step FROM work_item WHERE state = 'due'").all();
  return results.map((row) => row.step);
}
