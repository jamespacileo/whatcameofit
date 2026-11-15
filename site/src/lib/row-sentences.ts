// What the records add to a news report, as sentences on a home page row (openspec
// home-day-by-day). Each is built by a fixed rule from a count or a date the export
// holds; a sentence whose count the export does not hold is left out, never estimated.
// A build fails rather than let one of them judge: see the checks at the foot.
import type { ExportedClaim } from "./export";
import { assertNeutral } from "./status.ts";
import { assertNoOutcomeVerdict, withResults } from "./trial-facts.ts";
import { formatDate } from "./timetable.ts";

/** A report row carries at most this many sentences: the first that apply. */
export const SENTENCES_SHOWN = 2;

/** The first registered trial is said only when this many calendar years before the report. */
export const YEARS_BEFORE = 2;

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;

// The site's own wording. Each takes counts and years only.
const TEMPLATES = {
  /** After a regulator's decision, given in the record's own words. */
  dated: (day: string) => `Dated ${formatDate(day)}.`,
  firstTrial: (year: number, before: number) =>
    `The first trial was registered in ${year}, ${plural(before, "year", "years")} before this report.`,
  trials: (count: number, completed: number, results: number) =>
    [
      `${plural(count, "trial", "trials")} on record`,
      ...(completed > 0 ? [`${completed} completed`] : []),
      results > 0 ? `${results} with results posted` : "none with results posted",
    ].join(", ") + ".",
  nothingSince: (years: number) =>
    years === 1
      ? "No record is dated in the year since the first report."
      : `No record is dated in the ${years} years since the first report.`,
  /** What a record strip is, said before its sentences to a reader who cannot see it. */
  strip: (sentences: string) => `Records by date. ${sentences}`,
  /** The strip's own sentence, when no other applies: what is dated, and as of when. */
  onFile: (reports: number, records: number, day: string) =>
    `${plural(reports, "news report", "news reports")} and ${
      records === 0 ? "no dated record" : plural(records, "dated record", "dated records")
    } on file as of ${formatDate(day)}.`,
  /** The numerals beside a strip. */
  counts: (trials: number, results: number) =>
    [plural(trials, "trial", "trials"), ...(results > 0 ? [`${results} with results posted`] : [])].join(" · "),
};

/** A sentence that ends as a sentence, whatever the record's own words end with. */
const closed = (text: string) => (/[.!?]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`);

/**
 * Every sentence that applies to a claim's report of `reportDay`, in the order of
 * preference: a regulator's decision, the first registered trial, the trials on record,
 * nothing dated since the first report.
 */
export function sentencesFor(claim: ExportedClaim, reportDay: string): string[] {
  const out: string[] = [];

  const decision = claim.events
    .filter((event) => event.type === "regulatory_decision")
    .sort((a, b) => b.event_date.localeCompare(a.event_date))[0];
  // The decision is the record's own summary; only the date after it is the site's wording.
  if (decision) out.push(`${closed(decision.summary)} ${TEMPLATES.dated(decision.event_date)}`);

  const registered = claim.events
    .filter((event) => event.type === "trial_registered")
    .map((event) => event.event_date)
    .sort()[0];
  if (registered) {
    const before = Number(reportDay.slice(0, 4)) - Number(registered.slice(0, 4));
    if (before >= YEARS_BEFORE) out.push(TEMPLATES.firstTrial(Number(registered.slice(0, 4)), before));
  }

  // Counted as the claim page counts them. An export with no trials for the claim says
  // nothing here: the number is not worked out another way.
  const trials = claim.trials ?? [];
  if (trials.length > 0) {
    const completed = trials.filter((trial) => trial.state === "completed").length;
    out.push(TEMPLATES.trials(trials.length, completed, withResults(trials)));
  }

  const first = claim.first_reported_date;
  const years = claim.status.overlay_years;
  if (first && years && !claim.events.some((event) => event.event_date >= first)) {
    out.push(TEMPLATES.nothingSince(years));
  }

  return out;
}

/** The sentences a report row shows. */
export function rowSentences(claim: ExportedClaim, reportDay: string): string[] {
  return sentencesFor(claim, reportDay).slice(0, SENTENCES_SHOWN);
}

/**
 * The text alternative of a claim's record strip (openspec record-strip): the row's
 * sentences, or, when none applies, how many reports and dated records are on file.
 * `reportDay` is empty where the strip is not beside one report.
 */
export function stripName(
  claim: ExportedClaim,
  reportDay: string,
  onFile: { reports: number; records: number },
  lastChecked: string,
): string {
  // With no report day the years before a report cannot be counted, so that sentence is left out.
  const sentences = rowSentences(claim, reportDay || "0000");
  return TEMPLATES.strip(
    sentences.length > 0 ? sentences.join(" ") : TEMPLATES.onFile(onFile.reports, onFile.records, lastChecked),
  );
}

/** The counts shown in numerals beside a strip. */
export function countsLine(counts: { trials: number; results: number }): string {
  return TEMPLATES.counts(counts.trials, counts.results);
}

// Words that characterise a count or the time between a report and a record. A row
// states the number; the reader makes of it what they will.
const CHARACTERISING_WORDS =
  /\b(still|only|just|yet|finally|despite|already|merely|even|overdue|late|kept|delayed|at last|as many as|as few as|no fewer|no more than)\b/i;

/** Throws when a sentence the site writes judges what it counts. Names the sentence. */
export function assertRowSentence(name: string, text: string): void {
  const found = text.match(CHARACTERISING_WORDS);
  if (found) {
    throw new Error(
      `Characterising wording "${found[0]}" in the row sentence "${name}": "${text}". A row sentence states a count or a date only.`,
    );
  }
  try {
    assertNeutral([text]);
    assertNoOutcomeVerdict([text]);
  } catch (error) {
    throw new Error(`Row sentence "${name}": ${(error as Error).message}`);
  }
}

/** Every template as it reads with ordinary and with edge values, for the check below
 * and for a reader who wants to see the wording in one place. */
export function sampleSentences(templates: typeof TEMPLATES = TEMPLATES): [string, string][] {
  return [
    ["dated", templates.dated("2026-09-03")],
    ["firstTrial", templates.firstTrial(2012, 14)],
    ["trials", templates.trials(5, 3, 2)],
    ["trials", templates.trials(1, 0, 0)],
    ["nothingSince", templates.nothingSince(9)],
    ["nothingSince", templates.nothingSince(1)],
    ["onFile", templates.onFile(1, 0, "2026-11-14")],
    ["onFile", templates.onFile(2, 3, "2026-11-14")],
    ["counts", templates.counts(0, 0)],
    ["counts", templates.counts(5, 2)],
    ["strip", templates.strip(templates.trials(5, 3, 2))],
  ];
}

for (const [name, text] of sampleSentences()) assertRowSentence(name, text);
