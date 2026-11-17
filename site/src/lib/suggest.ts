// What the box offers while a reader types (openspec search-suggestions): rows of five
// kinds, each kind under its name and in a fixed order, so the panel is the same shape
// for every word. Pure: the lookup index and the search detail go in, groups of rows
// come out. Nothing here ranks by a model or a score; the order is by rules a reader
// could check.

export interface SuggestClaim {
  page: string;
  names: string[];
  indication: string;
  topic: string;
  status: string;
}

export interface SuggestIndex {
  claims: Record<string, SuggestClaim>;
  topics: Record<string, { title: string; count: number }>;
}

export interface SuggestDetail {
  claims: Record<
    string,
    {
      reports: { title: string; outlet: string; date: string | null }[];
      trials: { id: string; title: string | null; phases: string[] }[];
    }
  >;
}

export type SuggestKind = "topic" | "treatment" | "condition" | "report" | "trial";

export interface Suggestion {
  kind: SuggestKind;
  /** What the row says first: a name, a title, an identifier. */
  text: string;
  /** A treatment's other name, where that is the one the typed words are in. */
  also?: string;
  /** Said after it in grey: what a treatment is for, a trial's title. */
  sub?: string;
  /** At the row's right: how much is behind it, or where its claim stands. */
  meta: string;
  /** A page to open. */
  href?: string;
  /** Or words to search for, as if typed and sent. */
  query?: string;
}

export interface SuggestGroup {
  kind: SuggestKind;
  label: string;
  rows: Suggestion[];
}

/** The kinds in the order they are drawn, each with its name. */
export const SUGGEST_KINDS: [SuggestKind, string][] = [
  ["topic", "Topics"],
  ["treatment", "Treatments"],
  ["condition", "Conditions"],
  ["report", "Reports"],
  ["trial", "Trials on record"],
];

/** How many rows a kind may show. */
export const SUGGEST_ROWS = 2;

/** The typed words, lower case. One letter alone suggests nothing. */
export function suggestWords(text: string): string[] {
  const words = text
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean);
  return words.join("").length >= 2 ? words : [];
}

const escaped = (word: string) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** A test for text in which every typed word starts a word. */
function matcher(words: string[]) {
  const tests = words.map((word) => new RegExp(`(?<![\\p{L}\\p{N}])${escaped(word)}`, "iu"));
  return (text: string | null | undefined) => !!text && tests.every((test) => test.test(text));
}

/** Text that begins with the first typed word comes before text that holds it later. */
const leads = (text: string, words: string[]) => (text.toLowerCase().startsWith(words[0]) ? 0 : 1);

const claimsText = (count: number) => `${count} ${count === 1 ? "claim" : "claims"}`;

/** Newest first; an undated report last. Dates are as the site writes them. */
const byDate = (a: string | null, b: string | null) => (Date.parse(b ?? "") || 0) - (Date.parse(a ?? "") || 0);

/** The groups to draw for what is typed. A kind with no row is left out. Reports and
 * trials need the search detail: until it is loaded they are left out too. */
export function suggest(text: string, index: SuggestIndex, detail: SuggestDetail | null): SuggestGroup[] {
  const words = suggestWords(text);
  if (words.length === 0) return [];
  const has = matcher(words);
  const rows: Record<SuggestKind, Suggestion[]> = { topic: [], treatment: [], condition: [], report: [], trial: [] };

  rows.topic = Object.entries(index.topics)
    .filter(([, topic]) => has(topic.title))
    .sort(([, a], [, b]) => leads(a.title, words) - leads(b.title, words) || b.count - a.count || a.title.localeCompare(b.title))
    .map(([slug, topic]) => ({ kind: "topic", text: topic.title, meta: claimsText(topic.count), href: `/topic/${slug}` }));

  const claims = Object.values(index.claims);

  // One row for a claim: its treatment by its first name. Where the words are only in
  // another of its names, that name follows, so the row says why it is offered.
  rows.treatment = claims
    .filter((claim) => claim.names.some((name) => has(name)))
    .sort(
      (a, b) =>
        leads(a.names[0], words) - leads(b.names[0], words) ||
        a.names[0].length - b.names[0].length ||
        a.names[0].localeCompare(b.names[0]) ||
        a.page.localeCompare(b.page),
    )
    .map((claim) => ({
      kind: "treatment",
      text: claim.names[0],
      ...(has(claim.names[0]) ? {} : { also: claim.names.find((name) => has(name)) }),
      sub: claim.indication,
      meta: claim.status,
      href: claim.page,
    }));

  // One row for a condition as it is written, with how many claims are for it.
  const conditions = new Map<string, number>();
  for (const claim of claims) {
    if (has(claim.indication)) conditions.set(claim.indication, (conditions.get(claim.indication) ?? 0) + 1);
  }
  rows.condition = [...conditions]
    // The condition most claims are for comes first; of two with as many, the one that begins with the word.
    .sort(([a, countA], [b, countB]) => countB - countA || leads(a, words) - leads(b, words) || a.localeCompare(b))
    .map(([name, count]) => ({ kind: "condition", text: name, meta: claimsText(count), query: name }));

  if (detail) {
    const reports: (Suggestion & { date: string | null })[] = [];
    const trials = new Map<string, Suggestion & { byId: number }>();
    for (const claim of claims) {
      const held = detail.claims[claim.page.slice(1)];
      if (!held) continue;
      for (const report of held.reports) {
        if (!has(report.title)) continue;
        reports.push({
          kind: "report",
          text: report.title,
          meta: [report.outlet, report.date].filter(Boolean).join(" · "),
          href: claim.page,
          date: report.date,
        });
      }
      for (const trial of held.trials) {
        const byId = words.length === 1 && trial.id.toLowerCase().startsWith(words[0]) ? 0 : 1;
        if (trials.has(trial.id) || (byId === 1 && !has(trial.title))) continue;
        trials.set(trial.id, {
          kind: "trial",
          text: trial.id,
          sub: trial.title ?? undefined,
          meta: trial.phases.join(", "),
          query: trial.id,
          byId,
        });
      }
    }
    const seen = new Set<string>();
    rows.report = reports
      .sort((a, b) => byDate(a.date, b.date) || a.text.localeCompare(b.text))
      .filter((report) => !seen.has(report.text) && seen.add(report.text))
      .map(({ date: _date, ...report }) => report);
    rows.trial = [...trials.values()]
      // A trial found by its identifier first; then the newest identifier, which a registry gives last.
      .sort((a, b) => a.byId - b.byId || b.text.localeCompare(a.text))
      .map(({ byId: _byId, ...trial }) => trial);
  }

  return SUGGEST_KINDS.map(([kind, label]) => ({ kind, label, rows: rows[kind].slice(0, SUGGEST_ROWS) })).filter(
    (group) => group.rows.length > 0,
  );
}

/** A text cut where the typed words stand in it, for drawing them marked. Each part
 * says whether it is one of them. */
export function suggestParts(text: string, typed: string): { text: string; hit: boolean }[] {
  const words = suggestWords(typed);
  if (words.length === 0) return [{ text, hit: false }];
  const pattern = new RegExp(`(?<![\\p{L}\\p{N}])(?:${words.map(escaped).join("|")})`, "giu");
  const parts: { text: string; hit: boolean }[] = [];
  let at = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index! > at) parts.push({ text: text.slice(at, match.index), hit: false });
    parts.push({ text: match[0], hit: true });
    at = match.index! + match[0].length;
  }
  if (at < text.length) parts.push({ text: text.slice(at), hit: false });
  return parts;
}
