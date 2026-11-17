// The home page's lists, worked out once (openspec landing-rows-on-demand). The page
// draws each list's first rows; the files under /rows hold the rest, which the page
// fetches the first time a reader asks for them. Both read the lists from here, so a
// row is the same wherever it is drawn and the counts on the page are the lists' own.
import { calendarByMonth } from "./anniversaries";
import { dayList } from "./day-list";
import { data, listedTopics } from "./export";
import { longestWithoutSignal, promisesByDate, statusMoves } from "./feed";
import { recentReports } from "./reports";
import { latestPromise } from "./status";

/** How many rows of a tabbed list are in the page as built, and one page of its pager. */
export const PAGE_SIZE = 10;

export const reports = recentReports(data.claims, Infinity);
export const moves = statusMoves(data.claims);
export const promised = promisesByDate(data.claims);
export const quiet = longestWithoutSignal(data.claims);
// Every published claim once, by the day it was first reported, newest first; a claim
// with no day comes last, by name. A date, never a rank.
export const everyClaim = [...data.claims].sort((a, b) => {
  if (a.first_reported_date && b.first_reported_date && a.first_reported_date !== b.first_reported_date) {
    return a.first_reported_date < b.first_reported_date ? 1 : -1;
  }
  if (a.first_reported_date !== b.first_reported_date) return a.first_reported_date ? -1 : 1;
  return a.intervention.name.localeCompare(b.intervention.name);
});

// The headlines table sets the promise beside the status, as a claim page does. With no
// dated promise among the reports there is no amber column.
export const anyPromise = reports.some((report) => latestPromise(report.claim) !== null);
export const anyClaimPromise = everyClaim.some((claim) => latestPromise(claim) !== null);

export const FEED_VIEWS = ["headlines", "claims", "moved", "promised", "quiet"] as const;
export type FeedView = (typeof FEED_VIEWS)[number];

/** How many rows each tabbed list has in all. */
export const feedTotals: Record<FeedView, number> = {
  headlines: reports.length,
  claims: everyClaim.length,
  moved: moves.length,
  promised: promised.length,
  quiet: quiet.length,
};

/** The date of every dated row of a list, in the list's order: what the line about a
 * reader's last visit counts, without the rows themselves. */
export const feedDates: Partial<Record<FeedView, string[]>> = {
  headlines: reports.map((report) => report.publishedDate),
  moved: moves.map((move) => move.on),
  promised: promised.flatMap((claim) => latestPromise(claim)?.parsed_date ?? []),
};

// The lists can be narrowed to one topic; the counts on the path follow the topic.
export const topicChoices = listedTopics
  .map((topic) => ({
    ...topic,
    count: data.claims.filter((claim) => claim.vertical === topic.slug).length,
  }))
  .sort((a, b) => a.title.localeCompare(b.title));

// Everything dated, under dated headings. Null when the export does not say when the
// registries were last checked: then the four lists follow the lookup, as before.
export const days = data.claims.length > 0 ? dayList(data.claims, data.last_checked_at) : null;
/** The day-by-day list's rows that are not in the page as built: the headings before
 * its day headings, and the promised dates still to come. */
export const daysLater = {
  headings: days?.headings.filter((heading) => heading.span !== "day") ?? [],
  toCome: days?.toCome ?? [],
};
export const daysLaterRows = daysLater.headings.reduce((sum, heading) => sum + heading.rows.length, 0);

// Every day of the calendar that has a first report. The reader's own today picks
// which is shown, so the page is true whenever it is read.
export const calendarDays = calendarByMonth(data.claims).flatMap((month) => month.days);

/** Where the rest of a list's rows are, or nothing for a list that is whole in the page. */
export function restOf(list: FeedView | "latest"): string | undefined {
  const later =
    list === "latest" ? daysLaterRows + daysLater.toCome.length : feedTotals[list] - PAGE_SIZE;
  return later > 0 ? `/rows/${list}.txt` : undefined;
}

/** Where one calendar day's first reports are. */
export const anniversaryRows = (id: string) => `/rows/on-this-day/${id}.txt`;
