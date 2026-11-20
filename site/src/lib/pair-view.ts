// What a pair page shows, in the site's words, from one `PairPage` file (openspec pairs-site).
// Pure: no file, network or clock, so the build and the Worker read a page the same way. Every
// code's words are in `pair-wording.ts`; `readBundle` stops a build on a code
// with none, and the Worker reads only the bundle version the build read.
import {
  PAIR_APPROACH_LABELS,
  PAIR_EVENT_LABELS,
  PAIR_PHASE_WORDS,
  PAIR_REGISTRY_NAMES,
  PAIR_STATUS_GLOSSES,
  PAIR_STATUS_LABELS,
  PAIR_TRIAL_STATES,
} from "./pair-wording.ts";
import { TRIAL_STATE_WORDS } from "./trial-facts.ts";

export { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES };

/** Whether a pair's page is built ahead (design decision 2): a pair with a claim origin, or
 * with more than one supporting trial. Every other pair's page is made on request. The second
 * half is provisional until a full run's count of pairs is known (task 1.3). */
export function builtAhead(page: any): boolean {
  return page.row.origin !== null || page.trials.length > 1;
}

/** A name as the site shows it. The substance registry writes names in capitals
 * ("APITEGROMAB"); a name of letters alone is shown with only its first one capital. A name
 * with a digit is a code ("SRK-015") and is shown as written. */
export function shownName(name: string): string {
  if (name !== name.toUpperCase() || /\d/.test(name)) return name;
  return name[0] + name.slice(1).toLowerCase();
}

export interface PairEventView {
  key: string;
  day: string;
  label: string;
  nctId: string;
  estimated: boolean;
}

export interface PairTrialView {
  nctId: string;
  title: string | null;
  state: string;
  phases: string | null;
  participants: string | null;
  start: string | null;
  primaryCompletion: string | null;
  arms: string[];
  /** The arm that gives the pair's intervention, where the lab named one. */
  pairArm: string | null;
  whyStopped: string | null;
  events: PairEventView[];
  papers: number;
  resultsPosted: boolean;
  registryUrl: string;
}

export interface PairView {
  address: string;
  title: string;
  intervention: string;
  interventionSlug: string;
  condition: string;
  conditionId: string;
  conditionSlug: string;
  statusCode: string;
  status: string;
  gloss: string;
  asOf: string;
  /** The events that set the status, oldest first. */
  explainedBy: PairEventView[];
  trials: PairTrialView[];
  history: { on: string; before: string | null; after: string }[];
  otherNames: string[];
  approach: string | null;
  checkedByPerson: boolean;
  registryChecks: { registry: string; through: string }[];
  claimSlug: string | null;
}

function eventView(event: any): PairEventView {
  return {
    key: event.key,
    day: event.day,
    label: PAIR_EVENT_LABELS[event.kind],
    nctId: event.nct_id,
    estimated: event.day_basis === "registry_date_estimated",
  };
}

const byDay = (a: { day: string }, b: { day: string }) => (a.day < b.day ? -1 : a.day > b.day ? 1 : 0);

/** What a pair page shows, in the site's words. */
export function pairView(page: any): PairView {
  const { row } = page;
  const events = new Map<string, PairEventView>();
  for (const trial of page.trials) for (const event of trial.events) events.set(event.key, eventView(event));
  const preferred = row.intervention.preferred_name;
  const otherNames = [
    ...new Set(
      page.names
        .filter((name: any) => name.role !== "preferred" && name.name.toLowerCase() !== preferred.toLowerCase())
        .map((name: any) => shownName(name.name)),
    ),
  ] as string[];
  const intervention = shownName(preferred);
  return {
    address: row.pair.address,
    title: `${intervention} for ${row.descriptor.label.toLowerCase()}`,
    intervention,
    interventionSlug: row.intervention.slug,
    condition: row.descriptor.label,
    conditionId: row.condition.descriptor_id,
    conditionSlug: row.condition.slug,
    statusCode: row.status.code,
    status: PAIR_STATUS_LABELS[row.status.code as keyof typeof PAIR_STATUS_LABELS],
    gloss: PAIR_STATUS_GLOSSES[row.status.code as keyof typeof PAIR_STATUS_GLOSSES],
    asOf: row.status.as_of,
    explainedBy: row.status.explained_by
      .map((key: string) => events.get(key))
      .filter((event: PairEventView | undefined): event is PairEventView => Boolean(event))
      .sort(byDay),
    trials: page.trials.map((trial: any): PairTrialView => {
      const facts = trial.facts;
      const phases = (facts.phases ?? []).map((phase: string) => PAIR_PHASE_WORDS[phase]);
      return {
        nctId: trial.nct_id,
        title: facts.title,
        state: TRIAL_STATE_WORDS[PAIR_TRIAL_STATES[facts.overall_status]],
        phases: phases.length ? phases.join(" and ") : null,
        participants: facts.participants
          ? `${facts.participants.count.toLocaleString("en-GB")} ${facts.participants.actual ? "taking part" : "planned"}`
          : null,
        start: facts.start?.day ?? null,
        primaryCompletion: facts.primary_completion?.day ?? null,
        arms: trial.arms,
        pairArm: trial.claim_arm,
        whyStopped: facts.why_stopped,
        events: trial.events.map(eventView).sort(byDay),
        papers: trial.paper_ids.length,
        resultsPosted: trial.events.some((event: any) => event.kind === "results_posted"),
        registryUrl: `https://clinicaltrials.gov/study/${encodeURIComponent(trial.nct_id)}`,
      };
    }),
    history: page.history
      .map((change: any) => ({
        on: change.on,
        before: change.before ? PAIR_STATUS_LABELS[change.before as keyof typeof PAIR_STATUS_LABELS] : null,
        after: PAIR_STATUS_LABELS[change.after as keyof typeof PAIR_STATUS_LABELS],
      }))
      .sort((a: any, b: any) => (a.on < b.on ? -1 : 1)),
    otherNames,
    approach: page.approach?.approach ? PAIR_APPROACH_LABELS[page.approach.approach] : null,
    checkedByPerson: page.checked_by_person,
    registryChecks: page.checked.map((check: any) => ({ registry: PAIR_REGISTRY_NAMES[check.registry], through: check.checked_through })),
    claimSlug: row.origin?.claim_slug ?? null,
  };
}
