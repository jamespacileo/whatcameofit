// What a pair page shows, in the site's words, from one `PairPage` file (openspec pairs-site).
// Pure: no file, network or clock, so the build and the Worker read a page the same way. Every
// code's words are in `pair-wording.ts`; `readBundle` stops a build on a code
// with none, and the Worker reads only the bundle version the build read.
import {
  PAIR_APPROACH_LABELS,
  PAIR_EVENT_LABELS,
  PAIR_OUTCOME_KIND_WORDS,
  PAIR_PHASE_WORDS,
  PAIR_REGISTRY_NAMES,
  PAIR_STATUS_GLOSSES,
  PAIR_STATUS_LABELS,
  PAIR_TRIAL_STATES,
} from "./pair-wording.ts";
import { MEASURE_WORDS, TEST_WORDS, TRIAL_STATE_WORDS, comparisonText } from "./trial-facts.ts";

export { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES };

export interface PaperLink {
  id: string;
  /** The identifier as the reader sees it: "doi:10.1186/..." or "PMID 42027418". */
  label: string;
  /** Where the identifier resolves, or null for a kind the site does not link. */
  url: string | null;
}

/** A paper by the identifier the lab holds. A DOI is linked through the DOI resolver as
 * https://doi.org/<DOI>, the form Crossref's DOI display guidelines ask for
 * (https://www.crossref.org/display-guidelines/); a PubMed identifier through PubMed's own
 * address, https://pubmed.ncbi.nlm.nih.gov/<PMID>/ (NLM, "Linking to PubMed"). An identifier
 * of any other kind is shown as written, unlinked: the site does not guess an address. Each
 * part of a DOI between slashes is percent-encoded, so a `?`, `#` or `%` in its suffix reaches
 * the resolver as part of the DOI (DOI Handbook 2.5.2.4, https://www.doi.org/the-identifier/resources/handbook/2_numbering). */
