// The pair pages (openspec pairs-site): what a page shows, from the lab's `PairPage` files.
// The bundle folder named in PAIRS_BUNDLE is the build's only input (the operator's decision
// of 2026-11-20 removed the claims export), so a build without one stops.
import path from "node:path";
import { PAIR_APPROACH_LABELS } from "./pair-wording.ts";
import { readBundle, type Bundle } from "./bundle.ts";
import { builtAhead, pairView, shownName } from "./pair-view.ts";
import { categoryListing, interventionListing, topicListing, type ListingView } from "./listing-view.ts";
import { articleKey } from "./article-key.mjs";
import { UNCHECKED_NOTE } from "./notices.ts";
import { PAIR_RECORD_FORMAT, pairDataHeader, pairRecordOf } from "./pair-record.ts";
import { STAGE_PATH, STATUS_LABELS, STATUS_MEANINGS, overlayText } from "./status.ts";
import { formatDate } from "./timetable.ts";

/** The bundle folder this build reads. */
export function pairBundleFolder(): string {
  const folder = process.env.PAIRS_BUNDLE;
  if (!folder) {
    throw new Error(
      "No bundle to build from: set PAIRS_BUNDLE to a folder of the lab's page files (tests/bundle is the small one the tests build).",
    );
  }
  return path.resolve(folder);
}

let cached: Bundle | undefined;

/** The bundle this build reads, read once. */
export function pairBundle(): Bundle {
  return (cached ??= readBundle(pairBundleFolder()));
}

/** When the bundle was made, as its manifest states: the date the site's pages speak for. */
export function bundleMadeAt(): string {
  return pairBundle().manifest.made_at;
}

export { builtAhead, pairView, shownName, type PairEventView, type PairTrialView, type PairView } from "./pair-view.ts";

/** The version of the bundle this build reads: the checksum `load-pairs.mjs` loads it into
 * D1 under, as its manifest states and `readBundle` checked. */
export function pairBundleVersion(): string {
  return pairBundle().version;
}

/** Every pair the bundle holds, by address. */
export function pairPages(): Record<string, any> {
  return pairBundle().pages.PairPage ?? {};
}

/** The pairs whose page, card and embed this build makes (decision 2); the Worker makes
 * every other pair's page on request. */
export function builtAheadPages(): Record<string, any> {
  return Object.fromEntries(Object.entries(pairPages()).filter(([, page]) => builtAhead(page)));
}

// Listing pages (openspec pairs-site, task 3.2). Every list is worked out here from the pair
// pages themselves, not taken from a listing file's own `pairs`: the lab will give a pair
// the most specific MeSH term its trials are filed under, so a category or condition lists
// the pairs whose condition sits at or beneath it in the MeSH tree.

export interface PairRow {
  address: string;
  intervention: string;
  condition: string;
  statusCode: string;
  status: string;
  trials: number;
  asOf: string;
  checkedByPerson: boolean;
}

export function pairRow(page: any): PairRow {
  const { row } = page;
  return {
    address: row.pair.address,
    intervention: shownName(row.intervention.preferred_name),
    condition: row.descriptor.label,
    statusCode: row.status.code,
    status: STATUS_LABELS[row.status.code as keyof typeof STATUS_LABELS],
    trials: page.trials.length,
    asOf: row.status.as_of,
    checkedByPerson: page.checked_by_person,
  };
}

const byName = (a: PairRow, b: PairRow) =>
  a.intervention.localeCompare(b.intervention) || a.condition.localeCompare(b.condition);

/** Whether a MeSH tree number is the given one or beneath it. */
function atOrBeneath(treeNumber: string, top: string): boolean {
  return treeNumber === top || treeNumber.startsWith(`${top}.`);
}

/** The pairs whose condition sits at or beneath any of the given tree numbers. */
export function pairsBeneath(treeNumbers: string[]): PairRow[] {
  return Object.values(pairPages())
    .filter((page) =>
      page.row.descriptor.tree_numbers.some((number: string) => treeNumbers.some((top) => atOrBeneath(number, top))),
    )
    .map(pairRow)
    .sort(byName);
}

export interface ConditionListing {
  slug: string;
  descriptorId: string;
  label: string;
  treeNumbers: string[];
  pairs: PairRow[];
}

