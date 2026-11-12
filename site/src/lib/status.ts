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
        `Verdict wording "${found[0]}" in a status label: "${text}". Statuses describe records only.`,
      );
    }
  }
}

assertNeutral([
  ...Object.values(STATUS_LABELS),
  ...Object.values(STATUS_MEANINGS),
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
