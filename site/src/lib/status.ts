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