/** One listing a condition that a pair is for, with every pair at or beneath it. */
export function conditionListings(): ConditionListing[] {
  const conditions = new Map<string, any>();
  for (const page of Object.values(pairPages())) {
    conditions.set(page.row.condition.slug, { slug: page.row.condition.slug, ...page.row.descriptor });
  }
  return [...conditions.values()]
    .map((condition) => ({
      slug: condition.slug,
      descriptorId: condition.descriptor_id,
      label: condition.label,
      treeNumbers: condition.tree_numbers,
      pairs: pairsBeneath(condition.tree_numbers),
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export interface InterventionListing {
  slug: string;
  name: string;
  otherNames: string[];
  approach: string | null;
  pairs: PairRow[];
}

/** The published pairs a listing page lists, as rows: the same pairs the Worker's page for it
 * lists (lib/listing-view.ts), so every count the build shows matches the page it links. */
function listedRows(view: ListingView): PairRow[] {
  const pages = pairPages();
  return view.rows.map((row) => pairRow(pages[row.address])).sort(byName);
}

const publishedPairs = () => new Set(Object.keys(pairPages()));

/** One listing an intervention the bundle has a page for, with the pairs its file lists. */
export function interventionListings(): InterventionListing[] {
  const published = publishedPairs();
  return Object.values(pairBundle().pages.PairInterventionPage ?? {})
    .map((file: any) => {
      const preferred = file.intervention.preferred_name;
      return {
        slug: file.intervention.slug,
        name: shownName(preferred),
        otherNames: [
          ...new Set(
            file.names
              .filter((name: any) => name.role !== "preferred" && name.name.toLowerCase() !== preferred.toLowerCase())
              .map((name: any) => shownName(name.name)),
          ),
        ] as string[],
        approach: file.approach?.approach ? PAIR_APPROACH_LABELS[file.approach.approach] : null,
        pairs: listedRows(interventionListing(file, published)),
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

export interface TopicListing {
  slug: string;
  title: string;
  pairs: PairRow[];
}

/** One listing a topic of the bundle's topics page, with the pairs the lab filed under it. */
export function topicListings(): TopicListing[] {
  const topics = Object.values(pairBundle().pages.PairTopicsPage ?? {})[0];
  if (!topics) return [];
  const published = publishedPairs();
  const files = pairBundle().pages.PairTopicPage ?? {};
  return topics.verticals
    .map((vertical: any) => ({
      slug: vertical.slug,
      title: vertical.title,
      // The pairs the topic's own file lists; a topic with no file lists none.
      pairs: files[vertical.slug] ? listedRows(topicListing(files[vertical.slug], published)) : [],
    }))
    .sort((a: TopicListing, b: TopicListing) => a.title.localeCompare(b.title));
}

export interface CategoryListing {
  descriptorId: string;
  label: string;
  treeNumbers: string[];
  broader: { descriptorId: string; label: string }[];
  narrower: { descriptorId: string; label: string; count: number }[];
  pairs: PairRow[];
}

/** One listing a clinical category the bundle has a page for, with every pair at or
 * beneath it. A narrower category with no pair beneath it is left out. */
export function categoryListings(): CategoryListing[] {
  const files = Object.values(pairBundle().pages.PairClinicalCategoryPage ?? {});
  const categories = new Set(files.map((file: any) => file.descriptor.descriptor_id));
  const published = publishedPairs();
  const idOf = (href: string) => href.slice("/clinical/".length);
  return files
    .map((file: any) => {
      const view = categoryListing(file, published, categories);
      const group = (label: string) => view.linkGroups.find((one) => one.label === label)?.links ?? [];
      return {
        descriptorId: file.descriptor.descriptor_id,
        label: file.descriptor.label,
        treeNumbers: file.descriptor.tree_numbers,
        broader: group("Broader").map((link) => ({ descriptorId: idOf(link.href), label: link.label })),
        narrower: group("Narrower").map((link) => ({ descriptorId: idOf(link.href), label: link.label, count: link.count ?? 0 })),
        pairs: listedRows(view),
      };
    })
    .sort((a: CategoryListing, b: CategoryListing) => a.label.localeCompare(b.label));
}

export interface TopicEntry {
  slug: string;
  title: string;
  group: { slug: string; title: string } | null;
  count: number;
}

/** The topics page on the pair path: each topic with a pair filed under it, with its group
 * from the bundle's topics page. */
export function topicsIndex(): TopicEntry[] {
  const topics = Object.values(pairBundle().pages.PairTopicsPage ?? {})[0];
  if (!topics) return [];
  const groups = new Map(topics.groups.map((group: any) => [group.slug, group]));
  const counts = new Map(topicListings().map((listing) => [listing.slug, listing.pairs.length]));
  return topics.verticals
    .filter((vertical: any) => (counts.get(vertical.slug) ?? 0) > 0)
    .map((vertical: any) => {
      const group: any = vertical.group ? groups.get(vertical.group) : null;
      return {
        slug: vertical.slug,
        title: vertical.title,
        group: group ? { slug: group.slug, title: group.title } : null,
        count: counts.get(vertical.slug) ?? 0,
      };
    })
    .sort((a: TopicEntry, b: TopicEntry) => a.title.localeCompare(b.title));
}

/** The clinical index on the pair path: the categories with no broader one in the bundle,
 * each with the pairs at or beneath it. */
export function clinicalTops(): { descriptorId: string; label: string; count: number }[] {
  return categoryListings()
    .filter((listing) => listing.broader.length === 0 && listing.pairs.length > 0)
    .map((listing) => ({ descriptorId: listing.descriptorId, label: listing.label, count: listing.pairs.length }));
}

export interface PairChange {
  address: string;
  title: string;
  on: string;
  code: string;
  before: string | null;
}

/** Every pair's status changes, from its own history, newest first; on one day, by title. */
export function pairChanges(): PairChange[] {
  return Object.values(pairPages())
    .flatMap((page) => {
      const title = `${shownName(page.row.intervention.preferred_name)} for ${page.row.descriptor.label.toLowerCase()}`;
      return page.history.map((change: any) => ({
        address: page.row.pair.address,
        title,
        on: change.on,
        code: change.after,
        before: change.before,
      }));
    })
    .sort((a, b) => (a.on === b.on ? a.title.localeCompare(b.title) : a.on < b.on ? 1 : -1));
}

// The lookup file and open data on the pair path (openspec pairs-site, task 3.3).

/** One pair as the lookup file words it: the keys the released extension reads, as
 * the lookup file has always given them, so the extension needs no release at the cutover. */
export function pairLookup(page: any) {
  const view = pairView(page);
  const report = page.row.first_report;
  return {
    headline: `${view.intervention} for ${view.condition.toLowerCase()}`,
    page: `/${view.address}`,
    status: view.status,
    meaning: STATUS_MEANINGS[view.statusCode as keyof typeof STATUS_MEANINGS],
    place: STAGE_PATH.indexOf(view.statusCode as (typeof STAGE_PATH)[number]) + 1 || null,
    no_signal: overlayText(page.row.status.overlay_years),
    first_reported: report?.published ? formatDate(report.published) : null,
    latest_promise: null,
    unchecked: view.checkedByPerson ? null : UNCHECKED_NOTE,
    names: [view.intervention, ...view.otherNames],
    indication: view.condition,
    terms: [view.condition, ...(report ? [report.title] : [])].join(" "),
    // The site's search answer reads the topic; the extension does not.
    topic: page.row.filing?.vertical ?? null,
  };
}

export type PairLookup = ReturnType<typeof pairLookup>;

/** The lookup file's `articles` and `claims`: every pair by its address,
 * and each pair's first report by its address in comparison form, where the lab holds one. */
export function pairLookupMaps(): { articles: Record<string, string[]>; claims: Record<string, unknown> } {
  const articles: Record<string, string[]> = {};
  const claims: Record<string, unknown> = {};
  for (const page of Object.values(pairPages())) {
    const address = page.row.pair.address;
    claims[address] = pairLookup(page);
    const url = page.row.first_report?.url;
    const compared = url ? articleKey(url) : null;
    if (compared === null) continue;
    const addresses = (articles[compared] ??= []);
    if (!addresses.includes(address)) addresses.push(address);
  }
  return { articles, claims };
}

export { PAIR_RECORD_FORMAT };
export const PAIR_INDEX_FORMAT = { format: "pairs-index", format_version: 1 } as const;

/** The pairs whose open data record the build writes: those whose page it builds ahead, and
 * a data file with no page. Every other record is served on request from D1
 * (worker/pairs.mjs), so a full bundle does not take a file per pair in the deployment,
 * whose file limit it would pass (task 1.3; docs/sources.md, Workers static assets). */
export function builtAheadRecords(): string[] {
  const pages = pairPages();
  return Object.keys(pairBundle().pages.PairDataFile ?? {})
    .filter((address) => !pages[address] || builtAhead(pages[address]))
    .sort();
}

/** The index of the pairs' open data records. */
export function pairDataIndex(siteName: string, siteUrl: string) {
  return {
    ...PAIR_INDEX_FORMAT,
    ...pairDataHeader(siteName, siteUrl),
    entries: Object.keys(pairBundle().pages.PairDataFile ?? {})
      .sort()
      .map((address) => {
        const row = pairRow(pairPages()[address]);
        return {
          address,
          intervention: row.intervention,
          condition: row.condition,
          status: { code: row.statusCode },
          record: `/data/pairs/${address}.json`,
        };
      }),
  };
}
