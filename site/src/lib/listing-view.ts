// What a page that lists pairs shows, from the lab's page file for it (openspec pairs-site,
// design decision 2 as chosen on 2026-11-20): an intervention's page from its
// `PairInterventionPage`, a clinical category's from its `PairClinicalCategoryPage`, a topic's
// from its `PairTopicPage`. Pure, so the build and the Worker read a listing the same way, and
// the Worker reads one file by key: never the row tables, whose topic join read about 6,000 rows
// a view on the rehearsal against 6 to 170 for a page file.
import { shownName } from "./pair-view.ts";
import { STATUS_LABELS } from "./status.ts";
import { conditionCard, treatmentCard, type CardView } from "./card-view.ts";

export interface ListingRow {
  address: string;
  intervention: string;
  condition: string;
  statusCode: string;
  status: string;
  asOf: string;
  trials: number;
  checkedByPerson: boolean;
}

export interface ListingLink {
  href: string;
  label: string;
  /** For a narrower category: the published pairs beneath it on this page. */
  count?: number;
}

export interface ListingView {
  kind: "intervention" | "category" | "topic";
  path: string;
  title: string;
  description: string;
  crumbs: ListingLink[];
  /** Lines under the title, each plain text. */
  notes: string[];
  /** Linked lines under the notes: broader and narrower categories. */
  linkGroups: { label: string; links: ListingLink[] }[];
  /** What the listed treatment or category is: its knowledge card, or none. */
  card: CardView | null;
  rows: ListingRow[];
}

function rowOf(row: any): ListingRow {
  return {
    address: row.pair.address,
    intervention: shownName(row.intervention.preferred_name),
    condition: row.descriptor.label,
    statusCode: row.status.code,
    status: STATUS_LABELS[row.status.code as keyof typeof STATUS_LABELS],
    asOf: row.status.as_of,
    trials: row.pair.nct_ids.length,
    checkedByPerson: row.pair.checked_by_person,
  };
}

const byName = (a: ListingRow, b: ListingRow) => a.intervention.localeCompare(b.intervention) || a.condition.localeCompare(b.condition);
/** The file's rows, once each, for the pairs this bundle version publishes: a lab file can name
 * pairs a slice left out, and a listing links only pages that answer. */
const rowsOf = (pairs: any[], published: Set<string>) => {
  const seen = new Set<string>();
  return pairs
    .map(rowOf)
    .filter((row) => published.has(row.address) && !seen.has(row.address) && seen.add(row.address))
    .sort(byName);
};

/** The addresses a listing file names, for asking which of them the version publishes. */
export const namedPairs = (file: any): string[] => [...new Set<string>(file.pairs.map((row: any) => row.pair.address))];

/** An intervention's page: its names, its kind and every pair the lab lists for it. */
export function interventionListing(file: any, published: Set<string>): ListingView {
  const preferred = file.intervention.preferred_name;
  const name = shownName(preferred);
  return {
    kind: "intervention",
    path: `/intervention/${file.intervention.slug}`,
    title: name,
    description: `Where the public trial records show ${name} stands, for each condition it is tested for.`,
    crumbs: [],
    notes: [],
    linkGroups: [],
    card: treatmentCard(file),
    rows: rowsOf(file.pairs, published),
  };
}

const categoryPath = (id: string) => `/clinical/${id}`;
const byLabel = (a: any, b: any) => a.label.localeCompare(b.label);
const beneath = (treeNumbers: string[], tops: string[]) =>
  treeNumbers.some((number) => tops.some((top) => number === top || number.startsWith(`${top}.`)));

/** A clinical category's page: where it sits in MeSH and every pair the lab files at or
 * beneath it. It links only categories with a page in the bundle version (`categories`), a
 * narrower one only with a published pair beneath it, and says how many. */
export function categoryListing(file: any, published: Set<string>, categories: Set<string>): ListingView {
  const { descriptor } = file;
  const link = (one: any) => ({ href: categoryPath(one.descriptor_id), label: one.label });
  const shown = file.pairs.filter((row: any) => published.has(row.pair.address));
  const broader = file.broader.filter((one: any) => categories.has(one.descriptor_id)).sort(byLabel).map(link);
  const narrower = file.narrower
    .filter((one: any) => categories.has(one.descriptor_id))
    .map((one: any) => ({
      ...link(one),
      count: new Set(shown.filter((row: any) => beneath(row.descriptor.tree_numbers, one.tree_numbers)).map((row: any) => row.pair.address)).size,
    }))
    .filter((one: ListingLink) => (one.count ?? 0) > 0)
    .sort(byLabel);
  return {
    kind: "category",
    path: categoryPath(descriptor.descriptor_id),
    title: descriptor.label,
    description: `Treatments tested for conditions in the MeSH category ${descriptor.label}, and where each stands.`,
    crumbs: [{ href: "/clinical", label: "Clinical categories" }],
    // Names only: the descriptor's id and tree numbers are codes, and stay in the address.
    notes: ["Lists the pairs whose condition is this category or one beneath it. A category is not a diagnosis and not advice."],
    card: conditionCard(descriptor, file.broader, (id) => (categories.has(id) ? categoryPath(id) : undefined)),
    linkGroups: [...(broader.length ? [{ label: "Broader", links: broader }] : []), ...(narrower.length ? [{ label: "Narrower", links: narrower }] : [])],
    rows: rowsOf(file.pairs, published),
  };
}

/** A topic's page: the pairs the lab filed under it. */
export function topicListing(file: any, published: Set<string>): ListingView {
  const { vertical } = file;
  return {
    kind: "topic",
    path: `/topic/${vertical.slug}`,
    title: vertical.title,
    description: `Treatments followed in ${vertical.title.toLowerCase()}, and where the public trial records show each stands.`,
    crumbs: [{ href: "/topics", label: "Topics" }],
    notes: [],
    linkGroups: [],
    card: null,
    rows: rowsOf(file.pairs, published),
  };
}
