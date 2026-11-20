// The order a search's matches are shown in, and the example words the box offers
// (openspec search-answer-in-step). Pure: claims and the search detail go in, an order
// or a pair of words comes out. A fixed rule over the words a match holds, never a
// score shown to the reader.

/** A claim as far as the order needs it. */
export interface OrderedClaim {
  headline: string;
  page: string;
  names: string[];
  indication: string;
}

/** The titles of each claim's reports, keyed by the claim's slug. */
export interface OrderDetail {
  pairs: Record<string, { reports: { title: string }[] } | undefined>;
}

/** The words of a search, for marking where they stand in a match. Short words are
 * left unmarked, as they would mark half of every line. A common ending is cut, so
 * "regrowing" also finds "regrows" and "cells" finds "cell". */
export function searchWords(query: string): string[] {
  return query
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .map((word) => (word.length >= 5 ? word.replace(/(?:ing|ed|es|s)$/u, "") : word))
    .filter((word) => word.length >= 3);
}

/** Every word that starts with one of the searched words. */
export function wordPattern(words: string[]): RegExp {
  const escaped = words.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return new RegExp(`(?<![\\p{L}\\p{N}])(?:${escaped.join("|")})[\\p{L}\\p{N}]*`, "giu");
}

/** How many of the searched words a text holds. */
export function wordsIn(text: string, words: string[]): number {
  if (!text || words.length === 0) return 0;
  const lower = text.toLowerCase();
  return words.filter((word) => wordPattern([word]).test(lower)).length;
}

// The words of a text, for finding the searched words side by side.
const tokens = (text: string) => text.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean);

/** Whether a text holds every searched word. */
export const holdsAll = (text: string, words: string[]) => words.length > 0 && wordsIn(text, words) === words.length;

/** Whether a text holds the searched words side by side, in their order. */
export function holdsPhrase(text: string, words: string[]): boolean {
  if (words.length < 2) return false;
  const said = tokens(text);
  return said.some((_, at) => words.every((word, step) => said[at + step]?.startsWith(word)));
}

/** What a claim weighs for the searched words: the words side by side, then all of
 * them, in the claim's own headline first, then in a report's headline, then in the
 * treatment and what it is claimed for. */
export function matchWeight(claim: OrderedClaim, words: string[], detail: OrderDetail): number {
  const titles = detail.pairs[claim.page.slice(1)]?.reports.map((report) => report.title) ?? [];
  let weight = 0;
  if (holdsPhrase(claim.headline, words)) weight += 6;
  if (holdsAll(claim.headline, words)) weight += 4;
  if (titles.some((title) => holdsPhrase(title, words))) weight += 3;
  if (titles.some((title) => holdsAll(title, words))) weight += 2;
  if (holdsAll([...claim.names, claim.indication].join(" "), words)) weight += 2;
  return weight;
}

/** The matches in the order they are shown: the heaviest first. The search index's
 * order breaks a tie. */
export function ranked<Claim extends OrderedClaim>(matches: Claim[], words: string[], detail: OrderDetail): Claim[] {
  return matches
    .map((claim, at) => ({ claim, at, weight: matchWeight(claim, words, detail) }))
    .sort((a, b) => b.weight - a.weight || a.at - b.at)
    .map((entry) => entry.claim);
}

/** How long the example words may be, so the field shows them whole on a phone. */
export const EXAMPLE_LENGTH = 22;

/** A published claim as far as the example needs it. */
export interface ExampleClaim {
  slug: string;
  headline: string;
  intervention: { name: string; synonyms: string[] };
  indication: string;
  articles: { title: string }[];
}

/**
 * The words the field offers as an example, and the claim they lead to. Chosen by
 * rule, never by hand. The claims come in the order the site prefers its examples
 * (`exampleClaims`); the first is taken whose treatment's name
 *
 * - is one to three plain words, each long enough to be searched for, and short
 *   enough for the field;
 * - stands in the claim's own headline, as written, so the answer shows why it leads;
 * - is held whole by no other claim, in its headline, its treatment's names, its
 *   condition or a report's title, so no other claim can weigh as much.
 *
 * Null when no claim passes: the field then offers no example words.
 */
export function searchExample(claims: readonly ExampleClaim[]): { words: string; slug: string } | null {
  const said = (claim: ExampleClaim) =>
    [claim.headline, claim.intervention.name, ...claim.intervention.synonyms, claim.indication, ...claim.articles.map((article) => article.title)];
  for (const claim of claims) {
    const name = claim.intervention.name.trim();
    const parts = name.split(/\s+/);
    if (name.length > EXAMPLE_LENGTH || parts.length > 3) continue;
    if (!parts.every((part) => /^[\p{L}\p{N}]{3,}$/u.test(part))) continue;
    const words = searchWords(name);
    if (words.length !== parts.length) continue;
    const inHeadline = parts.length > 1 ? holdsPhrase(claim.headline, words) : holdsAll(claim.headline, words);
    if (!inHeadline) continue;
    const shared = claims.some((other) => other !== claim && said(other).some((text) => holdsAll(text, words)));
    if (shared) continue;
    // A name written with one capital, at its start, is offered as a reader would type it.
    return { words: /^\p{Lu}[^\p{Lu}]*$/u.test(name) ? name.toLowerCase() : name, slug: claim.slug };
  }
  return null;
}
