// A pair's trials as a table (openspec pairs-site, shared components; DESIGN.md, "Trials
// table"): grouped, trials that posted results first whatever their phase, then by the
// furthest phase each reached, furthest first, then those with no phase. A row gives the
// trial, how many people, its phase, its state and whether it posted results, and opens to its
// record. Built from the pair's own trial views: nothing here says how a trial turned out, a
// phase is only ever named ("Phase 4" is a study after approval, not an approval: the lab
// tracks no regulator's decision), and no colour marks a state.
import { escape } from "./blocks.ts";
import { trialRecord } from "./pair-render.ts";
import type { PairTrialView } from "./pair-view.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";

/** The phases, earliest first; a combined trial ("Phase 2 and Phase 3") is placed by its furthest. */
const PHASE_ORDER = ["early_phase_1", "phase_1", "phase_2", "phase_3", "phase_4"];

/** Each group's heading, by key. */
export const TRIAL_GROUPS: Record<string, string> = {
  results: "Results posted",
  phase_4: "Phase 4",
  phase_3: "Phase 3",
  phase_2: "Phase 2",
  phase_1: "Phase 1",
  early_phase_1: "Early Phase 1",
  none: "No phase given",
};

const COLUMNS = ["Trial", "People", "Phase", "State", "Results"];
const NOT_GIVEN = "Not given";
const NOT_STATED = "Not stated";

assertNoOutcomeVerdict([...Object.values(TRIAL_GROUPS), ...COLUMNS, NOT_GIVEN, NOT_STATED, "Posted", "None posted", "Its record"]);
for (const words of Object.values(TRIAL_GROUPS)) {
  if (/approv/i.test(words)) throw new Error(`a trial group is worded as an approval: ${words}`);
}

/** The group a trial falls in. */
export function trialGroup(trial: PairTrialView): string {
  if (trial.resultsPosted) return "results";
  const furthest = Math.max(-1, ...trial.phaseCodes.map((code) => PHASE_ORDER.indexOf(code)));
  return furthest < 0 ? "none" : PHASE_ORDER[furthest];
}

/** The trials in their groups, in the order the table shows them. */
export function trialGroups(trials: PairTrialView[]): { key: string; label: string; trials: PairTrialView[] }[] {
  const order = ["results", ...[...PHASE_ORDER].reverse(), "none"];
  return order
    .map((key) => ({ key, label: TRIAL_GROUPS[key], trials: trials.filter((trial) => trialGroup(trial) === key) }))
    .filter((group) => group.trials.length > 0);
}

const count = (n: number) => (n === 1 ? "1 trial" : `${n} trials`);

/** One trial's row, and the row under it that opens to its record. */
function trialRows(trial: PairTrialView): string {
  const cell = (label: string, html: string) => `<td data-label="${escape(label)}">${html}</td>`;
  return [
    `<tr data-trial="${escape(trial.nctId)}">`,
    `<th scope="row" data-label="Trial"><a href="${escape(trial.registryUrl)}" rel="external">${escape(trial.nctId)}</a>`,
    trial.title ? `<span class="trials-title">${escape(trial.title)}</span>` : "",
    `</th>`,
    cell("People", escape(trial.participants ?? NOT_STATED)),
    cell("Phase", escape(trial.phases ?? NOT_GIVEN)),
    cell("State", escape(trial.state)),
    cell("Results", trial.resultsPosted ? "Posted" : "None posted"),
    `</tr>`,
    `<tr class="trials-record"><td colspan="${COLUMNS.length}"><details><summary>Its record</summary>${trialRecord(trial)}</details></td></tr>`,
  ].join("");
}

/** The trials table: each group's heading with its count, then its rows. */
export function trialsTable(trials: PairTrialView[]): string {
  if (trials.length === 0) return `<p>No trial is on record for this pair.</p>`;
  return trialGroups(trials)
    .map((group) =>
      [
        `<section class="trials-group" data-trials-group="${escape(group.key)}">`,
        `<h3 class="trials-group-head">${escape(group.label)} <span class="count">${escape(count(group.trials.length))}</span></h3>`,
        `<table class="trials-table"><thead><tr>${COLUMNS.map((name) => `<th scope="col">${escape(name)}</th>`).join("")}</tr></thead><tbody>`,
        ...group.trials.map(trialRows),
        `</tbody></table></section>`,
      ].join(""),
    )
    .join("");
}
