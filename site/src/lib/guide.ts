// The guide (openspec landing-pages-and-guide): what an entry is, the checks a build
// runs on the entry files, and which published claims an entry shows at work. Pure: no
// file, network or clock. The entry files are read in guide-entries.ts.
import type { ExportedClaim, StatusCode } from "./export";
import {
  STAGE_PATH,
  STATUS_GLOSSES,
  STATUS_LABELS,
  STATUS_MEANINGS,
  assertNeutral,
  latestPromise,
} from "./status.ts";

export type Shelf = "status" | "site" | "research";

/** The three shelves, in the order the index lists them. */
export const SHELVES: { id: Shelf; title: string; about: string }[] = [
  { id: "status", title: "Statuses", about: "Where a claim can stand, as its page words it." },
  { id: "site", title: "Words this site uses", about: "What this site means by its own terms." },
  {
    id: "research",
    title: "How research is recorded",
    about: "What registries, regulators and journals hold, from their own published pages.",
  },
];

/** The method page's sections an entry's rule can link to. A site test compares them with the page. */
export const METHOD_SECTIONS: Record<string, string> = {
  "how-a-status-is-set": "How a status is set",
  "what-each-status-means": "What each status means",
  "no-signal": "No signal",
  "what-a-trial-entry-shows": "What a trial entry shows",
  "what-this-site-never-says": "What this site never says",
  "where-the-data-comes-from": "Where the data comes from",
  "an-optional-search-of-a-new-report": "An optional search of a new report",
  "ways-to-keep-up": "Ways to keep up",
};

export interface GuideSource {
  name: string;
  url: string;
  /** The day the source was read, as YYYY-MM-DD. */
  checked: string;
}

export interface GuideEntry {
  slug: string;
  shelf: Shelf;
  title: string;
  /** The one sentence that answers. A status entry's is the status's meaning. */
  answer: string;
  /** A status entry's code. */
  status: StatusCode | null;
  /** The same in plain words, for a status entry. */
  gloss: string | null;
  /** Where the entry sits on its shelf. Statuses are ordered by the path instead. */
  order: number;
  /** The method page section that holds the rule using this word. */
  rule: string;
  /** The rule, said in one or two sentences. */
  onSite: string;
  /** Which published claims the word applies to: a key of APPLIES, or null for none. */
  applies: string | null;
  sources: GuideSource[];
  related: string[];
  /** Whether a person has read the entry and set it checked. */
  checked: boolean;
  /** The entry's own text, for the wording checks and the count of words. */
  text: string;
}

