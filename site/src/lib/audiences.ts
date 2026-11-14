// The pages made for one kind of reader each (openspec landing-pages-and-guide): who
// they are for, and the words the researchers' page gives each field of the data file.
// Pure: no file, network or clock.

/** The audience pages, in the order the footer names them. */
export const AUDIENCES = ["journalists", "clinicians", "researchers"] as const;

export type Audience = (typeof AUDIENCES)[number];

/** What each field of a claim in the data file holds. A site test holds the list to the file. */
export const CLAIM_FIELDS: Record<string, string> = {
  slug: "The claim's address on this site.",
  headline: "A short description of the claim, written by this site.",
  summary: "One or two sentences on what was reported.",
  vertical: "The topic the claim is filed under.",
  approach: "The kind of treatment, such as drug or gene therapy, where one is recorded.",
  intervention: "The treatment's name and its other names.",
  indication: "The condition the treatment was reported to treat.",
  first_reported_date: "The date of the earliest news report read.",
  evidence_stage: "The kind of study the first reports described.",
  status:
    "The status code, the years behind a no-signal note, and the records that produced the status.",
  articles: "Each news report: outlet, title, date and address. Never its text.",
  promises: "Each timeline stated in a report, with the date it names and its report.",
  events: "Each dated record, with its kind, source and link.",
  trials: "Each trial once, with what its registry record states and when that was read.",
  matches: "Each registry record matched to the claim, with its score and whether it counts.",
  background:
    "Each background card: a vocabulary term for the condition or the treatment, its definition in its source's words, its source and edition, its score and when its record was read.",
  checked_by_person: "Whether a person has reviewed the page.",
};

export interface PickerClaim {
  slug: string;
  name: string;
  headline: string;
  /** Everything a search can match: names, condition and headline, in lower case. */
  words: string;
}

/** The claims whose words hold every word typed, in the order given. Empty for a blank search. */
export function pickClaims<T extends { words: string }>(
  claims: readonly T[],
  typed: string,
  atMost = 8,
): T[] {
  const asked = typed.toLowerCase().split(/\s+/).filter(Boolean);
  if (asked.length === 0) return [];
  return claims
    .filter((claim) => asked.every((word) => claim.words.includes(word)))
    .slice(0, atMost);
}
