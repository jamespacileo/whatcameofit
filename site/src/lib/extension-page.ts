// What the extension page says about the extension (openspec landing-pages-and-guide).
// Everything here restates something held elsewhere, and a site test compares each
// list with its source: the popup's own words with the extension's view, the
// permissions with its manifest. What is sent and kept follows the privacy page, which
// stays the full account.
import type { ExportedClaim } from "./export";
import { confidenceLabel } from "./confidence.ts";
import { STAGE_PATH, STATUS_LABELS, latestPromise } from "./status.ts";

/**
 * The claim a landing page shows at work. Chosen by rule, never by hand: it must have
 * a news report to quote; then a status on the path comes first, then a dated promise,
 * then the most news reports. The slug settles a tie, so a rebuild picks the same one.
 */
export function exampleClaim(claims: readonly ExportedClaim[]): ExportedClaim | null {
  const rank = (claim: ExportedClaim) => [
    STAGE_PATH.includes(claim.status.code) ? 0 : 1,
    latestPromise(claim) ? 0 : 1,
    -claim.articles.length,
  ];
  const reported = claims.filter((claim) => claim.articles.length > 0);
  const ordered = [...reported].sort((a, b) => {
    const [ra, rb] = [rank(a), rank(b)];
    for (let index = 0; index < ra.length; index += 1) {
      if (ra[index] !== rb[index]) return ra[index] - rb[index];
    }
    return a.slug < b.slug ? -1 : 1;
  });
  return ordered[0] ?? null;
}

/** The report a reader would have been reading: the claim's earliest, as the outlet titled it. */
export function firstReport(claim: ExportedClaim) {
  return [...claim.articles].sort((a, b) => (a.published_date < b.published_date ? -1 : 1))[0];
}

/** The popup's own labels, as `extension/src/view.js` names and words them. */
export const POPUP_WORDS = {
  standing: "Where it stands",
  firstReported: "First reported",
  latestPromise: "Latest promise",
  open: "See the evidence",
  follow: "Keep me up to date",
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
} as const;

/** The line under the notices, in the extension's words. */
export const lastChecked = (date: string) => `Registries last checked ${date}.`;

/** What the popup says of a followed claim that has moved, in the extension's words. */
export const wasNow = (was: string, now: string) => `Was: ${was}. Now: ${now}.`;

/** How the popup counts the records an automatic search lists. */
export const possibleMatches = (count: number) =>
  `${count} possible ${count === 1 ? "match" : "matches"}`;

export interface RegistryRecord {
  /** The registry's own identifier: the export holds no trial titles. */
  id: string;
  phase: string | null;
  state: string | null;
  confidence: string;
}

const PHASE_ORDER = ["phase_1", "phase_2", "phase_3", "phase_4"];
const phaseWords = (phases: string[]) =>
  phases.length === 0 ? null : phases.map((phase) => phase.replace("phase_", "Phase ")).join(" / ");
const stateWords = (state: string) => state.charAt(0).toUpperCase() + state.slice(1);

/**
 * The trial records matched to a claim, furthest phase first, as an automatic search
 * would list them: identifier, phase, the trial's latest state, and the match's score in
 * the site's words. Only records the export holds; nothing is made up for the drawing.
 */
export function registryRecords(claim: ExportedClaim, atMost = 2): RegistryRecord[] {
  const records = (claim.matches ?? []).flatMap((match) => {
    const events = claim.events.filter((event) => event.trial_id === match.external_id);
    if (events.length === 0) return [];
    const phases = events.find((event) => event.trial_phases.length > 0)?.trial_phases ?? [];
    const states = events
      .filter((event) => event.trial_state)
      .sort((a, b) => (a.event_date < b.event_date ? 1 : -1));
    const furthest = Math.max(-1, ...phases.map((phase) => PHASE_ORDER.indexOf(phase)));
    return [
      {
        furthest,
        record: {
          id: match.external_id,
          phase: phaseWords(phases),
          state: states[0]?.trial_state ? stateWords(states[0].trial_state) : null,
          confidence: confidenceLabel(match.score),
        },
      },
    ];
  });
  return records
    .sort((a, b) => b.furthest - a.furthest || (a.record.id < b.record.id ? 1 : -1))
    .slice(0, atMost)
    .map((entry) => entry.record);
}

/** The claim's latest change of status, when its history holds one: from, to and the day. */
export function latestChange(claim: ExportedClaim) {
  const history = claim.status.history ?? [];
  if (history.length < 2) return null;
  const [before, after] = history.slice(-2);
  return { was: STATUS_LABELS[before.code], now: STATUS_LABELS[after.code], on: after.on };
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
    use: "Holds the lookup file, the pages you checked recently, the claims you follow and your reminders.",
  },
  {
    name: "alarms",
    plain: "A timer",
    use: "Fetches the lookup file twice a day, so a followed claim that moves can be noticed.",
  },
  {
    name: "notifications",
    plain: "Notifications",
    use: "Tells you when a claim you follow has moved, or a reminder you set is due. The browser may ask you first.",
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
    when: "You follow a claim or set a reminder",
    sent: null,
    sentNote: "The list is read against the lookup file inside your browser.",
    to: "Nowhere",
    kept: "The claim as it stood when you last looked, and the reminder's day until it is shown.",
  },
];
