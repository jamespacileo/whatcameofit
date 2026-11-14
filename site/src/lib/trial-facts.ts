// What a registered trial says of itself, in the site's own words. The export carries
// codes and the registry's own text; the site words the codes here. Openspec
// trial-facts: a posted result is shown as the registry's numbers, and nothing on this
// page says whether an outcome was met. A trial is never worded as open to join.
import type {
  ExportedClaim,
  ExportedComparison,
  ExportedResultGroup,
  ExportedResultOutcome,
  ExportedTrial,
  ExportedTrialFacts,
} from "./export";

export const TRIAL_STATE_WORDS: Record<string, string> = {
  not_started: "Not started",
  under_way: "Under way",
  completed: "Completed",
  suspended: "Suspended",
  terminated: "Stopped early",
  withdrawn: "Withdrawn before it started",
  unknown: "State not given",
};

export const PHASE_WORDS: Record<string, string> = {
  early_phase_1: "Early Phase 1",
  phase_1: "Phase 1",
  phase_2: "Phase 2",
  phase_3: "Phase 3",
  phase_4: "Phase 4",
  not_applicable: "No phase",
};

/** Furthest first. A trial with no phase sorts after every trial that has one. */
const PHASE_RANK: Record<string, number> = {
  phase_4: 5,
  phase_3: 4,
  phase_2: 3,
  phase_1: 2,
  early_phase_1: 1,
  not_applicable: 0,
};

export const STUDY_KIND_WORDS: Record<string, string> = {
  interventional: "Interventional trial",
  observational: "Observational study",
  expanded_access: "Expanded access record",
};

export const ALLOCATION_WORDS: Record<string, string> = {
  randomised: "Randomised",
  non_randomised: "Not randomised",
};

export const MASKING_WORDS: Record<string, string> = {
  none: "Open label",
  single: "Single-blind",
  double: "Double-blind",
  triple: "Triple-blind",
  quadruple: "Quadruple-blind",
};

export const COMPARATOR_WORDS: Record<string, string> = {
  placebo: "placebo",
  sham: "a sham procedure",
  active: "another treatment",
  no_treatment: "no treatment",
};

export const SPONSOR_KIND_WORDS: Record<string, string> = {
  industry: "Company",
  government: "Government body",
  individual: "An individual researcher",
  network: "Research network",
  other: "University, hospital or other body",
};

export const AGE_GROUP_WORDS: Record<string, string> = {
  child: "children",
  adult: "adults",
  older_adult: "older adults",
};

export const MEASURE_WORDS: Record<string, string> = {
  mean: "Mean",
  median: "Median",
  number: "Number",
  count_of_participants: "Number of participants",
  count_of_units: "Number of units",
  geometric_mean: "Geometric mean",
  least_squares_mean: "Least squares mean",
  geometric_least_squares_mean: "Geometric least squares mean",
  log_mean: "Log mean",
};

export const TEST_WORDS: Record<string, string> = {
  superiority: "superiority test",
  non_inferiority: "non-inferiority test",
  equivalence: "equivalence test",
};

const BASIS_WORDS: Record<string, string> = {
  actual: "enrolled",
  planned: "planned",
};

/** What the section says of itself, once, above the trials. */
export const TRIALS_NOTE =
  "Each trial on record for this treatment and condition, furthest phase first. The facts are a selection, unaltered, from the trial's registry record. Results are the numbers the trial's sponsor posted to the registry. A score is about the match, not about the treatment.";

export const NO_P_VALUE = "Comparison posted with no p value";

// A build fails rather than say how a trial turned out. The numbers are shown; the
// reader and the linked record do the rest.
const OUTCOME_VERDICT_WORDS =
  /\b(met|missed|significan\w*|success\w*|fail\w*|work(s|ed)|prove[nsd]?|effective\w*|ineffective\w*|promising|breakthrough|cure[sd]?|recruit\w*|enrol+ing|join|eligib\w*)\b/i;

export function assertNoOutcomeVerdict(texts: string[]): void {
  for (const text of texts) {
    const found = text.match(OUTCOME_VERDICT_WORDS);
    if (found) {
      throw new Error(
        `Verdict wording "${found[0]}" in trial wording: "${text}". Trial facts state what a record says, never how a trial turned out or that it is open to join.`,
      );
    }
  }
}

