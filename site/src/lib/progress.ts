// "Progress on record": how far a pair's testing has gone on the public record, as one of
// five steps, with the caution facts that are always shown beside it.
//
// The operator chose this on 2026-11-21 (docs/adr/0015): a level by progress only, from
// registry dates and events, never from what a result says. The step is the furthest of the
// five for which a record exists, so it cannot rise because a figure looked favourable, and
// a refusal would reach the last step as an approval does. The ladder follows Open Targets'
// clinical stage ladder (https://platform-docs.opentargets.org/evidence), without its score
// and without its halving for trials stopped for negative reasons, which needs a model to
// read the reason. The caution facts follow the FDAAA TrialsTracker's dated reporting facts
// (https://fdaaa.trialstracker.net) and are worded as facts, never as a breach.
//
// One pure function over a pair's page file. No model, nothing read from free text.

/** The five steps, in order. A pair with no trial on record has no step. */
export const PROGRESS_STEPS = ["registered", "started", "finished", "results", "regulator"] as const;
export type ProgressStep = (typeof PROGRESS_STEPS)[number];

export interface ProgressReason {
  /** The trial whose record put the pair on this step; null for the regulator's step. */
  nctId: string | null;
  /** The record's day, as the registry gives it, where the step comes from a dated event. */
  day: string | null;
  /** The event's key in the page file, where there is one, so the page can point at it. */
  eventKey: string | null;
}

export type Caution =
  /** A trial the registry says was stopped, suspended or withdrawn, with its stated reason. */
  | { kind: "ended_early"; nctId: string; state: string; reason: string | null }
  /** A trial with no results on the registry a year after its primary completion (`DueCode`). */
  | { kind: "no_results"; nctId: string; asOf: string; days: number }
  /** The pair's status is a retraction. */
  | { kind: "retracted" };

export interface Progress {
  step: ProgressStep;
  /** 1 to 5. */
  place: number;
  reason: ProgressReason;
  cautions: Caution[];
}

/** The registry's states of a trial that ended before it finished, or never began. */
const ENDED_EARLY = ["terminated", "suspended", "withdrawn"];

const recorded = (event: any) => event.day_basis !== "registry_date_estimated";

/** The earliest recorded event of a kind across the pair's trials, or null. */
function earliest(trials: any[], kind: string): ProgressReason | null {
  const found = trials
    .flatMap((trial) => trial.events.filter((event: any) => event.kind === kind && recorded(event)))
    .sort((a: any, b: any) => (a.day < b.day ? -1 : a.day > b.day ? 1 : 0))[0];
  return found ? { nctId: found.nct_id, day: found.day, eventKey: found.key } : null;
}

/** A trial whose record holds the fact without a dated event for it. */
function held(trials: any[], holds: (trial: any) => boolean): ProgressReason | null {
  const trial = trials.find(holds);
  return trial ? { nctId: trial.nct_id, day: null, eventKey: null } : null;
}

/** Where a pair's page file puts it, and the caution facts of its trials. Null with no trial. */
export function progressOf(page: any): Progress | null {
  const trials: any[] = page.trials;
  if (trials.length === 0) return null;
  const code: string = page.row.status.code;
  // Furthest first. Each step asks only whether a record exists.
  const reached: [ProgressStep, ProgressReason | null][] = [
    // The bundle's one regulator code is an approval; it carries no refusal yet (ADR 0015, known defects).
    ["regulator", code === "approved" ? { nctId: null, day: null, eventKey: null } : null],
    [
      "results",
      earliest(trials, "results_posted") ??
        held(trials, (trial) => Boolean(trial.findings?.outcomes?.length) || trial.findings?.due?.code === "results_posted"),
    ],
    ["finished", earliest(trials, "completed") ?? held(trials, (trial) => trial.facts.overall_status === "completed")],
    ["started", earliest(trials, "started")],
    ["registered", earliest(trials, "registered") ?? { nctId: trials[0].nct_id, day: null, eventKey: null }],
  ];
  const [step, reason] = reached.find(([, why]) => why !== null) as [ProgressStep, ProgressReason];
  const cautions: Caution[] = [];
  if (code === "retracted") cautions.push({ kind: "retracted" });
  for (const trial of trials) {
    const state: string = trial.facts.overall_status;
    if (ENDED_EARLY.includes(state)) cautions.push({ kind: "ended_early", nctId: trial.nct_id, state, reason: trial.facts.why_stopped ?? null });
    const due = trial.findings?.due;
    // Not said of a trial whose results the page itself carries: the record has moved on since the lab's reading.
    const posted = trial.events.some((event: any) => event.kind === "results_posted" && recorded(event)) || Boolean(trial.findings?.outcomes?.length);
    if (due?.code === "no_results_a_year_after_completion" && !posted) cautions.push({ kind: "no_results", nctId: trial.nct_id, asOf: due.as_of, days: due.days_since_completion });
  }
  return { step, place: PROGRESS_STEPS.indexOf(step) + 1, reason, cautions };
}
