// How far the load of trials has come, read from the store: `trial_slice`, the one record
// of each slice's state, written only by the merge, and what the store itself can count.
// Counts, a group's name and times only; nothing of a record, no trial.
import { now } from "./store.mjs";

// A stage is reached when its time is set.
export const STAGES = ["record", "registry_papers", "pubmed_papers", "in_store", "page"];
export const GROUPS = ["ended with results", "ended", "active with results", "active updated", "active not updated"];
const COUNTS = ["with_results", "registry_papers", "pubmed_asked", "pubmed_found", "in_store"];
const TIMES = STAGES.map((stage) => `${stage}_at`);

// Everything the progress view shows: each set (a rule and the year it was chosen in)
// with its slices, how many slices and trials have reached each stage, the same by group,
// the last merged run of each kind of writer, and the rows each table of the store holds.
// A set's totals are its slices': the pipeline hands every planned slice over, reached or not.
export async function progress(db) {
  const [slices, runs, tables] = await db.batch([
    db.prepare(`SELECT s.rule, s.year, s.number, s.grp, s.trials, ${COUNTS.map((name) => `s.${name}`).join(", ")}, ${TIMES.map((name) => `s.${name}`).join(", ")}, r.merged_at AS changed_at
      FROM trial_slice s LEFT JOIN run r ON r.id = s.changed_run ORDER BY s.year DESC, s.rule, s.number`),
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
  const sets = new Map();
  for (const slice of slices.results) {
    const key = `${slice.rule}\n${slice.year}`;
    if (!sets.has(key)) sets.set(key, []);
    sets.get(key).push(slice);
  }
  return {
    stages: STAGES,
    groups: GROUPS,
    sets: [...sets.values()].map((own) => {
      const reached = (stage) => own.filter((slice) => slice[`${stage}_at`] != null);
      return {
        rule: own[0].rule, year: own[0].year, total_slices: own.length, total_trials: sum(own, "trials"),
        changed_at: own.map((slice) => slice.changed_at).filter(Boolean).sort().at(-1) ?? null,
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