assertNoOutcomeVerdict([
  ...[
    TRIAL_STATE_WORDS,
    PHASE_WORDS,
    STUDY_KIND_WORDS,
    ALLOCATION_WORDS,
    MASKING_WORDS,
    COMPARATOR_WORDS,
    SPONSOR_KIND_WORDS,
    AGE_GROUP_WORDS,
    MEASURE_WORDS,
    TEST_WORDS,
    BASIS_WORDS,
  ].flatMap((words) => Object.values(words)),
  TRIALS_NOTE,
  NO_P_VALUE,
]);

/** Fact codes in the export that the site has no words for, as "kind: code". */
export function unlabelledTrialCodes(trials: ExportedTrial[]): string[] {
  const missing = new Set<string>();
  const check = (kind: string, words: Record<string, string>, code: string | null | undefined) => {
    if (code !== null && code !== undefined && !(code in words)) missing.add(`${kind}: ${code}`);
  };
  for (const trial of trials) {
    check("state", TRIAL_STATE_WORDS, trial.state);
    for (const phase of trial.phases) check("phase", PHASE_WORDS, phase);
    const facts = trial.facts;
    if (!facts) continue;
    check("study kind", STUDY_KIND_WORDS, facts.study_kind);
    check("allocation", ALLOCATION_WORDS, facts.allocation);
    check("masking", MASKING_WORDS, facts.masking);
    for (const comparator of facts.comparators) check("comparator", COMPARATOR_WORDS, comparator);
    for (const group of facts.age_groups) check("age group", AGE_GROUP_WORDS, group);
    check("sponsor kind", SPONSOR_KIND_WORDS, facts.sponsor?.kind);
    check("participants", BASIS_WORDS, facts.participants?.basis);
    for (const outcome of facts.results?.outcomes ?? []) {
      check("measure", MEASURE_WORDS, outcome.measure);
      for (const comparison of outcome.comparisons) check("test", TEST_WORDS, comparison.test);
    }
  }
  return [...missing].sort();
}

const number = (count: number) => count.toLocaleString("en-GB");

