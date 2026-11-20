// Every word a reader sees for a code in the lab's bundle (openspec pairs-site, task 2.4).
// The bundle carries codes only; the site owns all wording (CLAUDE.md, "The site owns all
// wording; the export carries codes"). Each table is keyed by the code exactly as the
// bundle's schema spells it, so a code is never shown where its words belong: the build
// stops on a code with none (`unwordedPairCodes`, read by `readBundle`), and on any table
// here holding verdict wording (`assertPairWordingNeutral`, run when this module loads).
import { assertNeutral, STATUS_GLOSSES, STATUS_LABELS } from "./status.ts";
import { PHASE_WORDS, TRIAL_STATE_WORDS } from "./trial-facts.ts";

/** A pair's status (`ClaimStatusCode`): the same codes and words as a claim's status. */
export { STATUS_GLOSSES as PAIR_STATUS_GLOSSES, STATUS_LABELS as PAIR_STATUS_LABELS };

/** A trial's phase (`TrialPhase`): the same codes and words as a claim's trial. */
export { PHASE_WORDS as PAIR_PHASE_WORDS };

/** The registry's state of a trial (`OverallStatus`), in the site's own trial states.
 *
 * The states ClinicalTrials.gov gives only to expanded access records (`available`,
 * `no_longer_available`, `temporarily_not_available`, `approved_for_marketing`,
 * `withheld`) are left without words on purpose, so a bundle carrying one stops the build.
 * An expanded access record is a route to a treatment outside a trial, not a trial
 * (https://clinicaltrials.gov/data-api/about-api/study-data-structure, "Expanded Access
 * Status"), and the site never presents a registry record as a treatment option
 * (CLAUDE.md, "No medical advice"). Word them only with a page that says what they are. */
export const PAIR_TRIAL_STATES: Record<string, keyof typeof TRIAL_STATE_WORDS> = {
  not_yet_recruiting: "not_started",
  recruiting: "under_way",
  enrolling_by_invitation: "under_way",
  active_not_recruiting: "under_way",
  suspended: "suspended",
  terminated: "terminated",
  completed: "completed",
  withdrawn: "withdrawn",
  unknown: "unknown",
};

/** The expanded access states of `OverallStatus`, which the site deliberately does not word. */
export const UNWORDED_TRIAL_STATES = [
  "available",
  "no_longer_available",
  "temporarily_not_available",
  "approved_for_marketing",
  "withheld",
];

/** A dated change in a trial's record (`TrialEventKind`). */
export const PAIR_EVENT_LABELS: Record<string, string> = {
  registered: "Trial registered",
  started: "Trial started",
  suspended: "Trial suspended",
  completed: "Trial completed",
  terminated: "Trial terminated",
  withdrawn: "Trial withdrawn",
  results_posted: "Trial results posted",
  phase_changed: "Trial phase changed",
};

/** The kind of treatment (`Approach`). The bundle spells its codes with underscores, where
 * the claims export spelled the same kinds with hyphens (`APPROACH_LABELS`), so the pair
 * path has its own table rather than a translation of the other's keys. The words are the
 * same: they name a kind of treatment only, never whether it works or anyone can get it. */
export const PAIR_APPROACH_LABELS: Record<string, string> = {
  drug: "Drug",
  vaccine: "Vaccine",
  gene_therapy: "Gene therapy",
  cell_therapy: "Cell therapy",
  tissue_regeneration: "Tissue regeneration",
  transplant: "Transplant",
  device: "Device",
  surgery_or_procedure: "Surgery or procedure",
  diet_or_lifestyle: "Diet or lifestyle",
};

/** A registry a pair's search read (`RegistryCheck.registry`), by the source name the
 * pipeline gives ClinicalTrials.gov (`SOURCE_NAMES` in `status.ts`). The schema types the
 * field as free text, so any other registry stops the build, named, until it is worded here. */
export const PAIR_REGISTRY_NAMES: Record<string, string> = {
  "clinicaltrials.gov": "ClinicalTrials.gov",
};

/** Every table of words this module holds, by the kind of code it words. */
export const PAIR_WORDING: Record<string, Record<string, string>> = {
  status: STATUS_LABELS,
  "status gloss": STATUS_GLOSSES,
  phase: PHASE_WORDS,
  "trial state": Object.fromEntries(
    Object.entries(PAIR_TRIAL_STATES).map(([code, state]) => [code, TRIAL_STATE_WORDS[state]]),
  ),
  event: PAIR_EVENT_LABELS,
  approach: PAIR_APPROACH_LABELS,
  registry: PAIR_REGISTRY_NAMES,
};

/** Throws, naming the words, when any table holds verdict wording ("dead", "abandoned", ...). */
export function assertPairWordingNeutral(wording: Record<string, Record<string, string>>): void {
  assertNeutral(Object.values(wording).flatMap((words) => Object.values(words)));
}

assertPairWordingNeutral(PAIR_WORDING);

/** Codes on pair pages, and on intervention pages, that the site has no words for, as
 * "kind: code", each once. */
export function unwordedPairCodes(pairPages: any[], interventionPages: any[] = []): string[] {
  const found = new Set<string>();
  const need = (kind: string, code: string | null | undefined) => {
    if (code !== null && code !== undefined && !(code in PAIR_WORDING[kind])) found.add(`${kind}: ${code}`);
  };
  for (const page of pairPages) {
    need("status", page.row.status.code);
    need("status gloss", page.row.status.code);
    need("approach", page.approach?.approach);
    for (const change of page.history) {
      need("status", change.before);
      need("status", change.after);
    }
    for (const trial of page.trials) {
      need("trial state", trial.facts.overall_status);
      for (const phase of trial.facts.phases ?? []) need("phase", phase);
      for (const event of trial.events) need("event", event.kind);
    }
    for (const check of page.checked) need("registry", check.registry);
  }
  for (const page of interventionPages) need("approach", page.approach?.approach);
  return [...found].sort();
}
