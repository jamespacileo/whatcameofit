// The write path, as functions of the D1 binding: register a run, stage, merge, report,
// report without applying. No rule of the tracker is here. Every record enters the store
// by the statements of store/merge.sql, bundled unchanged (src/sql.generated.mjs) and sent
// as one D1 batch, which D1 applies as one transaction. The site's Worker can call these
// in-process for a reader's lookup; the HTTP routes in index.mjs are for everyone else.
import { INGEST, MERGE, PREVIEW } from "./sql.generated.mjs";
import { runChecksum } from "./hash.mjs";
import { INBOX_KINDS } from "./kinds.mjs";

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

// The inbox of the bulk tier (migrations/0003_inbox.sql). It is for what a reader's lookup
// and the store-side consumer create (design.md decision 20): a device's, the daily job's
// and the operator's runs are pushes made on purpose, a slice of trials among them, and
// what they put in D1 stays there. A lookup's or the consumer's records of a bulk kind,
// and the payloads those records name, are copied as they were staged, in the batch of
// the merge and before it (the merge empties the staging table); a run the merge refused
// leaves none, and a batch that is undone leaves none either.
const BULK = INBOX_KINDS.map((kind) => `'${kind}'`).join(", ");
const KEEP = `INSERT INTO inbox (run_id, kind, key, body)
  SELECT s.run_id, s.kind, s.key, s.body FROM stg s
  WHERE s.run_id = ?1 AND (SELECT writer FROM run WHERE id = ?1) IN ('lookup', 'consumer') AND (s.kind IN (${BULK}) OR (s.kind = 'payload' AND s.body ->> 'sha256' IN (
    SELECT b.body ->> 'payload_sha256' FROM stg b WHERE b.run_id = ?1 AND b.kind IN (${BULK}))))
  ORDER BY s.kind = 'payload' DESC, s.rowid`;
const UNKEEP = "DELETE FROM inbox WHERE run_id = ?1 AND (SELECT status FROM run WHERE id = ?1) <> 'merged'";

// Up to `limit` records after `after`, oldest first, and no more than about 4 MB of them.
export async function inbox(db, after, limit) {
  const { results } = await db.prepare("SELECT seq, run_id AS run, kind, key, body FROM inbox WHERE seq > ?1 ORDER BY seq LIMIT ?2").bind(after, limit + 1).all();
  const records = [];
  let bytes = 0;
  for (const row of results.slice(0, limit)) {
    bytes += row.body.length;
    if (records.length && bytes > 4_000_000) break;
    records.push({ ...row, body: JSON.parse(row.body) });
  }
  return { records, through: records.at(-1)?.seq ?? after, more: results.length > records.length };
}

// A run is folded whole when its every inbox record is at or before ?1. It is noted in
// `inbox_folded` and stays there while a lead it added is still in D1.
const FOLDED = "(SELECT run_id FROM inbox_folded)";
// A folded run's leads, but not one the store-side consumer has yet to process: its
// work is read from D1, so it stays, with its shares and reading, until that is done.
const LEADS = `(SELECT l.id FROM link_lead l WHERE l.added_run IN ${FOLDED} AND NOT EXISTS (
  SELECT 1 FROM work_item w WHERE w.record_kind = 'link_lead' AND w.record_key = l.url_key AND w.step = 'lead_process' AND w.state = 'due'))`;
// A folded run's trials, but not one a paper has since been stored for: that trial is
// part of the load of trials now, and stays.
const TRIALS = `(SELECT t.id FROM registry_trial t WHERE t.added_run IN ${FOLDED} AND NOT EXISTS (SELECT 1 FROM trial_paper p WHERE p.trial_id = t.id))`;
// What folded runs left in D1's copies of the bulk tables, children first. A lead's
// shares, links, labels and reading go with it whichever run added them: a later run's
// are still in the inbox as records, and are folded from there.
const CLEAR = [
  "INSERT OR IGNORE INTO inbox_folded SELECT run_id FROM inbox WHERE seq <= ?1 EXCEPT SELECT run_id FROM inbox WHERE seq > ?1",
  "DELETE FROM inbox WHERE seq <= ?1",
  `DELETE FROM lead_reading WHERE link_lead_id IN ${LEADS}`,
  `DELETE FROM link_lead_label WHERE link_lead_id IN ${LEADS}`,
  `DELETE FROM link_lead_link WHERE link_lead_id IN ${LEADS}`,
  `DELETE FROM link_share WHERE link_lead_id IN ${LEADS}`,
  `DELETE FROM link_lead WHERE id IN ${LEADS}`,
  `DELETE FROM article_lead WHERE registry_trial_id IN ${TRIALS}`,
  `DELETE FROM registry_trial_status WHERE trial_id IN ${TRIALS}`,
  `DELETE FROM registry_trial WHERE id IN ${TRIALS}`,
  `DELETE FROM llm_usage WHERE run_id IN ${FOLDED}`,
  "DELETE FROM inbox_folded WHERE run_id NOT IN (SELECT added_run FROM link_lead)",
];

// How far the inbox may be cleared: the furthest fold recorded.
export async function foldedThrough(db) {
  return (await db.prepare("SELECT coalesce(max(through), 0) AS n FROM inbox_fold").first()).n;
}

// A fold is recorded once, by its delta object. `through` may not pass the last record
// the inbox ever gave: null when it does. The answer is what is recorded for the object,
// which for one recorded before is what was recorded then.
export async function recordFold(db, object, through, bytes) {
  const given = (await db.prepare("SELECT coalesce((SELECT seq FROM sqlite_sequence WHERE name = 'inbox'), 0) AS n").first()).n;
  if (through > given) return null;
  const done = await db.prepare("INSERT INTO inbox_fold (object, through, bytes, recorded_at) VALUES (?1, ?2, ?3, ?4) ON CONFLICT DO NOTHING").bind(object, through, bytes, now()).run();
  const row = await db.prepare("SELECT through, recorded_at FROM inbox_fold WHERE object = ?1").bind(object).first();
  return { recorded: row.through, recorded_at: row.recorded_at, again: (done.meta.changes ?? 0) === 0, folded_through: await foldedThrough(db) };
}

// Once the daily job has folded the records up to `through` into the bulk file: they
// leave the inbox, and the rows their runs added leave D1's copies of the bulk tables,
// but for a lead still waiting to be processed. One batch, so all of it or none.
export async function clearInbox(db, through) {
  const results = await db.batch(CLEAR.map((sql) => (sql.includes("?1") ? db.prepare(sql).bind(through) : db.prepare(sql))));
  const after = await db.prepare(`SELECT (SELECT count(*) FROM inbox) AS left, (SELECT count(*) FROM link_lead WHERE added_run IN ${FOLDED}) AS held`).first();
  return { cleared: results[1].meta.changes ?? 0, rows_removed: results.slice(2, -1).reduce((sum, result) => sum + (result.meta.changes ?? 0), 0), left: after.left, leads_held: after.held };
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
      await db.batch([db.prepare(KEEP).bind(id), ...MERGE.map((sql) => run1(db, sql, id)), db.prepare(UNKEEP).bind(id)]);
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
