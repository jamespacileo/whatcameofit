// The record strip (openspec record-strip): a claim's dated records as marks on one
// time axis. Every strip on the site shares one scale, from a start year fixed at build
// to the day the registries were last checked, so a date falls at the same place in
// every strip. Pure: a claim and two dates in, positions and counts out.
//
// The strip shows where dates fall and nothing else. A mark is never placed by
// estimate, a promise mark does not know whether its date has passed, and marks of one
// kind are one size.
import type { ExportedClaim } from "./export";
import { assertRowSentence } from "./row-sentences.ts";
import { withResults } from "./trial-facts.ts";

/** The kinds of mark, each with its own shape or position on the strip. */
export type StripMarkKind = "report" | "record" | "results" | "decision" | "promise";

export interface StripMark {
  kind: StripMarkKind;
  /** The day the mark stands for. */
  date: string;
  /** Where it falls on the axis: 0 at the start year, 1 at the last check. */
  at: number;
}

export interface StripCounts {
  trials: number;
  /** Trials with results posted, counted as the claim page counts them. */
  results: number;
}

export interface Strip {
  marks: StripMark[];
  /** Null when the export holds no list of trials for the claim: never worked out
   * another way. */
  counts: StripCounts | null;
  /** News reports with a date, and dated records, for the text alternative. */
  reports: number;
  records: number;
}

/** The years between two notches under the axis. */
export const NOTCH_YEARS = 5;

/** What each mark is called in a key. The site's wording; checked below. */
export const STRIP_KEY: Record<StripMarkKind | "check", string> = {
  report: "News report",
  record: "Registry record",
  results: "Results posted",
  decision: "Regulator decision",
  promise: "Promised date",
  check: "Registries last checked",
};

/** The order a key lists the marks in: as a reader meets them, left to right. */
export const STRIP_KEY_ORDER: (StripMarkKind | "check")[] = [
  "record",
  "results",
  "decision",
  "report",
  "promise",
  "check",
];

const MARK_OF: Record<string, StripMarkKind> = {
  trial_results_posted: "results",
  regulatory_decision: "decision",
};

const days = (isoDate: string) => Date.parse(`${isoDate.slice(0, 10)}T00:00:00Z`) / 86_400_000;

/**
 * The year every strip's axis starts at: the earliest dated record or report among the
 * claims, taken down to a multiple of five so it moves rarely and the notches fall on
 * round years. Throws when no claim holds a date: there is no axis to draw.
 */
export function axisStart(claims: ExportedClaim[]): number {
  const dates = claims.flatMap((claim) => [
    ...claim.events.map((event) => event.event_date),
    ...claim.articles.map((article) => article.published_date),
    claim.first_reported_date,
  ]);
  const years = dates.filter((date): date is string => Boolean(date)).map((date) => Number(date.slice(0, 4)));
  if (years.length === 0) throw new Error("No published claim holds a date: the record strip has no axis.");
  return Math.floor(Math.min(...years) / NOTCH_YEARS) * NOTCH_YEARS;
}

/** Where a day falls between the start year and the last check, or null outside them. */
function place(date: string, startYear: number, lastChecked: string): number | null {
  const from = days(`${startYear}-01-01`);
  const to = days(lastChecked);
  const at = (days(date) - from) / (to - from);
  return at >= 0 && at <= 1 ? at : null;
}

/** The notches under the axis: one every five years after the start. */
export function notches(startYear: number, lastChecked: string): { year: number; at: number }[] {
  const out: { year: number; at: number }[] = [];
  for (let year = startYear + NOTCH_YEARS; ; year += NOTCH_YEARS) {
    const at = place(`${year}-01-01`, startYear, lastChecked);
    if (at === null) return out;
    out.push({ year, at });
  }
}

/** A claim's strip: its marks, oldest first, and the counts shown beside it. */
export function stripFor(claim: ExportedClaim, startYear: number, lastChecked: string): Strip {
  const dated: { kind: StripMarkKind; date: string | null }[] = [
    ...claim.events.map((event) => ({ kind: MARK_OF[event.type] ?? ("record" as const), date: event.event_date })),
    ...claim.articles.map((article) => ({ kind: "report" as const, date: article.published_date })),
    // Only a promise whose date the export holds; its place is never estimated.
    ...claim.promises.map((promise) => ({ kind: "promise" as const, date: promise.parsed_date })),
  ];
  const marks: StripMark[] = [];
  for (const { kind, date } of dated) {
    if (!date) continue;
    // A date after the last check has no place on an axis that ends there.
    const at = place(date, startYear, lastChecked);
    if (at !== null) marks.push({ kind, date: date.slice(0, 10), at });
  }
  marks.sort((a, b) => a.date.localeCompare(b.date));

  return {
    marks,
    counts: claim.trials ? { trials: claim.trials.length, results: withResults(claim.trials) } : null,
    reports: marks.filter((mark) => mark.kind === "report").length,
    records: marks.filter((mark) => mark.kind !== "report" && mark.kind !== "promise").length,
  };
}

for (const [name, text] of Object.entries(STRIP_KEY)) assertRowSentence(`strip key: ${name}`, text);
