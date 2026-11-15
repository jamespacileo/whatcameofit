// Why a claim stands where it does, in the claim's own records: the sentence a home page
// row's status card opens to. It reads only the events the status rests on
// (`status.explained_by`) and the trial events beside them, so it says what the rule in
// pipeline/src/thenwhat/status/rules.py saw, and never more. Each status that has records
// has a fixed template; the others have no reason beyond their meaning, and get none.
import type { ExportedClaim, ExportedEvent } from "./export";
import { STATUS_LABELS, assertNeutral, eventLabel } from "./status.ts";
import { formatDate } from "./timetable.ts";

/** Phases the rule counts as a trial phase; "not_applicable" and none are not phases. */
const PHASES = new Set(["early_phase_1", "phase_1", "phase_2", "phase_3", "phase_4"]);
/** A trial cannot finish without having started, whether or not its start was recorded. */
const SHOWS_A_START = new Set(["started", "completed"]);

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;

function trialsResting(claim: ExportedClaim): Map<string, ExportedEvent[]> {
  const resting = new Set(
    claim.events
      .filter((event) => claim.status.explained_by.includes(event.id) && event.trial_id)
      .map((event) => event.trial_id!),
  );
  const trials = new Map<string, ExportedEvent[]>();
  for (const event of claim.events) {
    if (event.trial_id && resting.has(event.trial_id)) {
      trials.set(event.trial_id, [...(trials.get(event.trial_id) ?? []), event]);
    }
  }
  return trials;
}

const started = (trial: ExportedEvent[]) =>
  trial.some((event) => SHOWS_A_START.has(event.trial_state ?? ""));

/** The phases the trial was most recently recorded with, as the rule reads them. */
function hasPhase(trial: ExportedEvent[]): boolean {
  const dated = [...trial].sort((a, b) => (a.event_date < b.event_date ? -1 : 1));
  const latest = dated.reverse().find((event) => event.trial_phases.length > 0);
  return (latest?.trial_phases ?? []).some((phase) => PHASES.has(phase));
}

// The site's own wording. Each takes counts, identifiers and dates only.
const TEMPLATES = {
  onRecord: (trials: number) => `${plural(trials, "trial is", "trials are")} on record.`,
  allStartedNoPhase: (trials: number) =>
    trials === 1
      ? "It has started, and the registry gives it no phase."
      : `${trials === 2 ? "Both" : `All ${trials}`} have started, and the registry gives them no phase.`,
  someStartedNoPhase: (count: number) =>
    `${count} of them ${count === 1 ? "has" : "have"} started, and the registry gives ${count === 1 ? "it" : "them"} no phase.`,
  noneStarted: (trials: number) =>
    trials === 1 ? "It has not started yet." : "None has started yet.",
  othersNotStarted: (count: number) => `${plural(count, "has", "have")} not started.`,
  whyNoPhase:
    "Registries give no phase to studies such as device or behaviour trials, and only a started trial with a phase moves a claim to Phase 1 or later.",
  phaseOne: (id: string, label: string, day: string) =>
    `Trial ${id} is recorded as a ${label} and started on ${day}.`,
  phaseMany: (count: number, label: string, day: string) =>
    `${count} trials recorded as ${label}s have started, the first on ${day}.`,
  noneLater: "No trial at a later phase has started.",
  latest: (label: string, day: string) => `The latest record it rests on: ${label}, ${day}.`,
};

/** One or more sentences on why this claim has its status, or null when there is no record to cite. */
export function statusReason(claim: ExportedClaim): string | null {
  const code = claim.status.code;
  if (code === "trial_registered") {
    const trials = [...trialsResting(claim).values()];
    if (trials.length === 0) return null;
    const startedCount = trials.filter((trial) => started(trial) && !hasPhase(trial)).length;
    const waiting = trials.length - startedCount;
    const sentences = [TEMPLATES.onRecord(trials.length)];
    if (startedCount === trials.length) sentences.push(TEMPLATES.allStartedNoPhase(trials.length));
    else if (startedCount === 0) sentences.push(TEMPLATES.noneStarted(trials.length));
    else sentences.push(TEMPLATES.someStartedNoPhase(startedCount), TEMPLATES.othersNotStarted(waiting));
    if (startedCount > 0) sentences.push(TEMPLATES.whyNoPhase);
    return sentences.join(" ");
  }
  if (code === "phase_1" || code === "phase_2" || code === "phase_3") {
    const trials = [...trialsResting(claim).entries()];
    const starts = trials
      .flatMap(([, trial]) => trial)
      .filter((event) => SHOWS_A_START.has(event.trial_state ?? ""))
      .map((event) => event.event_date)
      .sort();
    if (trials.length === 0 || starts.length === 0) return null;
    const label = STATUS_LABELS[code];
    const day = formatDate(starts[0]);
    const first =
      trials.length === 1
        ? TEMPLATES.phaseOne(trials[0][0], label, day)
        : TEMPLATES.phaseMany(trials.length, label, day);
    return code === "phase_3" ? first : `${first} ${TEMPLATES.noneLater}`;
  }
  const resting = claim.events
    .filter((event) => claim.status.explained_by.includes(event.id))
    .sort((a, b) => (a.event_date < b.event_date ? -1 : 1));
  const latest = resting.at(-1);
  return latest ? TEMPLATES.latest(eventLabel(latest), formatDate(latest.event_date)) : null;
}

/** Every template filled with sample values, for the build's wording checks. */
export function sampleReasons(): string[] {
  return [
    TEMPLATES.onRecord(1),
    TEMPLATES.onRecord(3),
    TEMPLATES.allStartedNoPhase(1),
    TEMPLATES.allStartedNoPhase(2),
    TEMPLATES.allStartedNoPhase(3),
    TEMPLATES.someStartedNoPhase(2),
    TEMPLATES.noneStarted(1),
    TEMPLATES.noneStarted(3),
    TEMPLATES.othersNotStarted(1),
    TEMPLATES.whyNoPhase,
    TEMPLATES.phaseOne("NCT00000000", "Phase 2 trial", "1 Jan 2020"),
    TEMPLATES.phaseMany(2, "Phase 3 trial", "1 Jan 2020"),
    TEMPLATES.noneLater,
    TEMPLATES.latest("Regulatory approval", "1 Jan 2020"),
  ];
}

assertNeutral(sampleReasons());