export function paperLink(id: string): PaperLink {
  if (/^10\.\d{4,9}\/\S+$/.test(id)) {
    return { id, label: `doi:${id}`, url: `https://doi.org/${id.split("/").map(encodeURIComponent).join("/")}` };
  }
  const pmid = /^pmid:(\d+)$/i.exec(id)?.[1];
  if (pmid) return { id, label: `PMID ${pmid}`, url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` };
  return { id, label: id, url: null };
}

export interface ResultRowView {
  group: string;
  /** The registry's row or category title within the group, where it gives one. */
  part: string | null;
  analysed: string | null;
  value: string;
}

export interface OutcomeView {
  title: string;
  kind: string;
  /** "Median, pg/mL": what the numbers are. */
  measure: string | null;
  timeFrame: string | null;
  rows: ResultRowView[];
  comparisons: string[];
}

/** A posted value as the registry wrote it: "0.0 (Full Range -4.2 to 10.9)". Nothing is
 * worked out or rounded. ClinicalTrials.gov's results data elements set what each field is:
 * the measure type, the measure of dispersion or precision, and the number analysed
 * (https://clinicaltrials.gov/policy/results-definitions). */
function valueText(value: any, dispersion: string | null): string {
  if (value.value === null) return "No value posted";
  const kind = dispersion ? `${dispersion} ` : "";
  if (value.lower !== null && value.upper !== null) return `${value.value} (${kind}${value.lower} to ${value.upper})`;
  if (value.spread !== null) return `${value.value} (${kind}${value.spread})`;
  return value.value;
}

/** A posted comparison in the registry's terms: its p value and method in the claim page's
 * wording, then any estimate with its interval ("Risk Difference (RD) -1.5, 95% interval -7.2
 * to 3.7"), then the groups it covers, so a comparison of two arms of three, or within one
 * arm, says which. ClinicalTrials.gov's statistical analysis elements
 * (https://clinicaltrials.gov/policy/results-definitions) give each field. */
/** A posted interval with whichever bounds the registry gives: both ("95% interval -7.2 to
 * 3.7"), or one, as a one-sided interval is posted ("95% interval from -7.2", "95% interval up
 * to 3.7"). Each bound is nullable on its own in `PostedComparison`. */
function intervalText(comparison: any): string | null {
  const { lower, upper } = comparison;
  if (lower === null && upper === null) return null;
  const label = comparison.interval_pct ? `${comparison.interval_pct}% interval` : "interval";
  if (lower !== null && upper !== null) return `${label} ${lower} to ${upper}`;
  return lower !== null ? `${label} from ${lower}` : `${label} up to ${upper}`;
}

function comparisonLine(comparison: any, titles: Map<string, string>): string {
  const estimate = comparison.estimate
    ? [
        [comparison.estimate_kind, comparison.estimate].filter(Boolean).join(" "),
        intervalText(comparison),
      ].filter(Boolean).join(", ")
    : null;
  const test = comparison.design && Object.hasOwn(TEST_WORDS, comparison.design.toLowerCase()) ? comparison.design.toLowerCase() : null;
  // With an estimate and no p value, the estimate is the result; the line does not say "no p value".
  const tested = comparison.p_value || !estimate ? comparisonText({ p_value: comparison.p_value, method: comparison.method, test } as any) : comparison.method;
  const groups = comparison.group_ids.map((id: string) => titles.get(id) ?? id);
  return [tested, estimate].filter(Boolean).join("; ") + (groups.length ? `. Posted for: ${groups.join(", ")}` : "");
}

/** A trial's posted outcomes, primary first, each with its groups' values and any
 * comparison the sponsor posted with it. */
function outcomesOf(findings: any): OutcomeView[] {
  if (!findings) return [];
  const rank: Record<string, number> = { primary: 0, secondary: 1, other: 2, post_hoc: 3 };
  return [...findings.outcomes]
    .sort((a, b) => (rank[a.kind] ?? 9) - (rank[b.kind] ?? 9))
    .map((outcome) => {
      const measureCode = outcome.param_type?.toLowerCase().replace(/\s+/g, "_");
      const kind = measureCode && Object.hasOwn(MEASURE_WORDS, measureCode) ? MEASURE_WORDS[measureCode] : outcome.param_type;
      // A count of participants is not followed by the unit "participants".
      const repeats = measureCode === "count_of_participants" && /^participants?$/i.test(outcome.unit ?? "");
      const measure = [kind, repeats ? null : outcome.unit].filter(Boolean).join(", ") || null;
      return {
        title: outcome.title,
        kind: PAIR_OUTCOME_KIND_WORDS[outcome.kind],
        measure,
        timeFrame: outcome.time_frame,
        rows: outcome.values.map((value: any) => ({
          group: value.group_title ?? value.group_id,
          part: [value.class_title, value.category_title].filter(Boolean).join(", ") || null,
          analysed: value.analysed,
          value: valueText(value, outcome.dispersion_type),
        })),
        comparisons: findings.comparisons
          .filter((comparison: any) => comparison.outcome_key === outcome.key)
          .map((comparison: any) =>
            comparisonLine(comparison, new Map(outcome.values.map((value: any) => [value.group_id, value.group_title ?? value.group_id]))),
          ),
      };
    });
}

/** Whether a pair is one of the examples built pages carry: the lookup's sentences to pass on
 * and the journalists' picker. A pair with a claim origin, or with more than one supporting
 * trial. It is no file of the build: every pair's page, record, embed and card is made on
 * request (openspec pairs-site task 4.6). Kept to a few, so a page never carries every pair. */
export function featured(page: any): boolean {
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
  /** The phase codes as the registry gives them (`TrialPhase`), for grouping by phase. */
  phaseCodes: string[];
  participants: string | null;
  start: string | null;
  primaryCompletion: string | null;
  arms: string[];
  /** The arm that gives the pair's intervention, where the lab named one. */
  pairArm: string | null;
  whyStopped: string | null;
  events: PairEventView[];
  papers: PaperLink[];
  resultsPosted: boolean;
  outcomes: OutcomeView[];
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
  /** The topic the lab filed the pair under, or null. */
  topic: string | null;
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
        phaseCodes: facts.phases ?? [],
        participants: facts.participants
          ? `${facts.participants.count.toLocaleString("en-GB")} ${facts.participants.actual ? "taking part" : "planned"}`
          : null,
        start: facts.start?.day ?? null,
        primaryCompletion: facts.primary_completion?.day ?? null,
        arms: trial.arms,
        pairArm: trial.claim_arm,
        whyStopped: facts.why_stopped,
        events: trial.events.map(eventView).sort(byDay),
        papers: trial.paper_ids.map(paperLink),
        // Posted when the registry dated their posting, or when the page carries them.
        resultsPosted: trial.events.some((event: any) => event.kind === "results_posted") || Boolean(trial.findings?.outcomes.length),
        outcomes: outcomesOf(trial.findings),
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
    topic: row.filing?.vertical ?? null,
  };
}

export interface NarrowerPair {
  address: string;
  condition: string;
}

/** The same treatment's other pairs whose condition sits beneath this pair's in MeSH: a tree
 * number of theirs continues one of this pair's ("C01.610" is beneath "C01"). Read from the
 * intervention's page file, the one source the built page and the Worker share, so the two
 * list the same pairs. In the order of the conditions' names. */
export function narrowerPairs(page: any, interventionPage: any | null, published: Set<string>): NarrowerPair[] {
  if (!interventionPage) return [];
  const tops: string[] = page.row.descriptor.tree_numbers;
  const self = page.row.pair.address;
  const found = new Map<string, string>();
  for (const row of interventionPage.pairs) {
    const address = row.pair.address;
    // Only a pair with a page in this bundle version: a listing can name pairs a slice left out.
    if (address === self || found.has(address) || !published.has(address)) continue;
    const beneath = row.descriptor.tree_numbers.some((number: string) => tops.some((top) => number.startsWith(`${top}.`)));
    if (beneath) found.set(address, row.descriptor.label);
  }
  return [...found].sort(([, a], [, b]) => a.localeCompare(b)).map(([address, condition]) => ({ address, condition }));
}
