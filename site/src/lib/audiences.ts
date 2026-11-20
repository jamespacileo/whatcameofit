// The pages made for one kind of reader each (openspec landing-pages-and-guide): who
// they are for, and the journalists' page's search.
// Pure: no file, network or clock.

/** The audience pages, in the order the footer names them. */
export const AUDIENCES = ["journalists", "clinicians", "researchers"] as const;

export type Audience = (typeof AUDIENCES)[number];

export interface PickerPair {
  /** The pair's address. */
  slug: string;
  name: string;
  headline: string;
  /** Everything a search can match: names and condition, in lower case. */
  words: string;
}

/** The pairs whose words hold every word typed, in the order given. Empty for a blank search. */
export function pickPairs<T extends { words: string }>(
  pairs: readonly T[],
  typed: string,
  atMost = 8,
): T[] {
  const asked = typed.toLowerCase().split(/\s+/).filter(Boolean);
  if (asked.length === 0) return [];
  return pairs
    .filter((pair) => asked.every((word) => pair.words.includes(word)))
    .slice(0, atMost);
}
