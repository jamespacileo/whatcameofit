// The site's wording for the organisations a claim names. Openspec organisations and
// site-publishing: the export carries codes and five fields of a registry record; the
// site words the codes, states who is behind a claim and in what role, and never
// judges an organisation or says what its part implies.
import { assertNeutral } from "./status.ts";

export interface ExportedOrganisationRole {
  /** "named_in_report" or "sponsor". */
  role: string;
  /** For "named_in_report": the claim's articles that named it. Empty when which
   * report named it was not recorded. */
  article_urls: string[];
  /** For "sponsor": the trials whose registry record names it as lead sponsor. */
  trial_ids: string[];
}

export interface ExportedOrganisationRecord {
  /** The registry's name, such as "ror". */
  source: string;
  external_id: string;
  /** The record's own page. */
  url: string;
  /** The registry's display name. */
  name: string;
  /** The registry's types, as lower-case codes. */
  kinds: string[];
  country: string | null;
  /** Only an https address. */
  website: string | null;
  /** The registry's own measure of how well the name matched, 0 to 1. */
  score: number;
  read_at: string;
}

export interface ExportedOrganisation {
  /** The registry's name when identified, else the name a source gave. */
  name: string;
  identified: boolean;
  record: ExportedOrganisationRecord | null;
  roles: ExportedOrganisationRole[];
}

/** The registries an organisation can be identified in, by the export's source name. */
export const REGISTRY_NAMES: Record<string, string> = {
  ror: "the Research Organization Registry (ROR)",
};

/** The registry's types of organisation, in the site's words. */
export const KIND_WORDS: Record<string, string> = {
  education: "Education",
  healthcare: "Healthcare",
  company: "Company",
  funder: "Funder",
  government: "Government",
  facility: "Facility",
  nonprofit: "Non-profit",
  archive: "Archive",
  other: "Other",
};

/** The roles an organisation plays for a claim, in the order the page lists them. */
export const ROLE_ORDER = ["named_in_report", "sponsor"];

const ROLE_WORDS: Record<string, (role: ExportedOrganisationRole) => string> = {
  // A report is named only when the pipeline recorded which one named the organisation.
  named_in_report: ({ article_urls }) =>
    article_urls.length === 0
      ? "Named in one of this claim’s reports"
      : article_urls.length === 1
        ? "Named in the report"
        : `Named in ${article_urls.length} reports`,
  sponsor: ({ trial_ids }) =>
    trial_ids.length === 1 ? "Sponsor of 1 trial" : `Sponsor of ${trial_ids.length} trials`,
};

/** What the section says of itself, once, above the list. */
export const ORGANISATIONS_NOTE =
  "The universities, hospitals and companies this claim’s reports and trial records name, and the part each source gives them. A sponsor is the organisation a trial’s registry record names as its lead sponsor. An open registry identifies an organisation from its name; it does not verify the organisation’s part in this claim.";

export const NOT_IDENTIFIED =
  "Not matched to a registry record. Shown by the name its source gave.";

/** What a role says, such as "Named in the report" or "Sponsor of 3 trials". */
export function roleText(role: ExportedOrganisationRole): string {
  return ROLE_WORDS[role.role](role);
}

/** The registry's kinds of the organisation, in the site's words. */
export function kindsText(kinds: string[]): string {
  return kinds.map((kind) => KIND_WORDS[kind]).join(", ");
}

/** The host a reader sees for a website, without "www.". */
export function websiteHost(website: string): string {
  return new URL(website).hostname.replace(/^www\./, "");
}

/** Where the identification comes from, with the registry's own name-match score. */
export function identifiedText(record: Pick<ExportedOrganisationRecord, "source" | "score">): string {
  return `Identified in ${REGISTRY_NAMES[record.source]}, which scores the name match ${Math.round(record.score * 100)}%.`;
}

/** Beside a report on the website of an organisation the claim names. It says where
 * the report is, and nothing of what that means. */
export function publisherText(name: string): string {
  return `This report is on ${name}’s website.`;
}

/** Each organisation once, ordered by its first role and then by name. */
export function orderOrganisations(organisations: ExportedOrganisation[]): ExportedOrganisation[] {
  const rank = (organisation: ExportedOrganisation) =>
    Math.min(...organisation.roles.map((role) => ROLE_ORDER.indexOf(role.role)));
  return [...organisations].sort(
    (a, b) =>
      rank(a) - rank(b) || a.name.localeCompare(b.name, "en", { sensitivity: "base" }),
  );
}

/** The organisation a report is marked as published by, if it is one of the claim's. */
export function publisherOf(
  organisations: ExportedOrganisation[],
  publishedBy: string | null | undefined,
): ExportedOrganisation | null {
  if (!publishedBy) return null;
  return organisations.find((organisation) => organisation.record?.url === publishedBy) ?? null;
}

/** Organisation codes in the export that the site has no words for, as "kind: code". */
export function unwordedOrganisationCodes(organisations: ExportedOrganisation[]): string[] {
  const missing = new Set<string>();
  for (const organisation of organisations) {
    for (const role of organisation.roles) {
      if (!(role.role in ROLE_WORDS)) missing.add(`organisation role: ${role.role}`);
    }
    for (const kind of organisation.record?.kinds ?? []) {
      if (!(kind in KIND_WORDS)) missing.add(`organisation kind: ${kind}`);
    }
    const source = organisation.record?.source;
    if (source && !(source in REGISTRY_NAMES)) missing.add(`organisation registry: ${source}`);
  }
  return [...missing].sort();
}

// The site states who is behind a claim and never vouches for or against them: no
// endorsement, backing or funding, no standing, and no verdict on a report.
const STANDING_WORDS =
  /\b(endors\w*|back(s|ed|ing)?|vouch\w*|stands? behind|fund(s|ed|ing)?|promot\w*|bias\w*|unreliable|reliab\w*|trust\w*|reputa\w*|prestig\w*|renowned|leading|world-class|credib\w*|independent)\b/i;

export function assertNoStandingWords(texts: string[]): void {
  for (const text of texts) {
    const found = text.match(STANDING_WORDS);
    if (found) {
      throw new Error(
        `Wording "${found[0]}" in organisation wording: "${text}". The site states an organisation's role and where a report is, never what they imply.`,
      );
    }
  }
}

const SITE_WORDS = [
  ...Object.values(KIND_WORDS),
  ...Object.values(REGISTRY_NAMES),
  ...Object.values(ROLE_WORDS).flatMap((word) =>
    [[], ["a"], ["a", "b", "c"]].map((ids) => word({ role: "", article_urls: ids, trial_ids: ids })),
  ),
  identifiedText({ source: "ror", score: 0.97 }),
  ORGANISATIONS_NOTE,
  NOT_IDENTIFIED,
  publisherText("An Organisation"),
];
assertNeutral(SITE_WORDS);
assertNoStandingWords(SITE_WORDS);
