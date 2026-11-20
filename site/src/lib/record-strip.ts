// The record strip (DESIGN.md and the claim pages' openspec record-strip, recovered for pairs):
// a pair's dated trial events (GLOSSARY.md: a dated change in a trial's registry record) as
// marks on one time axis ending at the day the registries were last checked; with no such day
// there is no axis and no strip. It shows where dates fall, nothing more: the axis is one weight along its whole
// length and nothing is filled between marks, so a stretch with no mark is time, not an end. A
// kind of mark differs by shape and by where it sits against the axis, so the strip reads the
// same printed, in forced colours and without colour vision: a registry record rises from the
// axis, posted results sit above it, and the last check is a heavier upright that ends the
// axis, short enough that an event on its day still shows above it. One image to a screen
// reader, named by a sentence.
//
// The claim pages' marks for a promised date, a news report and a regulator's decision have
// no pair data behind them and are not drawn: the lab tracks no regulator's decision.
import { escape } from "./blocks.ts";
import type { PairView } from "./pair-view.ts";
import { assertNeutral } from "./status.ts";
import { formatDate } from "./timetable.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";

export type StripMarkKind = "record" | "results";

/** What each mark is called in a key. */
export const STRIP_KEY: Record<StripMarkKind | "check", string> = {
  record: "Trial event",
  results: "Results posted",
  check: "Registries last checked",
};

/** The fixed words of the strip's sentence, checked with its key as every page's words are. */
const NAME_WORDS = ["dated trial event", "dated trial events", "of them results posted", "to the last check on"];
assertNeutral([...Object.values(STRIP_KEY), ...NAME_WORDS]);
assertNoOutcomeVerdict([...Object.values(STRIP_KEY), ...NAME_WORDS]);

/** A notch on the axis every year on a span of this many years or fewer, else every five. */
export const YEARLY_NOTCHES_UP_TO = 15;

export interface Strip {
  startYear: number;
  lastChecked: string;
  notches: { year: number; at: number }[];
  marks: { kind: StripMarkKind; at: number }[];
  counts: Record<StripMarkKind, number>;
}

/** Where a registry date falls, as a time: a month or a year is placed at its start. Only the
 * mark's place uses it; no date is ever written filled in. */
function timeOf(day: string): number {
  const [year, month = "01", date = "01"] = day.split("-");
  return Date.UTC(Number(year), Number(month) - 1, Number(date));
}

/** A pair's strip: every dated event of its trials that the registry recorded (an expected
 * date is not an event yet), up to the day the registries were last checked. Null with no
 * such day (the day a status was worked out is not a check) or no event before it. */
export function stripOf(view: PairView): Strip | null {
  const lastChecked = view.registryChecks.map((check) => check.through).sort().at(-1);
  if (!lastChecked) return null;
  const events = view.trials.flatMap((trial) => trial.events).filter((event) => !event.estimated && event.day <= lastChecked);
  if (events.length === 0) return null;
  const startYear = Number(events.map((event) => event.day).sort()[0].slice(0, 4));
  const start = Date.UTC(startYear, 0, 1);
  const end = timeOf(lastChecked);
  const at = (time: number) => (end === start ? 1 : Math.min(1, Math.max(0, (time - start) / (end - start))));
  const marks = events.map((event) => ({ kind: (event.kind === "results_posted" ? "results" : "record") as StripMarkKind, at: at(timeOf(event.day)) }));
  const step = Number(lastChecked.slice(0, 4)) - startYear <= YEARLY_NOTCHES_UP_TO ? 1 : 5;
  const notches = [];
  for (let year = Math.ceil((startYear + 1) / step) * step; Date.UTC(year, 0, 1) < end; year += step) {
    notches.push({ year, at: at(Date.UTC(year, 0, 1)) });
  }
  const counts = { record: marks.filter((mark) => mark.kind === "record").length, results: marks.filter((mark) => mark.kind === "results").length };
  return { startYear, lastChecked, notches, marks, counts };
}

const percent = (at: number) => `${(at * 100).toFixed(2)}%`;

/** One mark, drawn about its own date at x = 0 on an axis at y = 15. */
function mark(kind: StripMarkKind | "check"): string {
  if (kind === "record") return `<line class="strip-record" x1="0" x2="0" y1="8" y2="15"></line>`;
  if (kind === "results") return `<rect class="strip-results" x="-2.5" y="1" width="5" height="5"></rect>`;
  // From just above the axis to below it: an event on the check's day rises past its top.
  return `<line class="strip-check" x1="0" x2="0" y1="12" y2="21"></line>`;
}

const plural = (n: number, one: string, many: string) => `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;

/** The strip in a sentence, as a screen reader is given it: the events it marks, not the
 * records they are in. */
export function stripName(strip: Strip): string {
  const results = strip.counts.results ? `, ${strip.counts.results.toLocaleString("en-GB")} of them results posted` : "";
  return `${plural(strip.counts.record + strip.counts.results, "dated trial event", "dated trial events")}${results}, from ${strip.startYear} to the last check on ${formatDate(strip.lastChecked)}.`;
}

/** The kinds of mark a strip draws, in the order a key names them, the last check always. */
export function stripKinds(strip: Strip): (StripMarkKind | "check")[] {
  return [...(["record", "results"] as StripMarkKind[]).filter((kind) => strip.counts[kind] > 0), "check"];
}

/** The strip, with its first year and the day of the last check under its ends when `years`. */
export function recordStrip(view: PairView, { years = true }: { years?: boolean } = {}): string {
  const strip = stripOf(view);
  if (!strip) return "";
  // Drawn so a record's line never covers posted results, which sit above it.
  const ordered = [...strip.marks.filter((one) => one.kind === "record"), ...strip.marks.filter((one) => one.kind === "results")];
  return [
    `<span class="record-strip${years ? " has-years" : ""}"><span class="strip-frame">`,
    `<svg class="strip-line" role="img" aria-label="${escape(stripName(strip))}" height="22">`,
    ...strip.notches.map((notch) => `<line class="strip-notch" x1="${percent(notch.at)}" x2="${percent(notch.at)}" y1="15" y2="20"></line>`),
    `<line class="strip-axis" x1="0" x2="100%" y1="15" y2="15"></line>`,
    `<svg x="100%" overflow="visible">${mark("check")}</svg>`,
    ...ordered.map((one) => `<svg x="${percent(one.at)}" overflow="visible">${mark(one.kind)}</svg>`),
    `</svg>`,
    years ? `<span class="strip-years" aria-hidden="true"><span>${strip.startYear}</span><span>Last checked ${escape(formatDate(strip.lastChecked))}</span></span>` : "",
    `</span></span>`,
  ].join("");
}

/** The key to the strip: each mark drawn as the strip draws it, with its name, said once on a
 * page before the first strip and naming only the marks its strips draw. */
export function stripKey(kinds: (StripMarkKind | "check")[]): string {
  return [
    `<div class="strip-key"><ul aria-label="Key to the record strip">`,
    ...kinds.map(
      (kind) =>
        `<li><svg class="strip-line" width="16" height="22" aria-hidden="true"><line class="strip-axis" x1="0" x2="16" y1="15" y2="15"></line><svg x="8" overflow="visible">${mark(kind)}</svg></svg>${escape(STRIP_KEY[kind])}</li>`,
    ),
    `</ul></div>`,
  ].join("");
}
