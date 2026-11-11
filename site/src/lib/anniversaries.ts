// Anniversaries of first reports. Pure: the date is passed in, nothing is read.
import type { ExportedClaim } from "./export";

export interface CalendarEntry {
  claim: ExportedClaim;
  /** The year the claim was first reported. */
  year: number;
}

export interface CalendarDay {
  /** "MM-DD", as the page marks it. */
  id: string;
  month: number;
  day: number;
  entries: CalendarEntry[];
}

export interface CalendarMonth {
  month: number;
  days: CalendarDay[];
}

export interface Anniversary {
  /** The anniversary date, ISO. */
  date: string;
  /** Whole years from the first report to the anniversary date. */
  years: number;
  claim: ExportedClaim;
}

const pad = (n: number) => String(n).padStart(2, "0");
const isLeap = (year: number) => (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;

function parts(isoDate: string): [number, number, number] {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return [year, month, day];
}

/** Published claims by the month and day of their first report, in calendar order. */
export function calendarByMonth(claims: ExportedClaim[]): CalendarMonth[] {
  const days = new Map<string, CalendarDay>();
  for (const claim of claims) {
    if (!claim.first_reported_date) continue;
    const [year, month, day] = parts(claim.first_reported_date);
    const id = `${pad(month)}-${pad(day)}`;
    const entry = days.get(id) ?? { id, month, day, entries: [] };
    entry.entries.push({ claim, year });
    days.set(id, entry);
  }
  const months = new Map<number, CalendarMonth>();
  for (const day of [...days.values()].sort((a, b) => a.id.localeCompare(b.id))) {
    day.entries.sort((a, b) => a.year - b.year || a.claim.headline.localeCompare(b.claim.headline));
    const month = months.get(day.month) ?? { month: day.month, days: [] };
    month.days.push(day);
    months.set(day.month, month);
  }
  return [...months.values()];
}

/** Anniversaries in the thirty days up to and including `today`, newest first. */
export function recentAnniversaries(claims: ExportedClaim[], today: string): Anniversary[] {
  const [todayYear] = parts(today);
  const todayDate = today.slice(0, 10);
  const start = new Date(`${todayDate}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - 29);
  const earliest = start.toISOString().slice(0, 10);

  const found: Anniversary[] = [];
  for (const claim of claims) {
    if (!claim.first_reported_date) continue;
    const [year, month, day] = parts(claim.first_reported_date);
    for (const onYear of [todayYear - 1, todayYear]) {
      const years = onYear - year;
      if (years < 1) continue;
      const shifted = month === 2 && day === 29 && !isLeap(onYear) ? 28 : day;
      const date = `${onYear}-${pad(month)}-${pad(shifted)}`;
      if (date >= earliest && date <= todayDate) found.push({ date, years, claim });
    }
  }
  return found.sort(
    (a, b) => b.date.localeCompare(a.date) || a.claim.headline.localeCompare(b.claim.headline),
  );
}