/** The address of a status's entry, from its label: "Phase 2 trial" is "phase-2-trial". */
export function statusSlug(code: StatusCode): string {
  return STATUS_LABELS[code]
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

const day = (value: unknown): string =>
  value instanceof Date ? value.toISOString().slice(0, 10) : String(value ?? "");

/**
 * An entry from its file: the name gives the address, the front matter the rest. A
 * status entry takes its title, answer and gloss from the status wording the claim
 * pages read, so they are typed once.
 */
export function readEntry(
  slug: string,
  front: Record<string, unknown>,
  text: string,
): GuideEntry {
  const status = (front.status as StatusCode | undefined) ?? null;
  const known = status !== null && status in STATUS_LABELS;
  return {
    slug,
    shelf: front.shelf as Shelf,
    title: known ? STATUS_LABELS[status] : String(front.title ?? ""),
    answer: known ? STATUS_MEANINGS[status] : String(front.answer ?? ""),
    status,
    gloss: known ? STATUS_GLOSSES[status] : null,
    order: Number(front.order ?? 0),
    rule: String(front.rule ?? ""),
    onSite: String(front.on_site ?? ""),
    applies: known ? status : front.applies ? String(front.applies) : null,
    sources: ((front.sources as Record<string, unknown>[] | undefined) ?? []).map((source) => ({
      name: String(source.name ?? ""),
      url: String(source.url ?? ""),
      checked: day(source.checked),
    })),
    related: ((front.related as unknown[] | undefined) ?? []).map(String),
    checked: front.checked === true,
    text,
  };
}

// An entry describes records. It never tells a reader what to do about their own
// care: these are the turns of phrase that would.
const ADVICE_WORDS =
  /\b(you should|you must|you ought|you need to|we (recommend|advise|suggest)|(should|must) (ask|join|avoid|take|stop|start|try|consider|talk|speak|see)|ask (your|a) (doctor|gp|clinician|pharmacist) (for|to|about|whether)|sign up (for|to)|worth (trying|asking|joining|taking)|(stop|start|keep) taking|is right for you|safe to (take|try|use))\b/i;

/** Throws when a text gives advice, naming the words. The guide's addition to assertNeutral. */
export function assertNoAdvice(texts: string[]): void {
  for (const text of texts) {
    const found = text.match(ADVICE_WORDS);
    if (found) {
      throw new Error(
        `Advice wording "${found[0]}" in a guide entry: "${text.slice(0, 120)}". Entries describe records only.`,
      );
    }
  }
}

/** The two headed parts every entry's text holds, in this order. */
export const ENTRY_PARTS = ["In the records", "What it does not tell you"] as const;

const WORDS = { fewest: 150, most: 500 };
const MOST_SOURCES = 4;
const MOST_RELATED = 5;

const wordCount = (text: string) => text.split(/\s+/).filter(Boolean).length;

/**
 * Everything wrong with the entry files, one line each; empty when the guide may be
 * built. A status without an entry, a research entry without a source, a related entry
 * that does not exist, and verdict or advice wording are each named with their entry.
 */
export function guideProblems(
  entries: readonly GuideEntry[],
  statuses: readonly StatusCode[] = Object.keys(STATUS_LABELS) as StatusCode[],
): string[] {
  const problems: string[] = [];
  const slugs = new Set(entries.map((entry) => entry.slug));
  const shelves = new Set(SHELVES.map((shelf) => shelf.id));

  for (const code of statuses) {
    const held = entries.filter((entry) => entry.status === code);
    if (held.length === 0) {
      problems.push(`The status "${STATUS_LABELS[code] ?? code}" (${code}) has no guide entry.`);
    }
    if (held.length > 1) {
      problems.push(`The status ${code} has ${held.length} guide entries; it takes one.`);
    }
  }

  for (const entry of entries) {
    const say = (problem: string) => problems.push(`Guide entry "${entry.slug}": ${problem}`);
    if (!shelves.has(entry.shelf)) say(`"${entry.shelf}" is not a shelf.`);
    if (entry.shelf === "status") {
      if (entry.status === null || !(entry.status in STATUS_LABELS)) {
        say("it is on the statuses shelf and names no status.");
      } else if (entry.slug !== statusSlug(entry.status)) {
        say(`a status entry is named for its label: ${statusSlug(entry.status)}.`);
      }
    } else if (entry.status !== null) {
      say("only an entry on the statuses shelf names a status.");
    }
    if (!entry.title) say("it has no title.");
    if (!entry.answer) say("it has no answer.");
    if (!(entry.rule in METHOD_SECTIONS)) {
      say(`its rule "${entry.rule}" is not a section of the method page.`);
    }
    if (!entry.onSite) say("it does not say the rule that uses the word.");
    if (entry.applies !== null && !(entry.applies in APPLIES)) {
      say(`"${entry.applies}" names no set of claims.`);
    }
    if (entry.shelf === "research" && entry.sources.length === 0) {
      say("an entry on how research is recorded lists at least one source.");
    }
    if (entry.sources.length > MOST_SOURCES) say(`it lists more than ${MOST_SOURCES} sources.`);
    for (const source of entry.sources) {
      if (!source.name || !/^https:\/\/\S+$/.test(source.url)) {
        say(`the source "${source.name || source.url}" needs a name and an https address.`);
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(source.checked)) {
        say(`the source "${source.name}" has no day it was checked.`);
      }
    }
    if (entry.related.length > MOST_RELATED) say(`it lists more than ${MOST_RELATED} related entries.`);
    for (const related of entry.related) {
      if (related === entry.slug) say("it lists itself as related.");
      else if (!slugs.has(related)) say(`its related entry "${related}" does not exist.`);
    }
    let from = 0;
    for (const part of ENTRY_PARTS) {
      const at = entry.text.indexOf(`## ${part}`, from);
      if (at < 0) say(`its text has no "${part}" part, or has it out of order.`);
      else from = at;
    }
    const words = wordCount([entry.answer, entry.onSite, entry.text].join(" "));
    if (words < WORDS.fewest || words > WORDS.most) {
      say(`it runs to ${words} words; an entry runs from ${WORDS.fewest} to ${WORDS.most}.`);
    }
    for (const check of [assertNeutral, assertNoAdvice]) {
      try {
        check([entry.title, entry.answer, entry.onSite, entry.text]);
      } catch (error) {
        say((error as Error).message);
      }
    }
  }
  return problems;
}

/** Stops a build whose entry files fail a check, naming every failure. */
export function assertGuide(entries: readonly GuideEntry[]): void {
  const problems = guideProblems(entries);
  if (problems.length > 0) {
    throw new Error(`The guide cannot be built:\n  ${problems.join("\n  ")}`);
  }
}

/** A shelf's entries in reading order: statuses along the path, then those off it. */
export function shelfEntries(entries: readonly GuideEntry[], shelf: Shelf): GuideEntry[] {
  const held = entries.filter((entry) => entry.shelf === shelf);
  if (shelf !== "status") return held.sort((a, b) => a.order - b.order || (a.slug < b.slug ? -1 : 1));
  const codes = Object.keys(STATUS_LABELS) as StatusCode[];
  const place = (entry: GuideEntry) => {
    const onPath = STAGE_PATH.indexOf(entry.status!);
    return onPath >= 0 ? onPath : STAGE_PATH.length + codes.indexOf(entry.status!);
  };
  return held.sort((a, b) => place(a) - place(b));
}

/** Every entry in the order the index lists them. */
export function orderedEntries(entries: readonly GuideEntry[]): GuideEntry[] {
  return SHELVES.flatMap((shelf) => shelfEntries(entries, shelf.id));
}

interface Applies {
  test: (claim: ExportedClaim) => boolean;
  /** How the claims are named in "3 of 12 …" and "No tracked claim … now". */
  many: string;
  none: string;
  /** Where the rest are listed. */
  more: { href: string; label: string };
}

const TOPICS = { href: "/topics", label: "Every tracked claim, by topic" };
const atStatus = (code: StatusCode): Applies => ({
  test: (claim) => claim.status.code === code,
  many: "have this status",
  none: "No tracked claim has this status now.",
  more: { href: `/?status=${code}`, label: "The claims at this status" },
});
const hasTrial = (claim: ExportedClaim) =>
  (claim.trials ?? []).length > 0 || claim.events.some((event) => event.trial_id !== null);

/**
 * The sets of published claims a word can apply to. An entry names one; the page lists
 * up to three of its claims and counts the rest.
 */
export const APPLIES: Record<string, Applies> = {
  ...(Object.fromEntries(
    (Object.keys(STATUS_LABELS) as StatusCode[]).map((code) => [code, atStatus(code)]),
  ) as Record<StatusCode, Applies>),
  approved: {
    ...atStatus("approved"),
    more: { href: "/it-happened", label: "Every approval on record" },
  },
  claims: {
    test: () => true,
    many: "are tracked",
    none: "No claim is tracked yet.",
    more: TOPICS,
  },
  promises: {
    test: (claim) => latestPromise(claim) !== null,
    many: "have a dated promise",
    none: "No tracked claim has a dated promise now.",
    more: { href: "/?view=promised", label: "Promises, by date" },
  },
  records: {
    test: (claim) => claim.events.length > 0,
    many: "have at least one record",
    none: "No tracked claim has a record now.",
    more: TOPICS,
  },
  matches: {
    test: (claim) => (claim.matches ?? []).length > 0,
    many: "list a match with its confidence",
    none: "No tracked claim lists a match now.",
    more: TOPICS,
  },
  "no-signal": {
    test: (claim) => claim.status.overlay_years !== null,
    many: "carry the no-signal note",
    none: "No tracked claim carries the no-signal note now.",
    more: { href: "/?view=quiet", label: "The claims with no signal, longest first" },
  },
  "follow-up-papers": {
    test: (claim) => claim.events.some((event) => event.type === "followup_paper"),
    many: "list a follow-up paper",
    none: "No tracked claim lists a follow-up paper now.",
    more: TOPICS,
  },
  checked: {
    test: (claim) => claim.checked_by_person,
    many: "have been checked by a person",
    none: "No tracked claim has been checked by a person yet. Each page says so.",
    more: TOPICS,
  },
  trials: {
    test: hasTrial,
    many: "list a trial registry record",
    none: "No tracked claim lists a trial registry record now.",
    more: TOPICS,
  },
  phases: {
    test: (claim) => ["phase_1", "phase_2", "phase_3"].includes(claim.status.code),
    many: "have a status that names a phase",
    none: "No tracked claim has a status that names a phase now.",
    more: TOPICS,
  },
  "primary-outcomes": {
    test: (claim) =>
      (claim.trials ?? []).some((trial) => (trial.facts?.primary_outcomes.length ?? 0) > 0),
    many: "list a trial with its planned primary outcomes",
    none: "No tracked claim lists a trial's planned primary outcomes now.",
    more: TOPICS,
  },
  "ended-early": {
    test: (claim) =>
      (claim.trials ?? []).some((trial) => ["terminated", "withdrawn"].includes(trial.state)) ||
      claim.events.some((event) => ["terminated", "withdrawn"].includes(event.trial_state ?? "")),
    many: "list a trial that was terminated or withdrawn",
    none: "No tracked claim lists a trial that was terminated or withdrawn now.",
    more: TOPICS,
  },
  retractions: {
    test: (claim) => claim.events.some((event) => event.type === "retraction"),
    many: "list a retraction notice",
    none: "No tracked claim lists a retraction notice now.",
    more: TOPICS,
  },
  "registered-not-approved": {
    test: (claim) => hasTrial(claim) && claim.status.code !== "approved",
    many: "list a registered trial and no approval",
    none: "No tracked claim lists a registered trial without an approval now.",
    more: TOPICS,
  },
};

/** The most claims an entry lists. */
export const CLAIMS_SHOWN = 3;

/** The claims an entry's word applies to now: up to three, newest report first, and how many in all. */
export function claimsAtWork(entry: GuideEntry, claims: readonly ExportedClaim[]) {
  const set = entry.applies ? APPLIES[entry.applies] : null;
  if (!set) return null;
  const held = claims
    .filter(set.test)
    .sort((a, b) => ((a.first_reported_date ?? "") < (b.first_reported_date ?? "") ? 1 : -1));
  return { shown: held.slice(0, CLAIMS_SHOWN), total: held.length, ...set };
}

/** The entries before and after one on its shelf, for the foot of its page. */
export function neighbours(entries: readonly GuideEntry[], entry: GuideEntry) {
  const shelf = shelfEntries(entries, entry.shelf);
  const at = shelf.findIndex((other) => other.slug === entry.slug);
  return { previous: shelf[at - 1] ?? null, next: shelf[at + 1] ?? null };
}
