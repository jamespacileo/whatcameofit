// The home page's day-by-day list (openspec home-day-by-day): everything dated for the
// published claims, newest first, under dated headings. Pure: the day the registries
// were last checked is passed in, and nothing here reads a clock. The page is dated by
// that day, never by the day it is built or read.
import type { ExportedClaim, ExportedEvent, StatusCode } from "./export";
import { changesOf } from "./changes.ts";
import { hasLinkedReport } from "./reports.ts";
import { latestPromise } from "./status.ts";

/** Day headings: this many days up to the day of the last check. */
export const DAY_HEADINGS = 14;
/** The days of the row above the list, which keep a heading even when empty. */
export const WEEK_DAYS = 7;
/** A registry record has a row when dated within this many days of the last check. */
export const RECORD_DAYS = 90;

export type RowKind = "report" | "record" | "promise";

interface RowBase {
  /** The day the row is filed under, as YYYY-MM-DD. */
  date: string;
  claim: ExportedClaim;
}

/** A claim's news reports of one day. The first is the one whose title is quoted. */
export interface ReportRow extends RowBase {
  kind: "report";
  reports: { outlet: string; title: string; url: string }[];
}

export interface RecordRow extends RowBase {
  kind: "record";
  event: ExportedEvent;
  /** Set on the one record row that stands for a change of the claim's status that day. */
  change: { before: StatusCode; code: StatusCode } | null;
}

export interface PromiseRow extends RowBase {
  kind: "promise";
  promise: { description: string; parsed_date: string | null; article_url: string };
}

export type DayRow = ReportRow | RecordRow | PromiseRow;

export interface Heading {
  /** The heading's name in the page's address: "d-2026-11-09", "w-2026-10-26", "y-2017". */
  id: string;
  span: "day" | "week" | "year";
  /** The day, the Monday of the week, or the first day of the year. */
  date: string;
  rows: DayRow[];
}

export interface DayList {
  /** The day the registries were last checked. */
  checked: string;
  headings: Heading[];
  /** Promised dates after the last check, earliest first. */
  toCome: PromiseRow[];
  /** The seven days up to the last check, oldest first, with their news reports. */
  week: { date: string; reports: number }[];
  /** One claim first reported in an earlier year, picked by the date. */
  older: ReportRow | null;
}

const DAY_MS = 864e5;

