// What the extension page says about the extension (openspec landing-pages-and-guide).
// Everything here restates something held elsewhere, and a site test compares each
// list with its source: the popup's own words with the extension's view, the
// permissions with its manifest. What is sent and kept follows the privacy page, which
// stays the full account.
import { STAGE_PATH, STATUS_LABELS, type StatusCode } from "./status.ts";

/**
 * The pair a landing page shows at work. Chosen by rule, never by hand: a status on the
 * path comes first, then a change of status on record (so the extension page can draw the
 * popup's followed list), then the most trials. The address settles a tie, so a rebuild
 * picks the same one. Takes the bundle's pair pages.
 */
export function examplePair(pages: readonly any[]): any | null {
  return examplePairs(pages)[0] ?? null;
}

/** Every pair, in the order `examplePair` prefers them. */
export function examplePairs(pages: readonly any[]): any[] {
  const rank = (page: any) => [
    STAGE_PATH.includes(page.row.status.code) ? 0 : 1,
    latestChange(page) ? 0 : 1,
    -page.trials.length,
  ];
  return [...pages].sort((a, b) => {
    const [ra, rb] = [rank(a), rank(b)];
    for (let index = 0; index < ra.length; index += 1) {
      if (ra[index] !== rb[index]) return ra[index] - rb[index];
    }
    return a.row.pair.address < b.row.pair.address ? -1 : 1;
  });
}

/** The popup's own labels, as `extension/src/view.js` names and words them. */
export const POPUP_WORDS = {
  standing: "Where it stands",
  firstReported: "First reported",
  latestPromise: "Latest promise",
  open: "See the evidence",
  follow: "Keep me up to date",
  again: "Search again",
  remindMe: "Remind me to look again:",
  inSixMonths: "in six months",
  inAYear: "in a year",
  recent: "Recently checked",
  following: "Following",
  back: "Back",
  stop: "Stop following",
  changed: "Changed",
  keptHere: "Kept in this browser only. Never sent anywhere.",
} as const;

/** Sentences the popup writes in place, in an automatic answer. */
export const POPUP_LINES = {
  automatic: "Automatic · Unreviewed",
  medical: "Not medical advice. A trial is not a treatment option.",
  settings: "Automatic search settings",
  sources: "Sources & privacy",
  answerSettings: "Settings",
} as const;

/** The line under the notices, in the extension's words. */
export const lastChecked = (date: string) => `Registries last checked ${date}.`;

/** What the popup says of a followed pair that has moved, in the extension's words. */
export const wasNow = (was: string, now: string) => `Was: ${was}. Now: ${now}.`;

/** How the popup counts the records an automatic search lists. */
export const possibleMatches = (count: number) =>
  `${count} possible ${count === 1 ? "match" : "matches"}`;

export interface RegistryRecord {
  /** The registry's own identifier. */
  id: string;
  /** The record in its registry. */
  url: string | null;
  phase: string | null;
  state: string | null;
}

const PHASE_ORDER = ["PHASE1", "PHASE2", "PHASE3", "PHASE4"];

/**
 * A pair's trial records, furthest phase first, as an automatic search would list them:
 * identifier, phase and the trial's state, in the words the pair page uses (`pairView`).
 * Only records the bundle holds; nothing is made up for the drawing.
 */
export function registryRecords(page: any, trials: { nctId: string; phases: string | null; state: string; registryUrl: string }[], atMost = 2): RegistryRecord[] {
  const furthest = new Map<string, number>(
    page.trials.map((trial: any) => [trial.nct_id, Math.max(-1, ...(trial.facts.phases ?? []).map((phase: string) => PHASE_ORDER.indexOf(phase)))]),
  );
  return [...trials]
    .sort((a, b) => furthest.get(b.nctId)! - furthest.get(a.nctId)! || (a.nctId < b.nctId ? 1 : -1))
    .slice(0, atMost)
    .map((trial) => ({ id: trial.nctId, url: trial.registryUrl, phase: trial.phases, state: trial.state }));
}

/** The pair's latest change of status, when its history holds one: from, to and the day. */
export function latestChange(page: any) {
  const changes = [...page.history].sort((a: any, b: any) => (a.on < b.on ? -1 : 1));
  const last = changes.at(-1);
  if (!last?.before) return null;
  return { was: STATUS_LABELS[last.before as StatusCode], now: STATUS_LABELS[last.after as StatusCode], on: last.on };
}

export interface Permission {
  /** The name the browser's manifest gives it. */
  name: string;
  /** What a reader would call it. */
  plain: string;
  use: string;
}

/** Every permission in the extension's manifest, each with what it is used for. */
export const PERMISSIONS: Permission[] = [
  {
    name: "activeTab",
    plain: "The tab you are on, when you open the extension",
    use: "Reads that tab's address to see whether its report is tracked. It cannot see a tab you have not opened it on.",
  },
  {
    name: "scripting",
    plain: "Reading the open page",
    use: "Reads the page's words for an automatic search, only on a page that is not tracked and only once you have allowed it.",
  },
  {
    name: "storage",
    plain: "Keeping things in this browser",
    use: "Holds the lookup file, the pages you checked recently, what you follow and your reminders.",
  },
  {
    name: "alarms",
    plain: "A timer",
    use: "Fetches the lookup file twice a day, so something you follow that moves can be noticed.",
  },
  {
    name: "notifications",
    plain: "Notifications",
    use: "Tells you when something you follow has moved, or a reminder you set is due. The browser may ask you first.",
  },
];

/** The hosts the extension may reach, besides the site itself. */
export const HOSTS: { host: string; use: string }[] = [
  {
    host: "t.co",
    use: "Opens up to three of X's shortened links in a post, without cookies, to learn which article the post leads to.",
  },
];

export interface LedgerRow {
  when: string;
  /** What leaves the browser. `nothing` rows are drawn with the word itself. */
  sent: string | null;
  sentNote: string;
  to: string;
  kept: string;
}

/** What the extension sends and keeps, by moment. The privacy page is the full account. */
export const LEDGER: LedgerRow[] = [
  {
    when: "You open it on a report this site tracks",
    sent: null,
    sentNote: "The page's address is compared with a public file inside your browser.",
    to: "Nowhere",
    kept: "The page's address and title, the date and what was found, among your ten most recent checks.",
  },
  {
    when: "You open it on a page this site does not track, having allowed automatic search",
    sent: "The page's words and outgoing links, or only the words you selected. With nothing selected, the page's address with tracking removed. If the words are not enough, one reduced image of what is visible.",
    sentNote: "Asked for before the first search. Turned off in Automatic search settings.",
    to: "This site's service, then OpenAI. Treatment and condition names go to ClinicalTrials.gov, Europe PMC and OpenAlex; organisation names to ROR.",
    kept: "In your browser, up to ten answers for 24 hours, with no page words and no image. This site's service stores neither; for a report anyone can read, it may keep the answer for 24 hours. OpenAI may hold what it received for up to 30 days to monitor abuse.",
  },
  {
    when: "When you open it, and twice a day while it is installed",
    sent: "A request for the public lookup file.",
    sentNote: "It carries no page address, nothing you checked and nothing about you.",
    to: "This site",
    kept: "The file and when it was fetched.",
  },
  {
    when: "You follow a treatment or set a reminder",
    sent: null,
    sentNote: "The list is read against the lookup file inside your browser.",
    to: "Nowhere",
    kept: "The status as it stood when you last looked, and the reminder's day until it is shown.",
  },
];
