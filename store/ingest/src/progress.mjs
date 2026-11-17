// How far the backfill has come: what the pipeline reports of each slice of a set of
// trials, and what the store itself can count. Counts only.
import { Refusal } from "./check.mjs";
import { now } from "./store.mjs";

export const STAGES = ["record", "registry_papers", "pubmed_papers", "in_store", "page"];
const NAME = /^[A-Za-z0-9._-]{1,64}$/;
const TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$/;
const whole = (value) => Number.isInteger(value) && value >= 0 && value <= 100_000_000;
const bad = (message, detail) => { throw new Refusal(400, "bad_progress", message, detail); };

// A report of some slices of one set. A slice is added or brought up to date; a stage a
// report leaves out keeps the count it had.
export async function reportSlices(db, body) {
  if (!body || typeof body !== "object" || !NAME.test(body.set || "")) bad("set names the set of trials: letters, digits, ., - or _");
  if (!Array.isArray(body.slices) || body.slices.length > 200) bad("slices is a list of at most 200");
  for (const name of ["total_trials", "total_slices"]) if (body[name] != null && !whole(body[name])) bad(`${name} is a whole number`);
  const rows = body.slices.map((slice, at) => {
    const where = { slice: at };
    if (!slice || typeof slice !== "object" || !NAME.test(slice.slice || "")) bad("a slice has its own id: letters, digits, ., - or _", where);
    if (!whole(slice.position) || !whole(slice.trials)) bad("a slice has a position and how many trials it holds", where);
    const stages = slice.stages ?? {};
    if (typeof stages !== "object" || Array.isArray(stages)) bad("stages is an object of stage to count", where);
    for (const [stage, count] of Object.entries(stages)) {
      if (!STAGES.includes(stage)) bad(`a stage is one of ${STAGES.join(", ")}`, { ...where, stage: String(stage).slice(0, 40) });
      if (!whole(count) || count > slice.trials) bad("a stage's count is a whole number, at most the slice's trials", { ...where, stage });
    }
    for (const name of ["started_at", "updated_at"]) if (slice[name] != null && !TIME.test(slice[name])) bad(`${name} is a time as the store keeps it`, where);
    return [slice.slice, slice.position, slice.trials, ...STAGES.map((stage) => stages[stage] ?? null), slice.started_at ?? null, slice.updated_at ?? now()];
  });
  const upsert = `INSERT INTO progress_slice (set_name, slice, position, trials, ${STAGES.join(", ")}, started_at, updated_at)
    VALUES (?1, ?2, ?3, ?4, ${STAGES.map((_, n) => `coalesce(?${n + 5}, 0)`).join(", ")}, ?10, ?11)
    ON CONFLICT (set_name, slice) DO UPDATE SET position = excluded.position, trials = excluded.trials,
      ${STAGES.map((stage, n) => `${stage} = coalesce(?${n + 5}, progress_slice.${stage})`).join(", ")},
      started_at = coalesce(excluded.started_at, progress_slice.started_at), updated_at = excluded.updated_at`;
  await db.batch([
    db.prepare(`INSERT INTO progress_set (name, total_trials, total_slices, updated_at) VALUES (?1, ?2, ?3, ?4)
      ON CONFLICT (name) DO UPDATE SET total_trials = coalesce(excluded.total_trials, progress_set.total_trials),
        total_slices = coalesce(excluded.total_slices, progress_set.total_slices), updated_at = excluded.updated_at`).bind(body.set, body.total_trials ?? null, body.total_slices ?? null, now()),
    ...rows.map((row) => db.prepare(upsert).bind(body.set, ...row)),
  ]);
  const held = await db.prepare("SELECT count(*) AS n FROM progress_slice WHERE set_name = ?1").bind(body.set).first();
  return { set: body.set, slices: held.n };
}

// Everything the progress view shows: each set with its slices and totals by stage, the
// last merged run of each kind of writer, and how many rows each table of the store
// holds. Counts, slice ids and times; nothing of a record.
export async function progress(db) {
  const [sets, slices, runs, tables] = await db.batch([
    db.prepare("SELECT name, total_trials, total_slices, updated_at FROM progress_set ORDER BY name"),
    db.prepare(`SELECT set_name, slice, position, trials, ${STAGES.join(", ")}, started_at, updated_at FROM progress_slice ORDER BY set_name, position, slice`),
    db.prepare("SELECT writer, count(*) AS runs, max(merged_at) AS last_merged_at FROM run WHERE status = 'merged' GROUP BY writer ORDER BY writer"),
    db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%' AND name NOT LIKE 'd1_%' AND name NOT LIKE '%_fts%' ORDER BY name"),
  ]);
  const names = tables.results.map((row) => row.name).filter((name) => /^[a-z_0-9]+$/.test(name));
  // Ninety counts a statement at most: D1 answers no more than 100 columns.
  const rows = {};
  for (let at = 0; at < names.length; at += 90) {
    const part = names.slice(at, at + 90);
    Object.assign(rows, await db.prepare(`SELECT ${part.map((name) => `(SELECT count(*) FROM "${name}") AS "${name}"`).join(", ")}`).first());
  }
  return {
    stages: STAGES,
    sets: sets.results.map((set) => {
      const own = slices.results.filter((slice) => slice.set_name === set.name);
      const trials = own.reduce((sum, slice) => sum + slice.trials, 0);
      return {
        set: set.name, total_trials: set.total_trials, total_slices: set.total_slices, updated_at: set.updated_at,
        slices_reported: own.length, trials_reported: trials,
        totals: Object.fromEntries(STAGES.map((stage) => [stage, own.reduce((sum, slice) => sum + slice[stage], 0)])),
        slices: own.map((slice) => ({ slice: slice.slice, position: slice.position, trials: slice.trials,
          stages: Object.fromEntries(STAGES.map((stage) => [stage, slice[stage]])), started_at: slice.started_at, updated_at: slice.updated_at })),
      };
    }),
    runs: runs.results,
    rows,
    at: now(),
  };
}