export function shiftDay(day: string, days: number): string {
  return new Date(Date.parse(`${day}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10);
}

const mondayOf = (day: string) =>
  shiftDay(day, -((new Date(`${day}T00:00:00Z`).getUTCDay() + 6) % 7));

const KIND_ORDER: Record<RowKind, number> = { report: 0, record: 1, promise: 2 };

/** A claim's reports as rows: one per day, its reports of that day in the order the
 * Headlines list gives them. */
function reportRows(claim: ExportedClaim): ReportRow[] {
  const byDay = new Map<string, ReportRow>();
  const articles = [...claim.articles].sort(
    (a, b) => b.published_date.localeCompare(a.published_date) || a.title.localeCompare(b.title),
  );
  for (const article of articles) {
    const row = byDay.get(article.published_date) ?? {
      kind: "report" as const,
      date: article.published_date,
      claim,
      reports: [],
    };
    row.reports.push({ outlet: article.outlet, title: article.title, url: article.url });
    byDay.set(article.published_date, row);
  }
  return [...byDay.values()];
}

/** A claim's records dated in the window, oldest event first. The first record on a
 * day the status changed says so; any other shows the status now. */
function recordRows(claim: ExportedClaim, from: string, to: string): RecordRow[] {
  const changes = changesOf(claim).filter((change) => change.before !== null);
  const said = new Set<string>();
  return [...claim.events]
    .filter((event) => event.event_date > from && event.event_date <= to)
    .sort((a, b) => a.event_date.localeCompare(b.event_date) || a.id - b.id)
    .map((event) => {
      const onDay = changes.filter((change) => change.on === event.event_date);
      const first = onDay.length > 0 && !said.has(event.event_date);
      if (first) said.add(event.event_date);
      return {
        kind: "record" as const,
        date: event.event_date,
        claim,
        event,
        // Two changes on one day read as one: from the status before the first to the last.
        change: first ? { before: onDay[0].before!, code: onDay[onDay.length - 1].code } : null,
      };
    });
}

function headingOf(day: string, checked: string): Pick<Heading, "id" | "span" | "date"> {
  if (day > shiftDay(checked, -DAY_HEADINGS)) return { id: `d-${day}`, span: "day", date: day };
  if (day.slice(0, 4) === checked.slice(0, 4)) {
    const monday = mondayOf(day);
    return { id: `w-${monday}`, span: "week", date: monday };
  }
  return { id: `y-${day.slice(0, 4)}`, span: "year", date: `${day.slice(0, 4)}-01-01` };
}

/** How many rows of each kind a list of rows holds. */
export function countKinds(rows: { kind: RowKind }[]): Record<RowKind, number> {
  const counts = { report: 0, record: 0, promise: 0 };
  for (const row of rows) counts[row.kind] += 1;
  return counts;
}

/**
 * The list for a set of published claims, dated by the day the registries were last
 * checked. Null when that day is not known: no other day stands in for it.
 */
export function dayList(claims: ExportedClaim[], lastChecked: string | null): DayList | null {
  if (!lastChecked) return null;
  const checked = lastChecked.slice(0, 10);
  const recordsFrom = shiftDay(checked, -RECORD_DAYS);

  const rows: DayRow[] = [];
  const toCome: PromiseRow[] = [];
  for (const claim of claims) {
    // A report dated after the last check has no heading to stand under.
    rows.push(...recordRows(claim, recordsFrom, checked));
    if (!hasLinkedReport(claim)) continue;
    rows.push(...reportRows(claim).filter((row) => row.date <= checked));
    const promise = latestPromise(claim);
    if (promise) {
      const row: PromiseRow = { kind: "promise", date: promise.parsed_date!, claim, promise };
      (row.date > checked ? toCome : rows).push(row);
    }
  }
  const within = (a: DayRow, b: DayRow) =>
    KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || a.claim.headline.localeCompare(b.claim.headline);
  rows.sort((a, b) => b.date.localeCompare(a.date) || within(a, b));
  toCome.sort((a, b) => a.date.localeCompare(b.date) || within(a, b));

  const week = Array.from({ length: WEEK_DAYS }, (_, index) => {
    const date = shiftDay(checked, index - (WEEK_DAYS - 1));
    const reports = claims
      .filter(hasLinkedReport)
      .flatMap((claim) => claim.articles)
      .filter((article) => article.published_date === date).length;
    return { date, reports };
  });

  const byId = new Map<string, Heading>();
  for (const { date } of week) byId.set(`d-${date}`, { id: `d-${date}`, span: "day", date, rows: [] });
  for (const row of rows) {
    const at = headingOf(row.date, checked);
    const heading = byId.get(at.id) ?? { ...at, rows: [] };
    heading.rows.push(row);
    byId.set(at.id, heading);
  }
  const headings = [...byId.values()].sort((a, b) => b.date.localeCompare(a.date));

  return { checked, headings, toCome, week, older: olderClaim(claims, checked) };
}

/**
 * One claim first reported before the year of `day`, the same for every reader that
 * day and a different one the next: the day of the year picks from the claims in the
 * order they were first reported. Shown as its newest report.
 */
export function olderClaim(claims: ExportedClaim[], day: string): ReportRow | null {
  const yearStart = `${day.slice(0, 4)}-01-01`;
  const earlier = claims
    .filter(
      (claim) =>
        claim.first_reported_date !== null &&
        claim.first_reported_date < yearStart &&
        hasLinkedReport(claim) &&
        claim.articles.length > 0,
    )
    .sort(
      (a, b) =>
        a.first_reported_date!.localeCompare(b.first_reported_date!) ||
        a.slug.localeCompare(b.slug),
    );
  if (earlier.length === 0) return null;
  const dayOfYear = Math.round((Date.parse(`${day}T00:00:00Z`) - Date.parse(`${yearStart}T00:00:00Z`)) / DAY_MS);
  return reportRows(earlier[dayOfYear % earlier.length])[0];
}

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/** "Saturday 14 November". */
export function dayName(day: string): string {
  const date = new Date(`${day}T00:00:00Z`);
  return `${WEEKDAYS[date.getUTCDay()]} ${date.getUTCDate()} ${MONTH_NAMES[date.getUTCMonth()]}`;
}

/** A heading as the list names it: a day, "Week of 26 October", or a year. */
export function headingTitle(heading: Pick<Heading, "span" | "date">): string {
  if (heading.span === "day") return dayName(heading.date);
  if (heading.span === "year") return heading.date.slice(0, 4);
  const date = new Date(`${heading.date}T00:00:00Z`);
  return `Week of ${date.getUTCDate()} ${MONTH_NAMES[date.getUTCMonth()]}`;
}

/** The line that opens the promised dates after the last check. */
export function toComeText(count: number): string {
  return `${count} promised ${count === 1 ? "date" : "dates"} to come.`;
}

/** What the control under the list says is still out of sight. */
export function earlierText(rows: number): string {
  return `${rows} earlier ${rows === 1 ? "row" : "rows"}`;
}

const KIND_WORDS: [RowKind, string, string][] = [
  ["report", "report", "reports"],
  ["record", "registry record", "registry records"],
  ["promise", "promised date", "promised dates"],
];

/** What a heading holds: "2 reports, 1 registry record". With no row, that nothing is dated. */
export function countsText(counts: Record<RowKind, number>): string {
  const parts = KIND_WORDS.filter(([kind]) => counts[kind] > 0).map(
    ([kind, one, many]) => `${counts[kind]} ${counts[kind] === 1 ? one : many}`,
  );
  return parts.length > 0 ? parts.join(", ") : "Nothing dated";
}

/** What makes two record rows the same record: its source, what it recorded and the day. */
export function recordKey(row: RecordRow): string {
  const { event } = row;
  return [event.trial_id ?? event.source_url, event.type, event.trial_state ?? "", row.date].join("|");
}

/** A day's rows with the rows of one registry record brought together. A trial is often
 * matched to several claims and so listed once for each; the first of those rows stays
 * where it stood and the rest follow straight after it, marked as following, so the
 * list can draw the record once and the other claims as short lines under it. Every
 * other row keeps its place. */
export function gatherRecords(rows: DayRow[]): { row: DayRow; follows: boolean }[] {
  const groups: DayRow[][] = [];
  const byKey = new Map<string, DayRow[]>();
  for (const row of rows) {
    const key = row.kind === "record" ? recordKey(row) : null;
    const group = key ? byKey.get(key) : undefined;
    if (group) {
      group.push(row);
      continue;
    }
    const made = [row];
    groups.push(made);
    if (key) byKey.set(key, made);
  }
  return groups.flatMap((group) => group.map((row, index) => ({ row, follows: index > 0 })));
}

/** How many of a long day's rows are shown before the reader asks for the rest. */
export const DAY_CAP = 5;

/** How many of a day's rows to keep in view. Rows are counted by the ones that lead: a
 * row that follows its record stays with it, so a record is never parted from its other
 * claims. A day is cut only when that hides at least two leading rows; a control that
 * brought back one row would cost more room than the row. */
export function keptRows(follows: boolean[], cap = DAY_CAP): number {
  const leading = follows.filter((follow) => !follow).length;
  if (leading <= cap + 1) return follows.length;
  let seen = 0;
  for (let index = 0; index < follows.length; index += 1) {
    if (follows[index]) continue;
    seen += 1;
    if (seen > cap) return index;
  }
  return follows.length;
}