function listOf(parts: string[]): string {
  if (parts.length <= 1) return parts.join("");
  return `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
}

export function phaseText(phases: string[]): string | null {
  const named = phases.map((phase) => PHASE_WORDS[phase] ?? phase);
  return named.length > 0 ? named.join("/") : null;
}

function phaseRank(trial: ExportedTrial): number {
  return Math.max(-1, ...trial.phases.map((phase) => PHASE_RANK[phase] ?? -1));
}

/** Furthest phase first. Within a phase: a trial with posted results, then the larger
 * trial, then by identifier, so the order is fixed. */
export function orderTrials(trials: ExportedTrial[]): ExportedTrial[] {
  const posted = (trial: ExportedTrial) => (trial.facts?.results ? 1 : 0);
  return [...trials].sort(
    (a, b) =>
      phaseRank(b) - phaseRank(a) ||
      posted(b) - posted(a) ||
      (b.facts?.participants?.count ?? -1) - (a.facts?.participants?.count ?? -1) ||
      (a.trial_id < b.trial_id ? -1 : 1),
  );
}

/** How many of these trials have posted results, for the fold that holds the rest. */
export function withResults(trials: ExportedTrial[]): number {
  return trials.filter((trial) => trial.facts?.results).length;
}

/** "83 participants enrolled" or "400 participants planned". */
export function participantsText(facts: ExportedTrialFacts | null): string | null {
  const stated = facts?.participants;
  if (!stated) return null;
  const people = stated.count === 1 ? "participant" : "participants";
  return `${number(stated.count)} ${people} ${BASIS_WORDS[stated.basis] ?? stated.basis}`;
}

/** "Randomised, double-blind, compared with placebo". Null when the record states none of it. */
export function designText(facts: ExportedTrialFacts | null): string | null {
  if (!facts) return null;
  const parts = [
    facts.allocation ? ALLOCATION_WORDS[facts.allocation] : null,
    facts.masking ? MASKING_WORDS[facts.masking] : null,
    facts.comparators.length > 0
      ? `compared with ${listOf(facts.comparators.map((code) => COMPARATOR_WORDS[code] ?? code))}`
      : null,
  ].filter((part): part is string => part !== null);
  if (parts.length === 0) return null;
  const [first, ...rest] = parts;
  return [first.charAt(0).toUpperCase() + first.slice(1), ...rest.map(lowerFirst)].join(", ");
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

/** "Healthy volunteers; adults and older adults". Null when the record states neither. */
export function studiedText(facts: ExportedTrialFacts | null): string | null {
  if (!facts) return null;
  const ages = listOf(facts.age_groups.map((code) => AGE_GROUP_WORDS[code] ?? code));
  const parts = [
    facts.healthy_volunteers === true ? "Healthy volunteers" : null,
    ages ? ages.charAt(0).toUpperCase() + ages.slice(1) : null,
  ].filter((part): part is string => part !== null);
  return parts.length > 0 ? parts.join("; ") : null;
}

/** The sponsor's name with its kind, or the kind alone when the sponsor is a person. */
export function sponsorText(facts: ExportedTrialFacts | null): string | null {
  const sponsor = facts?.sponsor;
  if (!sponsor) return null;
  const kind = sponsor.kind ? SPONSOR_KIND_WORDS[sponsor.kind] : null;
  if (sponsor.name && kind) return `${sponsor.name} (${lowerFirst(kind)})`;
  return sponsor.name ?? kind;
}

/** "3.4 (Standard Deviation 1.1)" or "33 (22 to 47)", as the registry wrote the numbers. */
export function groupValueText(group: ExportedResultGroup, outcome: ExportedResultOutcome): string {
  if (group.value === null) return "No value posted";
  const kind = outcome.spread_kind ? `${outcome.spread_kind} ` : "";
  if (group.lower !== null && group.upper !== null) {
    return `${group.value} (${kind}${group.lower} to ${group.upper})`;
  }
  if (group.spread !== null) return `${group.value} (${kind}${group.spread})`;
  return group.value;
}

/** "Median, score on a scale" for the line that says what the numbers are. A count of
 * participants is not followed by the unit "participants". */
export function measureText(outcome: ExportedResultOutcome): string | null {
  const kind = outcome.measure ? MEASURE_WORDS[outcome.measure] : null;
  const repeats =
    outcome.measure === "count_of_participants" && /^participants?$/i.test(outcome.unit ?? "");
  const parts = [kind, repeats ? null : outcome.unit].filter((part): part is string => Boolean(part));
  return parts.length > 0 ? parts.join(", ") : null;
}

/** "p = 0.03, t-test, 2 sided (superiority test)". The p value is the registry's own text. */
export function comparisonText(comparison: ExportedComparison): string {
  const written = comparison.p_value?.trim();
  const p = !written ? NO_P_VALUE : /^[<>=≤≥]/.test(written) ? `p ${spaced(written)}` : `p = ${written}`;
  const test = comparison.test ? ` (${TEST_WORDS[comparison.test]})` : "";
  return [p, comparison.method].filter(Boolean).join(", ") + test;
}

// "<0.001" reads as "p < 0.001".
function spaced(written: string): string {
  return written.replace(/^([<>=≤≥]=?)\s*/, "$1 ");
}

export interface TrialCount {
  count: number;
  /** The largest number of participants any trial states. Never a sum across trials. */
  largest: { count: number; basis: string } | null;
}

export function countTrials(claim: Pick<ExportedClaim, "trials">): TrialCount {
  const trials = claim.trials ?? [];
  const stated = trials
    .map((trial) => trial.facts?.participants)
    .filter((entry): entry is { count: number; basis: "actual" | "planned" } => Boolean(entry));
  const largest = stated.sort((a, b) => b.count - a.count)[0] ?? null;
  return { count: trials.length, largest };
}

/** "3 on record". */
export function trialCountText(tally: TrialCount): string {
  return `${number(tally.count)} on record`;
}

/** "The largest, 1,200 participants enrolled", or the one trial's size. Null when no
 * trial states a number. */
export function largestText(tally: TrialCount): string | null {
  if (!tally.largest) return null;
  const people = tally.largest.count === 1 ? "participant" : "participants";
  const size = `${number(tally.largest.count)} ${people} ${BASIS_WORDS[tally.largest.basis] ?? tally.largest.basis}`;
  return tally.count === 1 ? size : `The largest, ${size}`;
}

// The sources whose records are papers. Every other matched record is a trial registry's.
const PAPER_SOURCES = new Set(["crossref", "europepmc", "openalex"]);

/** Whether a matched record is a paper, which is never counted as a registry record. */
export function isPaperMatch(match: { source_name: string }): boolean {
  return PAPER_SOURCES.has(match.source_name);
}

/** How many trials the page shows before the rest go behind one press. */
export const TRIALS_SHOWN = 5;
