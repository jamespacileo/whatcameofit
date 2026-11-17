// How far the backfill has come: what the pipeline reports of each slice of a set of
// trials, and what the store itself can count. Counts, a group's name and times only.
import { Refusal } from "./check.mjs";
import { now } from "./store.mjs";

// A stage is reached when its time is set.
export const STAGES = ["record", "registry_papers", "pubmed_papers", "in_store", "page"];
export const GROUPS = ["ended with results", "ended", "active with results", "active updated", "active not updated"];
const COUNTS = ["with_results", "registry_papers", "pubmed_asked", "pubmed_found", "in_store"];
const TIMES = STAGES.map((stage) => `${stage}_at`);
const NAME = /^[A-Za-z0-9._-]{1,64}$/;
const TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$/;
const whole = (value) => Number.isInteger(value) && value >= 0 && value <= 100_000_000;
const bad = (message, detail) => { throw new Refusal(400, "bad_progress", message, detail); };

// A report of some slices of one set. A slice is added or brought up to date, and a stage
// never goes back: the larger count and the later time are kept, and what a report
// leaves out stays as it was.
export async function reportSlices(db, body) {
  if (!body || typeof body !== "object" || !NAME.test(body.rule || "")) bad("rule names the set of trials: letters, digits, ., - or _");
  if (!Number.isInteger(body.year) || body.year < 2000 || body.year > 2100) bad("year is the year the rule was chosen in");
  if (!Array.isArray(body.slices) || body.slices.length > 200) bad("slices is a list of at most 200");
  for (const name of ["total_trials", "total_slices"]) if (body[name] != null && !whole(body[name])) bad(`${name} is a whole number`);
  const known = new Set(["number", "grp", "trials", ...COUNTS, ...TIMES]);
  const rows = body.slices.map((slice, at) => {
    const where = { slice: at };
    if (!slice || typeof slice !== "object" || Array.isArray(slice)) bad("a slice is an object", where);
    const extra = Object.keys(slice).find((name) => !known.has(name));
    if (extra !== undefined) bad("a slice holds its number, group, counts and times, and nothing else", { ...where, field: String(extra).slice(0, 40) });
    if (!whole(slice.number) || slice.number < 1 || !whole(slice.trials)) bad("a slice has its number, from 1, and how many trials it holds", where);
    if (!GROUPS.includes(slice.grp)) bad(`a slice's group is one of: ${GROUPS.join("; ")}`, where);
    for (const name of COUNTS) if (slice[name] != null && (!whole(slice[name]) || slice[name] > slice.trials)) bad("a count is a whole number, at most the slice's trials", { ...where, field: name });
    for (const name of TIMES) if (slice[name] != null && !TIME.test(slice[name])) bad("a time is as the store keeps it", { ...where, field: name });
    return [slice.number, slice.grp, slice.trials, ...COUNTS.map((name) => slice[name] ?? null), ...TIMES.map((name) => slice[name] ?? null)];
  });
  const columns = ["rule", "year", "number", "grp", "trials", ...COUNTS, ...TIMES, "updated_at"];
  const later = (name) => `${name} = CASE WHEN excluded.${name} IS NULL THEN progress_slice.${name} WHEN progress_slice.${name} IS NULL THEN excluded.${name} ELSE max(progress_slice.${name}, excluded.${name}) END`;
  const upsert = `INSERT INTO progress_slice (${columns.join(", ")})
    VALUES (${columns.map((name, n) => (name === "in_store" ? `coalesce(?${n + 1}, 0)` : `?${n + 1}`)).join(", ")})
    ON CONFLICT (rule, year, number) DO UPDATE SET grp = excluded.grp, trials = excluded.trials,
      ${[...COUNTS.filter((name) => name !== "in_store"), ...TIMES].map(later).join(", ")},
      in_store = max(progress_slice.in_store, excluded.in_store), updated_at = excluded.updated_at`;
  const at = now();
  await db.batch([
    db.prepare(`INSERT INTO progress_set (rule, year, total_trials, total_slices, updated_at) VALUES (?1, ?2, ?3, ?4, ?5)
      ON CONFLICT (rule, year) DO UPDATE SET total_trials = coalesce(excluded.total_trials, progress_set.total_trials),
        total_slices = coalesce(excluded.total_slices, progress_set.total_slices), updated_at = excluded.updated_at`).bind(body.rule, body.year, body.total_trials ?? null, body.total_slices ?? null, at),
    ...rows.map((row) => db.prepare(upsert).bind(body.rule, body.year, ...row, at)),
  ]);
  const held = await db.prepare("SELECT count(*) AS n FROM progress_slice WHERE rule = ?1 AND year = ?2").bind(body.rule, body.year).first();
  return { rule: body.rule, year: body.year, slices: held.n };
}

// Everything the progress view shows: each set with its slices, how many slices and
// trials have reached each stage, the same by group, the last merged run of each kind of
// writer, and how many rows each table of the store holds. Nothing of a record.
export async function progress(db) {
  const [sets, slices, runs, tables] = await db.batch([
    db.prepare("SELECT rule, year, total_trials, total_slices, updated_at FROM progress_set ORDER BY year DESC, rule"),
    db.prepare(`SELECT rule, year, number, grp, trials, ${COUNTS.join(", ")}, ${TIMES.join(", ")}, updated_at FROM progress_slice ORDER BY year DESC, rule, number`),
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
  const sum = (list, name) => list.reduce((total, one) => total + (one[name] ?? 0), 0);
  return {
    stages: STAGES,
    groups: GROUPS,
    sets: sets.results.map((set) => {
      const own = slices.results.filter((slice) => slice.rule === set.rule && slice.year === set.year);
      const reached = (stage, list = own) => list.filter((slice) => slice[`${stage}_at`] != null);
      return {
        rule: set.rule, year: set.year, total_trials: set.total_trials, total_slices: set.total_slices, updated_at: set.updated_at,
        slices_reported: own.length, trials_reported: sum(own, "trials"),
        // For each stage: the slices that have reached it and the trials those slices hold.
        stages: Object.fromEntries(STAGES.map((stage) => [stage, { slices: reached(stage).length, trials: sum(reached(stage), "trials") }])),
        counts: Object.fromEntries(COUNTS.map((name) => [name, sum(own, name)])),
        groups: GROUPS.map((grp) => { const list = own.filter((slice) => slice.grp === grp); return { grp, slices: list.length, trials: sum(list, "trials"), in_store: sum(list, "in_store") }; }).filter((group) => group.slices),
        slices: own.map(({ rule, year, ...slice }) => slice),
      };
    }),
    runs: runs.results,
    rows,
    at: now(),
  };
}
