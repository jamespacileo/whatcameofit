// What a registered trial says of itself, in the site's own words. The bundle carries
// codes and the registry's own text; the site words the codes here. Openspec
// trial-facts: a posted result is shown as the registry's numbers, and nothing on a
// page says whether an outcome was met. A trial is never worded as open to join.

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
  ...[TRIAL_STATE_WORDS, PHASE_WORDS, MEASURE_WORDS, TEST_WORDS].flatMap((words) => Object.values(words)),
  NO_P_VALUE,
]);

/** A comparison a sponsor posted with an outcome, as the bundle gives it. */
export interface PostedComparison {
  p_value: string | null;
  method: string | null;
  test: string | null;
}

/** "p = 0.03, t-test, 2 sided (superiority test)". The p value is the registry's own text. */
export function comparisonText(comparison: PostedComparison): string {
  const written = comparison.p_value?.trim();
  const p = !written ? NO_P_VALUE : /^[<>=≤≥]/.test(written) ? `p ${spaced(written)}` : `p = ${written}`;
  const test = comparison.test ? ` (${TEST_WORDS[comparison.test]})` : "";
  return [p, comparison.method].filter(Boolean).join(", ") + test;
}

// "<0.001" reads as "p < 0.001".
function spaced(written: string): string {
  return written.replace(/^([<>=≤≥]=?)\s*/, "$1 ");
}
