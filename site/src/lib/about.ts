// What the about page draws and says (openspec landing-pages-and-guide): the years of
// its example pair, the one cited finding, and who runs the site. Pure: no file,
// network or clock.

/** One year of a pair, or a run of years in which nothing is on record. */
export type StripCell =
  | {
      kind: "year";
      year: number;
      /** Registry events dated this year. */
      records: number;
      /** The bundle's records were gathered this year. */
      checked: boolean;
    }
  | { kind: "gap"; from: number; to: number };

const yearOf = (date: string) => Number(date.slice(0, 4));

/**
 * A pair's years in order, from its earliest dated registry event to the year the records
 * were gathered. An event the registry only expects (an estimated date after that year) is
 * left out. Years with nothing in them are joined into one quiet cell.
 */
export function yearStrip(pair: { trials: { events: { day: string }[] }[] }, gatheredAt: string): StripCell[] {
  const checkedYear = yearOf(gatheredAt);
  const recorded = pair.trials.flatMap((trial) => trial.events.map((event) => yearOf(event.day))).filter((year) => year <= checkedYear);
  const cells: StripCell[] = [];
  for (let year = Math.min(checkedYear, ...recorded); year <= checkedYear; year += 1) {
    const cell = {
      kind: "year" as const,
      year,
      records: recorded.filter((other) => other === year).length,
      checked: checkedYear === year,
    };
    const last = cells.at(-1);
    if (cell.records > 0 || cell.checked) cells.push(cell);
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
