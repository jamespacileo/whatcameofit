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
import type { ExportedArm, ExportedEvent } from "./export";
import { assertNeutral } from "./status.ts";
import { formatDate } from "./timetable.ts";

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
  "Each trial on record for this treatment and condition: those that have posted results first, then the rest by furthest phase. The facts are a selection, unaltered, from the trial's registry record. Results are the numbers the trial's sponsor posted to the registry. A score is about the match, not about the treatment.";

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

/** What the trial compared with, by the names its record gives its comparator arms:
 * "Fluticasone and placebo". An "active comparator" arm counts only beside an
 * experimental arm, as for the comparator codes. Null when no arm names one. */
export function comparedNames(arms: ExportedArm[], shown = 2): string | null {
  const tested = arms.some((arm) => arm.kind === "experimental");
  const names = [
    ...new Set(
      arms
        .filter((arm) =>
          arm.kind === "active_comparator"
            ? tested
            : ["placebo_comparator", "sham_comparator", "no_intervention"].includes(arm.kind),
        )
        .flatMap((arm) =>
          arm.interventions.length > 0
            ? arm.interventions
            : arm.kind === "no_intervention"
              ? [COMPARATOR_WORDS.no_treatment]
              : arm.label
                ? [arm.label]
                : [],
        ),
    ),
  ];
  if (names.length === 0) return null;
  const listed = names.slice(0, shown);
  const more = names.length - listed.length;
  const text = more > 0 ? `${listed.join(", ")} and ${more} more` : listed.join(" and ");
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

/** What the trial tests, by its experimental arms' interventions: "Mometasone". */
export function testedNames(arms: ExportedArm[]): string | null {
  const names = [
    ...new Set(arms.filter((arm) => arm.kind === "experimental").flatMap((arm) => arm.interventions)),
  ];
  return names.length > 0 ? names.slice(0, 2).join(" and ") : null;
}

/** Registry abbreviations a trial's main measure often uses, said plainly. Shown under
 * the registry's own words, which stay as written. Whole words only, case as listed. */
export const MEASURE_ABBREVIATIONS: Record<string, string> = {
  OS: "overall survival, how long people lived",
  PFS: "progression-free survival, the time before the illness grew or got worse",
  EFS: "event-free survival, the time before a set event such as the illness returning",
  DFS: "disease-free survival, the time with no sign of the illness",
  ORR: "objective response rate, the share whose tumours shrank by a set amount",
  pCR: "pathological complete response, no cancer found in tissue removed after treatment",
  TEAE: "side effects that began or worsened during treatment",
  TEAEs: "side effects that began or worsened during treatment",
  AE: "adverse event, any unwanted medical event",
  AEs: "adverse events, any unwanted medical events",
  SAE: "serious adverse event",
  SAEs: "serious adverse events",
  DLT: "dose-limiting toxicity, a side effect serious enough to limit the dose",
  DLTs: "dose-limiting toxicities, side effects serious enough to limit the dose",
  RECIST: "standard rules for measuring tumour size",
  IRRC: "an independent review committee",
  BICR: "an independent review committee",
  HbA1c: "average blood sugar over about three months",
  FEV1: "how much air a person can blow out in one second",
  MACE: "major heart and circulation events",
};

assertNoOutcomeVerdict(Object.values(MEASURE_ABBREVIATIONS));

/** The abbreviations a measure's text uses, in the order they first appear, each said
 * once: "PFS: progression-free survival, …". */
export function measureGlosses(text: string): string[] {
  const found = new Map<string, string>();
  for (const word of text.match(/[A-Za-z][A-Za-z0-9]*/g) ?? []) {
    const plain = MEASURE_ABBREVIATIONS[word];
    if (plain && ![...found.values()].includes(plain)) found.set(word, plain);
  }
  return [...found.entries()].map(([word, plain]) => `${word}: ${plain}`);
}

/** How many trials of one phase are shown before the rest of that phase fold away. */
export const TRIALS_PER_PHASE = 10;

export const NO_PHASE_GROUP = "No phase given";
export const RESULTS_GROUP = "Results posted";

export interface PhaseGroup {
  /** "Results posted", "Phase 3", "Phase 2, including Phase 1/Phase 2", or "No phase given". */
  name: string;
  /** In the order `orderTrials` gives them. */
  trials: ExportedTrial[];
  /** More than one phase wording in the group, so each row names its own. */
  mixed: boolean;
}

/** Ordered trials in groups: first every trial that has posted results, whatever its
 * phase, then the rest by furthest phase, furthest first. A trial of Phase 1/Phase 2 sits
 * with Phase 2. A trial with no phase, or "not applicable", is in the last group. */
export function phaseGroups(trials: ExportedTrial[]): PhaseGroup[] {
  const ordered = orderTrials(trials);
  const posted = ordered.filter((trial) => trial.facts?.results);
  const byRank = new Map<number, ExportedTrial[]>();
  for (const trial of ordered) {
    if (trial.facts?.results) continue;
    const rank = Math.max(0, phaseRank(trial));
    byRank.set(rank, [...(byRank.get(rank) ?? []), trial]);
  }
  const phases = [...byRank.entries()]
    .sort(([a], [b]) => b - a)
    .map(([rank, members]) => {
      if (rank === 0) return { name: NO_PHASE_GROUP, trials: members, mixed: false };
      const words = [
        ...new Set(members.map((trial) => phaseText(trial.phases.filter((code) => code !== "not_applicable"))!)),
      ].sort((a, b) => a.length - b.length || (a < b ? -1 : 1));
      const name = words.length > 1 ? `${words[0]}, including ${words.slice(1).join(" and ")}` : words[0];
      return { name, trials: members, mixed: words.length > 1 };
    });
  return posted.length > 0 ? [{ name: RESULTS_GROUP, trials: posted, mixed: true }, ...phases] : phases;
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

// The sources whose records are papers. Every other matched record is a trial registry's.
const PAPER_SOURCES = new Set(["crossref", "europepmc", "openalex"]);

/** Whether a matched record is a paper, which is never counted as a registry record. */
export function isPaperMatch(match: { source_name: string }): boolean {
  return PAPER_SOURCES.has(match.source_name);
}

/** How many trials the page shows before the rest go behind one press. */
// A trial's entry in plain words (openspec site-publishing, change plain-trial-entries):
// a heading a lay reader can read, the design and state said plainly, and posted results
// as a table. The registry's exact terms stay one press away, in the entry's fold.

/** How people were assigned, said plainly. The registry's term is in the fold. */
export const PLAIN_ALLOCATION: Record<string, string> = {
  randomised: "Assigned at random",
  non_randomised: "Not assigned at random",
};

/** Whether anyone was kept unaware of who had what. Every level reads "Blinded": the
 * levels differ in who was kept unaware, which the fold gives in the registry's term. */
export const PLAIN_MASKING: Record<string, string> = {
  none: "Open label: everyone knew what they had",
  single: "Blinded",
  double: "Blinded",
  triple: "Blinded",
  quadruple: "Blinded",
};

/** A trial's state, said plainly. Never that a trial is open to join. */
export const PLAIN_STATE: Record<string, string> = { ...TRIAL_STATE_WORDS, completed: "Finished" };

export const RESULTS_POSTED = "Results posted";

/** How an entry introduces what a trial measures: in the past only once the trial has
 * ended or has posted results, so a trial not yet started is not said to have measured anything. */
export const MEASURE_LEADS = { ended: "It measured", planned: "It sets out to measure" } as const;

export function measureLead(trial: ExportedTrial): string {
  const ended = trial.state === "completed" || trial.state === "terminated";
  return ended || trial.facts?.results ? MEASURE_LEADS.ended : MEASURE_LEADS.planned;
}

/** What the fold's control says is inside. */
export const FOLD_LABELS = {
  results: "Who took part, who ran it, and the posted results",
  planned: "Who took part, who ran it, and what it planned to measure",
  record: "More from its record",
} as const;

/** What stands under a table of posted results. */
export const RESULT_NOTES = {
  fall: "A minus number is a fall.",
  scale: "The registry record says what this measure runs from and to, and which way is better.",
  no_phase: "None given.",
} as const;

/** What a trial was compared with, as a heading says it. A sham is a device for a
 * device and a procedure otherwise. */
function comparatorWords(code: string, approach: string | null): string {
  if (code === "sham") return approach === "device" ? "a sham device" : "a sham procedure";
  if (code === "placebo") return "a placebo";
  return COMPARATOR_WORDS[code] ?? code;
}

/** "135 people, compared with a sham device and with no treatment". States only what the
 * record states. With no stated size the heading is the registry's title. */
export function trialHeading(
  trial: ExportedTrial,
  approach: string | null,
): { text: string; isTitle: boolean } {
  const stated = trial.facts?.participants;
  if (!stated) return { text: trial.title ?? `Trial ${trial.trial_id}`, isTitle: true };
  const people = `${number(stated.count)} ${stated.count === 1 ? "person" : "people"}`;
  const size = stated.basis === "planned" ? `${people} planned` : people;
  const compared = (trial.facts?.comparators ?? []).map((code) => comparatorWords(code, approach));
  const text = compared.length > 0 ? `${size}, compared with ${compared.join(" and with ")}` : size;
  return { text, isTitle: false };
}

export interface TrialDates {
  /** The day the registry says the trial was completed. */
  finished: string | null;
  /** The day results were last posted. */
  posted: string | null;
}

/** A trial's dates, from the claim's events for it. */
export function trialDates(events: ExportedEvent[], trialId: string): TrialDates {
  const latest = (found: ExportedEvent[]) => found.map((event) => event.event_date).sort().pop() ?? null;
  const own = events.filter((event) => event.trial_id === trialId);
  return {
    finished: latest(own.filter((event) => event.type === "trial_status_change" && event.trial_state === "completed")),
    posted: latest(own.filter((event) => event.type === "trial_results_posted")),
  };
}

/** A date that never breaks across two lines. */
const day = (isoDate: string) => formatDate(isoDate).replace(/ /g, "\u00a0");

/** The line under the heading: how people were assigned, blinded or open label, the state
 * with its date, results posted with their date, and the phase when the registry gives
 * one. A code the record does not state yields nothing. */
export function plainFacts(trial: ExportedTrial, dates: TrialDates): string[] {
  const facts = trial.facts;
  const state = PLAIN_STATE[trial.state] ?? null;
  const phased = trial.phases.filter((code) => code !== "not_applicable");
  return [
    facts?.allocation ? (PLAIN_ALLOCATION[facts.allocation] ?? null) : null,
    facts?.masking ? (PLAIN_MASKING[facts.masking] ?? null) : null,
    state && trial.state === "completed" && dates.finished ? `${state} ${day(dates.finished)}` : state,
    facts?.results ? (dates.posted ? `${RESULTS_POSTED} ${day(dates.posted)}` : RESULTS_POSTED) : null,
    phased.length > 0 ? phaseText(phased) : null,
  ].filter((part): part is string => part !== null);
}

/** What the trials table says when a record names nothing to compare with, or has
 * posted nothing. */
export const NO_COMPARATOR = "None named in the record";
export const NO_RESULTS = "None posted";

export interface TrialColumns {
  /** "135 people", "330 people planned", or the registry's title when no size is stated. */
  lead: string;
  isTitle: boolean;
  /** "Phase 3", when the registry gives a phase. */
  phase: string | null;
  compared: string;
  /** How people were assigned and whether it was blinded: the parts the record states. */
  design: string[];
  state: string | null;
  results: string;
}

/** One trial as a row to read across: the same facts and words as `trialHeading` and
 * `plainFacts`, set out by column. States only what the record states. */
export function trialColumns(
  trial: ExportedTrial,
  approach: string | null,
  dates: TrialDates,
): TrialColumns {
  const facts = trial.facts;
  const stated = facts?.participants;
  const people = stated ? `${number(stated.count)} ${stated.count === 1 ? "person" : "people"}` : null;
  const compared = (facts?.comparators ?? []).map((code) => comparatorWords(code, approach));
  const comparedText = compared.join(" and ");
  const state = PLAIN_STATE[trial.state] ?? null;
  const phased = trial.phases.filter((code) => code !== "not_applicable");
  return {
    lead: people
      ? stated!.basis === "planned"
        ? `${people} planned`
        : people
      : (trial.title ?? `Trial ${trial.trial_id}`),
    isTitle: !people,
    phase: phased.length > 0 ? phaseText(phased) : null,
    compared:
      comparedText.length > 0
        ? `${comparedText.charAt(0).toUpperCase()}${comparedText.slice(1)}`
        : NO_COMPARATOR,
    design: [
      facts?.allocation ? (PLAIN_ALLOCATION[facts.allocation] ?? null) : null,
      facts?.masking ? (PLAIN_MASKING[facts.masking] ?? null) : null,
    ].filter((part): part is string => part !== null),
    state: state && trial.state === "completed" && dates.finished ? `${state} ${day(dates.finished)}` : state,
    results: facts?.results ? (dates.posted ? `Posted ${day(dates.posted)}` : "Posted") : NO_RESULTS,
  };
}

/** What the fold's control says is inside it. */
export function foldLabel(trial: ExportedTrial): string {
  const facts = trial.facts;
  if (facts?.results) return FOLD_LABELS.results;
  if (facts && (facts.primary_outcomes.length > 0 || facts.sponsor || facts.age_groups.length > 0)) {
    return FOLD_LABELS.planned;
  }
  return FOLD_LABELS.record;
}

export interface ResultTable {
  /** What the numbers are: "Mean", or "Value" when the record does not say. */
  statistic: string;
  /** What the spread is, when any group has one: "Standard Deviation". */
  spread: string | null;
  rows: { group: string; value: string; spread: string | null; analysed: string | null }[];
  /** The measure is a change and a value is below zero. */
  fall: boolean;
}

/** A posted outcome with one value for each group, as rows to read down. Null for an
 * outcome posted in several rows, which carries no values. The numbers are the registry's text. */
export function resultTable(outcome: ExportedResultOutcome): ResultTable | null {
  if (outcome.rows !== 1) return null;
  const rows = outcome.groups.map((group) => ({
    group: group.title,
    value: group.value ?? "No value posted",
    spread:
      group.lower !== null && group.upper !== null ? `${group.lower} to ${group.upper}` : group.spread,
    analysed: group.analysed,
  }));
  const anySpread = rows.some((entry) => entry.spread !== null);
  return {
    statistic: (outcome.measure ? MEASURE_WORDS[outcome.measure] : null) ?? "Value",
    spread: anySpread ? (outcome.spread_kind ?? "Spread") : null,
    rows,
    fall: /\bchange\b/i.test(outcome.title) && rows.some((entry) => /^[-−]/.test(entry.value.trim())),
  };
}

const PLAIN_WORDING = [
  ...Object.values(PLAIN_ALLOCATION),
  ...Object.values(PLAIN_MASKING),
  ...Object.values(PLAIN_STATE),
  ...Object.values(FOLD_LABELS),
  ...Object.values(RESULT_NOTES),
  RESULTS_POSTED,
  ...Object.values(MEASURE_LEADS),
  "a sham device",
  "a sham procedure",
  "a placebo",
];
assertNeutral(PLAIN_WORDING);
assertNoOutcomeVerdict(PLAIN_WORDING);
