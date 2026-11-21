// Words for statuses and events. They describe records; they never judge.
/** The status codes, as the bundle's schema spells them. */
export type StatusCode =
  | "preclinical_only"
  | "no_trial_found"
  | "trial_registered"
  | "phase_1"
  | "phase_2"
  | "phase_3"
  | "approved"
  | "failed"
  | "terminated"
  | "retracted";

export const STATUS_LABELS: Record<StatusCode, string> = {
  preclinical_only: "Preclinical only",
  no_trial_found: "No trial record found",
  trial_registered: "Trial registered",
  phase_1: "Phase 1 trial",
  phase_2: "Phase 2 trial",
  phase_3: "Phase 3 trial",
  approved: "Approved",
  failed: "Trial missed its primary endpoint",
  terminated: "Trials ended early",
  retracted: "Origin paper retracted",
};

export const STATUS_MEANINGS: Record<StatusCode, string> = {
  preclinical_only:
    "The confirmed first-report evidence is laboratory or animal work. No clinical trial was found in the registries checked.",
  no_trial_found:
    "No clinical trial was found in the registries checked. This does not establish whether the treatment has been studied in people.",
  trial_registered: "A clinical trial is registered. None that has started has a phase.",
  phase_1: "The furthest trial that has started is a Phase 1 trial.",
  phase_2: "The furthest trial that has started is a Phase 2 trial.",
  phase_3: "The furthest trial that has started is a Phase 3 trial.",
  approved: "A regulator has recorded an approval.",
  failed:
    "A trial result was reported in which the primary endpoint was not met, and no other trial stands.",
  terminated: "Every registered trial was terminated or withdrawn.",
  retracted: "The paper the first news reports were about has been retracted.",
};

// A status in plain words, for a reader who does not know trial phases. A gloss never
// claims more than the meaning above it: "no trial on record" is not "never tested".
export const STATUS_GLOSSES: Record<StatusCode, string> = {
  preclinical_only: "No trial in people on record",
  no_trial_found: "No matching registered trial found",
  trial_registered: "A trial in people is registered",
  phase_1: "Early trial in people, checking safety",
  phase_2: "Mid-stage trial in people",
  phase_3: "Large late-stage trial in people",
  approved: "Approved by a regulator",
  failed: "A trial did not meet its main goal",
  terminated: "Its trials were stopped early",
  retracted: "The original paper was retracted",
};

// A status as the end of a sentence about one pair or several ("12 have reached large
// late-stage trials in people"), for the line that sums a list up. The claims site's wording
// (production commit 4ea7f23, lib/status.ts), kept word for word: each says what the records
// show and no more than its gloss above.
export const STATUS_CLAUSES: Record<StatusCode, [one: string, many: string]> = {
  preclinical_only: ["has no trial in people on record", "have no trial in people on record"],
  no_trial_found: ["has no matching registered trial found", "have no matching registered trial found"],
  trial_registered: ["has a trial in people registered", "have a trial in people registered"],
  phase_1: ["has reached an early trial in people", "have reached early trials in people"],
  phase_2: ["has reached a mid-stage trial in people", "have reached mid-stage trials in people"],
  phase_3: ["has reached a large late-stage trial in people", "have reached large late-stage trials in people"],
  approved: ["has been approved by a regulator", "have been approved by a regulator"],
  failed: ["had a trial that did not meet its main goal", "had a trial that did not meet its main goal"],
  terminated: ["had its trials stopped early", "had their trials stopped early"],
  retracted: ["had its original paper retracted", "had their original papers retracted"],
};

export function overlayText(years: number | null): string | null {
  return years === null ? null : `No signal for ${years} ${years === 1 ? "year" : "years"}`;
}


// A build fails rather than publish a verdict. "No signal" is never worded as an ending.
const VERDICT_WORDS =
  /\b(dead|abandon\w*|scam\w*|hoax\w*|debunk\w*|bogus|fake\w*|quack\w*|fraud\w*)\b/i;

export function assertNeutral(texts: string[]): void {
  for (const text of texts) {
    const found = text.match(VERDICT_WORDS);
    if (found) {
      throw new Error(
        `Verdict wording "${found[0]}" in status wording: "${text}". Statuses describe records only.`,
      );
    }
  }
}

assertNeutral([
  ...Object.values(STATUS_LABELS),
  ...Object.values(STATUS_MEANINGS),
  ...Object.values(STATUS_GLOSSES),
  ...Object.values(STATUS_CLAUSES).flat(),
  overlayText(1)!,
  overlayText(6)!,
]);

// The path a pair can move along. A status off the path (no trial record found,
// failed, terminated, retracted) is shown in words only.
export const STAGE_PATH: StatusCode[] = [
  "preclinical_only",
  "trial_registered",
  "phase_1",
  "phase_2",
  "phase_3",
  "approved",
];

/** Every status off the path, in the order the labels list them. */
export const OFF_PATH: StatusCode[] = (Object.keys(STATUS_LABELS) as StatusCode[]).filter((code) => !STAGE_PATH.includes(code));

/**
 * The places on the path no pair can stand at yet, so a count of none there is not a finding:
 * a pair is made from a registered trial, so none is "preclinical only". The home page says
 * "not followed yet" at such a place rather than 0 (the operator read the zeros as missing
 * data, 2026-11-21). "Approved" left this list when the lab began reading regulators' own
 * records (lab change `regulator-approvals`, pull request 189): a count of none there is now
 * a count. A place with a pair shows its count as any other; take a code out of this list
 * once the bundle can fill it.
 */
export const NOT_FOLLOWED_YET: StatusCode[] = ["preclinical_only"];

/** How many of the rows stand at each status. */
export function statusCounts(rows: { statusCode: string }[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of rows) counts.set(row.statusCode, (counts.get(row.statusCode) ?? 0) + 1);
  return counts;
}

// The most statuses a summary names; the pairs at any others are counted together.
const SUMMARY_NAMES = 4;

/**
 * One sentence on where a list's pairs stand, from the count at each status alone (the claims
 * site's topic summary, on pairs). The statuses with the most pairs are named, in path order
 * and then those off the path, so the sentence reads along the path and never ranks one status
 * above another. Null for an empty list.
 */
export function standingSummary(counts: ReadonlyMap<string, number>): string | null {
  const present = [...STAGE_PATH, ...OFF_PATH].filter((code) => (counts.get(code) ?? 0) > 0);
  const total = present.reduce((sum, code) => sum + counts.get(code)!, 0);
  if (total === 0) return null;
  if (total === 1) return `1 treatment and condition followed: it ${STATUS_CLAUSES[present[0]][0]}.`;
  // "Of 5, 5 have" reads as a slip; every pair at one status is said as all of them.
  if (present.length === 1) return `All ${total} treatments and conditions followed ${STATUS_CLAUSES[present[0]][1]}.`;
  // The sort is stable, so statuses with equal counts keep their path order.
  const named = [...present].sort((a, b) => counts.get(b)! - counts.get(a)!).slice(0, SUMMARY_NAMES);
  const parts = present
    .filter((code) => named.includes(code))
    .map((code) => `${counts.get(code)} ${STATUS_CLAUSES[code][counts.get(code) === 1 ? 0 : 1]}`);
  const rest = total - named.reduce((sum, code) => sum + counts.get(code)!, 0);
  if (rest > 0) parts.push(`${rest} ${rest === 1 ? "is" : "are"} at other statuses`);
  const said = parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
  return `Of ${total} treatments and conditions followed, ${said}.`;
}
