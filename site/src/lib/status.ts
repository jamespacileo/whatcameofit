// Words for statuses and events. They describe records; they never judge.
import type { ExportedClaim, ExportedEvent, StatusCode } from "./export";

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
    "No clinical trial was found in the registries checked. The first reports are not recorded as describing a study in people.",
  no_trial_found:
    "The first reports described a study in people. No clinical trial was found in the registries checked.",
  trial_registered: "A clinical trial is registered. No trial with a phase has started.",
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
  no_trial_found: "Studied in people, no registered trial found",
  trial_registered: "A trial in people is registered",
  phase_1: "Early trial in people, checking safety",
  phase_2: "Mid-stage trial in people",
  phase_3: "Large late-stage trial in people",
  approved: "Approved by a regulator",
  failed: "A trial did not meet its main goal",
  terminated: "Its trials were stopped early",
  retracted: "The original paper was retracted",
};

// How a count of claims with one status is said in a sentence: for one claim, for several.
const STATUS_CLAUSES: Record<StatusCode, [one: string, many: string]> = {
  preclinical_only: ["has no trial in people on record", "have no trial in people on record"],
  no_trial_found: [
    "was studied in people with no registered trial found",
    "were studied in people with no registered trial found",
  ],
  trial_registered: ["has a trial in people registered", "have a trial in people registered"],
  phase_1: ["has reached an early trial in people", "have reached early trials in people"],
  phase_2: ["has reached a mid-stage trial in people", "have reached mid-stage trials in people"],
  phase_3: [
    "has reached a large late-stage trial in people",
    "have reached large late-stage trials in people",
  ],
  approved: ["has been approved by a regulator", "have been approved by a regulator"],
  failed: [
    "had a trial that did not meet its main goal",
    "had a trial that did not meet its main goal",
  ],
  terminated: ["had its trials stopped early", "had their trials stopped early"],
  retracted: ["had its original paper retracted", "had their original papers retracted"],
};

export function overlayText(years: number | null): string | null {
  return years === null ? null : `No signal for ${years} ${years === 1 ? "year" : "years"}`;
}

const TRIAL_STATES: Record<string, string> = {
  started: "Trial started",
  completed: "Trial completed",
  terminated: "Trial terminated",
  withdrawn: "Trial withdrawn",
  suspended: "Trial suspended",
};

export function eventLabel(event: ExportedEvent): string {
  switch (event.type) {
    case "followup_paper":
      return "Follow-up paper";
    case "trial_registered":
      return "Trial registered";
    case "trial_status_change":
      return TRIAL_STATES[event.trial_state ?? ""] ?? "Trial status changed";
    case "trial_results_posted":
      return "Trial results posted";
    case "grant_awarded":
      return "Grant awarded";
    case "company_event":
      return "Company event";
    case "retraction":
      return "Retraction notice";
    case "regulatory_decision":
      return event.regulatory_outcome === "approved" ? "Regulatory approval" : "Regulatory refusal";
    default:
      return "Record";
  }
}

const SOURCE_NAMES: Record<string, string> = {
  "clinicaltrials.gov": "ClinicalTrials.gov",
  europepmc: "Europe PMC",
  crossref: "Crossref",
  "manual entry": "Source",
};

export function sourceName(name: string): string {
  return SOURCE_NAMES[name] ?? name;
}

export const EVIDENCE_STAGES: Record<string, string> = {
  in_vitro: "Laboratory (in vitro)",
  animal: "Animal study",
  early_human: "Early human study",
  late_human: "Late human study",
};

export function latestPromise(claim: ExportedClaim) {
  const dated = claim.promises.filter((promise) => promise.parsed_date !== null);
  return dated.sort((a, b) => (a.parsed_date! < b.parsed_date! ? 1 : -1))[0] ?? null;
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
  ...Object.values(TRIAL_STATES),
  overlayText(1)!,
  overlayText(6)!,
]);

// The path a claim can move along. A status off the path (no trial record found,
// failed, terminated, retracted) is shown in words only.
export const STAGE_PATH: StatusCode[] = [
  "preclinical_only",
  "trial_registered",
  "phase_1",
  "phase_2",
  "phase_3",
  "approved",
];

// The most statuses a summary names; the claims at any others are counted together.
const SUMMARY_NAMES = 4;

/**
 * One sentence on where a list's claims stand, from the count at each status alone.
 * Statuses are named in path order, then those off the path. Null for an empty list.
 */
export function topicSummary(counts: ReadonlyMap<StatusCode, number>): string | null {
  const offPath = (Object.entries(STATUS_LABELS) as [StatusCode, string][])
    .map(([code]) => code)
    .filter((code) => !STAGE_PATH.includes(code));
  const present = [...STAGE_PATH, ...offPath].filter((code) => (counts.get(code) ?? 0) > 0);
  const total = present.reduce((sum, code) => sum + counts.get(code)!, 0);
  if (total === 0) return null;
  if (total === 1) {
    return `1 reported breakthrough tracked: it ${STATUS_CLAUSES[present[0]][0]}.`;
  }
  // The sort is stable, so statuses with equal counts keep their path order.
  const named = [...present]
    .sort((a, b) => counts.get(b)! - counts.get(a)!)
    .slice(0, SUMMARY_NAMES);
  const parts = present
    .filter((code) => named.includes(code))
    .map((code) => {
      const count = counts.get(code)!;
      return `${count} ${STATUS_CLAUSES[code][count === 1 ? 0 : 1]}`;
    });
  const rest = total - named.reduce((sum, code) => sum + counts.get(code)!, 0);
  if (rest > 0) parts.push(`${rest} ${rest === 1 ? "is" : "are"} at other statuses`);
  const said =
    parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
  return `Of ${total} reported breakthroughs tracked, ${said}.`;
}

// What kind of record an entry is. Each kind has one drawing, named once in a legend.
export type RecordKind =
  | "report"
  | "trial"
  | "paper"
  | "regulator"
  | "retraction"
  | "grant"
  | "company"
  | "record";

export const KIND_NAMES: Record<RecordKind, string> = {
  report: "News report",
  trial: "Trial registry record",
  paper: "Paper",
  regulator: "Regulator decision",
  retraction: "Retraction notice",
  grant: "Grant",
  company: "Company event",
  record: "Record",
};

export function eventKind(event: ExportedEvent): RecordKind {
  if (event.type.startsWith("trial_")) return "trial";
  switch (event.type) {
    case "followup_paper":
      return "paper";
    case "regulatory_decision":
      return "regulator";
    case "retraction":
      return "retraction";
    case "grant_awarded":
      return "grant";
    case "company_event":
      return "company";
    default:
      return "record";
  }
}
