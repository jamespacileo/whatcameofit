// A reminder to look at a claim's record again, as a calendar file made in the
// reader's browser. Nothing here asks the network for anything: the reader's
// calendar holds the date, and the site never learns it.

export type ReminderChoice = "promise" | "six-months" | "year" | "anniversary";

interface Dates {
  /** Today, as YYYY-MM-DD in the reader's own time. */
  today: string;
  /** The date the latest dated promise names, or null when there is none. */
  promiseDue: string | null;
  /** The date of the first report, or null when it is not known. */
  firstReported: string | null;
}

const pad = (value: number) => String(value).padStart(2, "0");

function parts(isoDate: string): [number, number, number] {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return [year, month, day];
}

function iso(year: number, month: number, day: number): string {
  return `${year}-${pad(month)}-${pad(day)}`;
}

function daysIn(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

// A month later on the same day, or on the month's last day when it is shorter:
// six months after 31 August is the last day of February.
function addMonths(isoDate: string, months: number): string {
  const [year, month, day] = parts(isoDate);
  const total = year * 12 + (month - 1) + months;
  const toYear = Math.floor(total / 12);
  const toMonth = (total % 12) + 1;
  return iso(toYear, toMonth, Math.min(day, daysIn(toYear, toMonth)));
}

/**
 * The date a choice stands for, or null when the choice cannot be offered: no
 * dated promise, a promise date that is not in the future, or no first report.
 */
export function reminderDate(choice: ReminderChoice, dates: Dates): string | null {
  const { today, promiseDue, firstReported } = dates;
  if (choice === "six-months") return addMonths(today, 6);
  if (choice === "year") return addMonths(today, 12);
  if (choice === "promise") {
    return promiseDue && promiseDue.slice(0, 10) > today ? promiseDue.slice(0, 10) : null;
  }
  if (!firstReported) return null;
  const [thisYear] = parts(today);
  const [, month, day] = parts(firstReported);
  for (const year of [thisYear, thisYear + 1]) {
    const candidate = iso(year, month, Math.min(day, daysIn(year, month)));
    if (candidate > today) return candidate;
  }
  return null;
}

// Text in a calendar file: a backslash before the characters the format reserves.
function escape(text: string): string {
  return text
    .replaceAll("\\", "\\\\")
    .replaceAll(";", "\\;")
    .replaceAll(",", "\\,")
    .replaceAll(/\r?\n/g, "\\n");
}

// A line is at most 75 bytes; a longer one continues on the next after a space.
function fold(line: string): string {
  const encoder = new TextEncoder();
  const pieces: string[] = [];
  let piece = "";
  let size = 0;
  for (const character of line) {
    const bytes = encoder.encode(character).length;
    const limit = pieces.length === 0 ? 75 : 74;
    if (size + bytes > limit) {
      pieces.push(piece);
      piece = "";
      size = 0;
    }
    piece += character;
    size += bytes;
  }
  pieces.push(piece);
  return pieces.join("\r\n ");
}

interface Reminder {
  /** The site's name, for the event's title. */
  site: string;
  /** The claim's headline. */
  headline: string;
  /** The claim page's address. */
  url: string;
  /** The claim's slug, which makes the event's identity. */
  slug: string;
  /** The day of the event, as YYYY-MM-DD. */
  date: string;
  /** The moment the file is made, as an ISO timestamp. */
  madeAt: string;
}

/** One all-day event that names the claim and links to its page. */
export function calendarFile(reminder: Reminder): string {
  const { site, headline, url, slug, date, madeAt } = reminder;
  const compact = (isoDate: string) => isoDate.slice(0, 10).replaceAll("-", "");
  const [year, month, day] = parts(date);
  const next = new Date(Date.UTC(year, month - 1, day + 1)).toISOString();
  const stamp = `${madeAt.slice(0, 19).replaceAll(/[-:]/g, "")}Z`;
  const host = new URL(url).host;
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    `PRODID:-//${escape(host)}//Reminder//EN`,
    "BEGIN:VEVENT",
    `UID:${slug}-${compact(date)}@${host}`,
    `DTSTAMP:${stamp}`,
    `DTSTART;VALUE=DATE:${compact(date)}`,
    `DTEND;VALUE=DATE:${compact(next)}`,
    `SUMMARY:${escape(`${site} ${headline}`)}`,
    `DESCRIPTION:${escape(`Look at the record again: ${url}`)}`,
    `URL:${url}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ]
    .map(fold)
    .join("\r\n")
    .concat("\r\n");
}
