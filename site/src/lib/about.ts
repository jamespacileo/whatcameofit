// What the about page draws and says (openspec landing-pages-and-guide): the years of
// its example claim, the one cited finding, and who runs the site. Pure: no file,
// network or clock.
import type { ExportedClaim } from "./export";
import { latestPromise } from "./status.ts";

/** One year of a claim, or a run of years in which nothing is on record. */
export type StripCell =
  | {
      kind: "year";
      year: number;
      /** News reports read that are dated this year. */
      reports: number;
      /** Records dated this year. */
      records: number;
      /** The latest dated promise names this year. */
      promised: boolean;
      /** The registries were last checked this year. */
      checked: boolean;
    }
  | { kind: "gap"; from: number; to: number };

const yearOf = (date: string) => Number(date.slice(0, 4));

/**
 * A claim's years in order, from its earliest report or record to the later of the
 * year the registries were checked and the year its latest promise names. Years with
 * nothing in them are joined into one quiet cell, as the timetable joins them.
 */
export function yearStrip(claim: ExportedClaim, checkedAt: string | null): StripCell[] {
  const promise = latestPromise(claim);
  const promisedYear = promise?.parsed_date ? yearOf(promise.parsed_date) : null;
  const checkedYear = checkedAt ? yearOf(checkedAt) : null;
  const reported = claim.articles.map((article) => yearOf(article.published_date));
  if (claim.first_reported_date) reported.push(yearOf(claim.first_reported_date));
  const recorded = claim.events.map((event) => yearOf(event.event_date));
  const all = [...reported, ...recorded, ...(promisedYear ? [promisedYear] : []), ...(checkedYear ? [checkedYear] : [])];
  if (all.length === 0) return [];

  const cells: StripCell[] = [];
  for (let year = Math.min(...all); year <= Math.max(...all); year += 1) {
    const cell = {
      kind: "year" as const,
      year,
      // The first report's date can repeat an article's: a year is reported once it has either.
      reports: new Set(claim.articles.filter((a) => yearOf(a.published_date) === year).map((a) => a.url)).size ||
        (claim.first_reported_date && yearOf(claim.first_reported_date) === year ? 1 : 0),
      records: recorded.filter((other) => other === year).length,
      promised: promisedYear === year,
      checked: checkedYear === year,
    };
    const empty = cell.reports === 0 && cell.records === 0 && !cell.promised && !cell.checked;
    const last = cells.at(-1);
    if (!empty) cells.push(cell);
    else if (last?.kind === "gap") last.to = year;
    else cells.push({ kind: "gap", from: year, to: year });
  }
  return cells;
}

/** The finding the about page cites, with where it was read and the day. Stated in words on the page. */
export const CITED_FINDING = {
  authors: "Dumas-Mallet, Smith, Boraud and Gonon",
  title: "Poor replication validity of biomedical association studies reported by newspapers",
  journal: "PLOS ONE",
  year: 2017,
  url: "https://doi.org/10.1371/journal.pone.0172650",
  checked: "2026-11-14",
} as const;

/**
 * Who runs the site. The operator is named as the privacy page names them. The
 * sentence on funding is the operator's to word (task 4.4): until it is set here,
 * the page says nothing about funding.
 */
export const WHO_RUNS_IT: { operator: string; funding: string | null } = {
  operator: "James Pacileo",
  funding: null,
};
