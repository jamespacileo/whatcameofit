// The claim page's timetable: for each year, what was promised and what was recorded.
import type { ExportedClaim, ExportedEvent } from "./export";

export interface PromisedEntry {
  description: string;
  outlet: string;
  madeOn: string;
  articleUrl: string;
}

export type RecordedEntry =
  | {
      kind: "report";
      date: string;
      outlet: string;
      title: string;
      url: string;
      archiveUrl: string | null;
    }
  | { kind: "event"; date: string; event: ExportedEvent; mark: string; explains: boolean };

export type Row =
  | {
      kind: "year";
      year: number;
      promised: PromisedEntry[];
      recorded: RecordedEntry[];
      current: boolean;
    }
  | { kind: "quiet"; from: number; to: number };

export interface Timetable {
  rows: Row[];
  undated: PromisedEntry[];
  sources: { mark: string; event: ExportedEvent }[];
}

const yearOf = (isoDate: string) => Number(isoDate.slice(0, 4));

function push<Entry>(byYear: Map<number, Entry[]>, year: number, entry: Entry): void {
  byYear.set(year, [...(byYear.get(year) ?? []), entry]);
}

// Footnote marks: a, b, ... z, aa, ab, ...
function footnoteMark(index: number): string {
  let mark = "";
  for (let n = index; n >= 0; n = Math.floor(n / 26) - 1) {
    mark = String.fromCharCode(97 + (n % 26)) + mark;
  }
  return mark;
}

export function buildTimetable(claim: ExportedClaim, generatedAt: string): Timetable {
  const articles = new Map(claim.articles.map((article) => [article.url, article]));
  const promised = new Map<number, PromisedEntry[]>();
  const recorded = new Map<number, RecordedEntry[]>();
  const undated: PromisedEntry[] = [];
  const explaining = new Set(claim.status.explained_by);

  for (const promise of claim.promises) {
    const article = articles.get(promise.article_url);
    const entry: PromisedEntry = {
      description: promise.description,
      outlet: article?.outlet ?? "",
      madeOn: article?.published_date ?? "",
      articleUrl: promise.article_url,
    };
    if (promise.parsed_date === null) undated.push(entry);
    else push(promised, yearOf(promise.parsed_date), entry);
  }

  for (const article of claim.articles) {
    push(recorded, yearOf(article.published_date), {
      kind: "report",
      date: article.published_date,
      outlet: article.outlet,
      title: article.title,
      url: article.url,
      archiveUrl: article.archive_url,
    });
  }

  const sources = claim.events.map((event, index) => ({ mark: footnoteMark(index), event }));
  for (const { mark, event } of sources) {
    push(recorded, yearOf(event.event_date), {
      kind: "event",
      date: event.event_date,
      event,
      mark,
      explains: explaining.has(event.id),
    });
  }
  for (const entries of recorded.values()) entries.sort((a, b) => (a.date < b.date ? -1 : 1));

  const thisYear = yearOf(generatedAt);
  const years = [
    ...Array.from(promised, ([year]) => year),
    ...Array.from(recorded, ([year]) => year),
    thisYear,
  ];
  const first = Math.min(...years);
  const last = Math.max(...years);

  const rows: Row[] = [];
  for (let year = first; year <= last; year++) {
    const isEmpty = !promised.has(year) && !recorded.has(year) && year !== thisYear;
    const previous = rows[rows.length - 1];
    if (isEmpty && previous?.kind === "quiet") previous.to = year;
    else if (isEmpty) rows.push({ kind: "quiet", from: year, to: year });
    else
      rows.push({
        kind: "year",
        year,
        promised: promised.get(year) ?? [],
        recorded: recorded.get(year) ?? [],
        current: year === thisYear,
      });
  }
  return { rows, undated, sources };
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDate(isoDate: string | null): string {
  if (!isoDate) return "";
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

export function dayAndMonth(isoDate: string): string {
  const [, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return `${day} ${MONTHS[month - 1]}`;
}
