// What a returning reader is shown: what is dated since their last visit, and the claims
// they follow. Everything here is worked out in the reader's browser from what the page
// already holds and from two entries in that browser's own storage. Nothing is sent to
// the site. Pure: storage, the clock and the page are passed in.

/** The storage entries. Their values never leave the browser. */
export const VISIT_ENTRY = "home-visit";
export const FOLLOWING_ENTRY = "following";

/** The day of this visit and of the visit before it, as YYYY-MM-DD. */
export interface Visit {
  current: string;
  previous: string | null;
}

const isDay = (value: unknown): value is string =>
  typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);

function parse(raw: string | null): unknown {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * The visit to store for `today`. A second look on the same day keeps the earlier
 * "previous", so what is marked new does not vanish on a reload.
 */
export function nextVisit(raw: string | null, today: string): Visit {
  const stored = parse(raw) as Partial<Visit> | null;
  if (!stored || !isDay(stored.current) || stored.current > today) {
    return { current: today, previous: null };
  }
  if (stored.current === today) {
    return { current: today, previous: isDay(stored.previous) ? stored.previous : null };
  }
  return { current: today, previous: stored.current };
}

export interface Since {
  /** The first day counted, as YYYY-MM-DD. */
  from: string;
  /** True when `from` is the reader's last visit; false for the fixed window. */
  visited: boolean;
}

/** What "since" means for this reader: their last visit, or the last thirty days. */
export function sinceOf(visit: Visit, today: string, days = 30): Since {
  if (visit.previous) return { from: visit.previous, visited: true };
  const start = new Date(`${today}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - days);
  return { from: start.toISOString().slice(0, 10), visited: false };
}

/** A day counts when it is on or after `from` and not after `today`. */
export const isSince = (day: string, from: string, today: string) => day >= from && day <= today;

export interface ChangedPart {
  /** The list on the home page that holds these rows. */
  view: "headlines" | "moved" | "promised";
  text: string;
}

const counted = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;

/** The counts as words, in the order of the lists. A count of none is left out. */
export function changedParts(counts: { reports: number; moves: number; promises: number }): ChangedPart[] {
  const parts: ChangedPart[] = [];
  if (counts.reports > 0) {
    parts.push({ view: "headlines", text: counted(counts.reports, "news report", "news reports") });
  }
  if (counts.moves > 0) {
    parts.push({ view: "moved", text: counted(counts.moves, "status change", "status changes") });
  }
  if (counts.promises > 0) {
    parts.push({
      view: "promised",
      text: counted(counts.promises, "promised date reached", "promised dates reached"),
    });
  }
  return parts;
}

/** A claim the reader follows, as stored: its status in words when they last saw it. */
export interface Followed {
  headline: string;
  status: string;
  /** The day they began following, as YYYY-MM-DD. */
  since: string;
}

/** The followed claims by slug. Anything not in the expected shape is dropped. */
export function readFollowed(raw: string | null): Record<string, Followed> {
  const stored = parse(raw);
  const followed: Record<string, Followed> = {};
  if (!stored || typeof stored !== "object" || Array.isArray(stored)) return followed;
  for (const [slug, entry] of Object.entries(stored as Record<string, Partial<Followed>>)) {
    if (
      entry &&
      typeof entry.headline === "string" &&
      typeof entry.status === "string" &&
      isDay(entry.since)
    ) {
      followed[slug] = { headline: entry.headline, status: entry.status, since: entry.since };
    }
  }
  return followed;
}

export interface FollowedRow {
  slug: string;
  headline: string;
  /** The claim's page, or null when the site no longer lists the claim. */
  page: string | null;
  /** The status now, in words; null when the claim is no longer listed. */
  status: string | null;
  /** The status when the reader last saw it, when it differs from the status now. */
  was: string | null;
}

/**
 * The followed claims as the home page lists them: those whose status has changed
 * first, then the most recently followed. `listed` is the site's lookup of claims.
 */
export function followedRows(
  followed: Record<string, Followed>,
  listed: Record<string, { headline: string; page: string; status: string } | undefined>,
): FollowedRow[] {
  return Object.entries(followed)
    .map(([slug, entry]) => {
      const now = listed[slug];
      return {
        slug,
        headline: now?.headline ?? entry.headline,
        page: now?.page ?? null,
        status: now?.status ?? null,
        was: now && now.status !== entry.status ? entry.status : null,
        since: entry.since,
      };
    })
    .sort(
      (a, b) =>
        Number(b.was !== null) - Number(a.was !== null) ||
        b.since.localeCompare(a.since) ||
        a.headline.localeCompare(b.headline),
    )
    .map(({ since: _since, ...row }) => row);
}
