// The pair pages (openspec pairs-site): what a page shows, from the lab's `PairPage` files.
// Until the cutover the claims site stays as it is, and pair pages are built only when the
// build is given a bundle folder in PAIRS_BUNDLE. A build without one is the claims site
// alone, so a merge to main publishes no pair page.
import path from "node:path";
import { APPROACH_LABELS } from "./approach.ts";
import { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES, readBundle, type Bundle } from "./bundle.ts";
import { STATUS_GLOSSES, STATUS_LABELS } from "./status.ts";
import { PHASE_WORDS, TRIAL_STATE_WORDS } from "./trial-facts.ts";

/** The bundle folder this build reads, or null when it builds no pair page. */
export function pairBundleFolder(): string | null {
  const folder = process.env.PAIRS_BUNDLE;
  return folder ? path.resolve(folder) : null;
}

let cached: Bundle | null | undefined;

/** The bundle this build reads, read once; null when it builds no pair page. */
export function pairBundle(): Bundle | null {
  if (cached === undefined) {
    const folder = pairBundleFolder();
    cached = folder ? readBundle(folder) : null;
  }
  return cached;
}

/** A name as the site shows it. The substance registry writes names in capitals
 * ("APITEGROMAB"); a name of letters alone is shown with only its first one capital. A name
 * with a digit is a code ("SRK-015") and is shown as written. */
export function shownName(name: string): string {
  if (name !== name.toUpperCase() || /\d/.test(name)) return name;
  return name[0] + name.slice(1).toLowerCase();
}

export interface PairEventView {
  key: string;
  day: string;
  label: string;
  nctId: string;
  estimated: boolean;
}

export interface PairTrialView {
  nctId: string;
  title: string | null;
  state: string;
  phases: string | null;
  participants: string | null;
  start: string | null;
  primaryCompletion: string | null;
  arms: string[];
  /** The arm that gives the pair's intervention, where the lab named one. */
  pairArm: string | null;
  whyStopped: string | null;
  events: PairEventView[];
  papers: number;
  resultsPosted: boolean;
  registryUrl: string;
}

export interface PairView {
  address: string;
  intervention: string;
  interventionSlug: string;
  condition: string;
  conditionId: string;
  conditionSlug: string;
  statusCode: string;
  status: string;
  gloss: string;
  asOf: string;
  /** The events that set the status, oldest first. */
  explainedBy: PairEventView[];
  trials: PairTrialView[];
  history: { on: string; before: string | null; after: string }[];
  otherNames: string[];
  approach: string | null;
  checkedByPerson: boolean;
  registryChecks: { registry: string; through: string }[];
  claimSlug: string | null;
}

function eventView(event: any): PairEventView {
  return {
    key: event.key,
    day: event.day,
    label: PAIR_EVENT_LABELS[event.kind],
    nctId: event.nct_id,
    estimated: event.day_basis === "registry_date_estimated",
  };
}

const byDay = (a: { day: string }, b: { day: string }) => (a.day < b.day ? -1 : a.day > b.day ? 1 : 0);

/** What a pair page shows, in the site's words. The bundle was read by `readBundle`, which
 * stops on a code with no wording, so every lookup here finds its words. */
export function pairView(page: any): PairView {
  const { row } = page;
  const events = new Map<string, PairEventView>();
  for (const trial of page.trials) for (const event of trial.events) events.set(event.key, eventView(event));
  const preferred = row.intervention.preferred_name;
  const otherNames = [
    ...new Set(
      page.names
        .filter((name: any) => name.role !== "preferred" && name.name.toLowerCase() !== preferred.toLowerCase())
        .map((name: any) => shownName(name.name)),
    ),
  ] as string[];
  return {
    address: row.pair.address,
    intervention: shownName(preferred),
    interventionSlug: row.intervention.slug,
    condition: row.descriptor.label,
    conditionId: row.condition.descriptor_id,
    conditionSlug: row.condition.slug,
    statusCode: row.status.code,
    status: STATUS_LABELS[row.status.code as keyof typeof STATUS_LABELS],
    gloss: STATUS_GLOSSES[row.status.code as keyof typeof STATUS_GLOSSES],
    asOf: row.status.as_of,
    explainedBy: row.status.explained_by
      .map((key: string) => events.get(key))
      .filter((event: PairEventView | undefined): event is PairEventView => Boolean(event))
      .sort(byDay),
    trials: page.trials.map((trial: any): PairTrialView => {
      const facts = trial.facts;
      const phases = (facts.phases ?? []).map((phase: string) => PHASE_WORDS[phase]);
      return {
        nctId: trial.nct_id,
        title: facts.title,
        state: TRIAL_STATE_WORDS[PAIR_TRIAL_STATES[facts.overall_status]],
        phases: phases.length ? phases.join(" and ") : null,
        participants: facts.participants
          ? `${facts.participants.count.toLocaleString("en-GB")} ${facts.participants.actual ? "taking part" : "planned"}`
          : null,
        start: facts.start?.day ?? null,
        primaryCompletion: facts.primary_completion?.day ?? null,
        arms: trial.arms,
        pairArm: trial.claim_arm,
        whyStopped: facts.why_stopped,
        events: trial.events.map(eventView).sort(byDay),
        papers: trial.paper_ids.length,
        resultsPosted: trial.events.some((event: any) => event.kind === "results_posted"),
        registryUrl: `https://clinicaltrials.gov/study/${trial.nct_id}`,
      };
    }),
    history: page.history
      .map((change: any) => ({
        on: change.on,
        before: change.before ? STATUS_LABELS[change.before as keyof typeof STATUS_LABELS] : null,
        after: STATUS_LABELS[change.after as keyof typeof STATUS_LABELS],
      }))
      .sort((a: any, b: any) => (a.on < b.on ? -1 : 1)),
    otherNames,
    approach: page.approach?.approach ? APPROACH_LABELS[page.approach.approach] : null,
    checkedByPerson: page.checked_by_person,
    registryChecks: page.checked.map((check: any) => ({ registry: check.registry, through: check.checked_through })),
    claimSlug: row.origin?.claim_slug ?? null,
  };
}

/** The pair pages this build makes, by address. Empty when it reads no bundle. */
export function pairPages(): Record<string, any> {
  return pairBundle()?.pages.PairPage ?? {};
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

/** One listing an intervention the bundle has a page for, with its pairs. */
export function interventionListings(): InterventionListing[] {
  const pages = Object.values(pairPages());
  return Object.values(pairBundle()?.pages.PairInterventionPage ?? {})
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
        approach: file.approach?.approach ? APPROACH_LABELS[file.approach.approach] : null,
        pairs: pages
          .filter((page) => page.row.intervention.id === file.intervention.id)
          .map(pairRow)
          .sort(byName),
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
  const topics = Object.values(pairBundle()?.pages.PairTopicsPage ?? {})[0];
  if (!topics) return [];
  const pages = Object.values(pairPages());
  return topics.verticals
    .map((vertical: any) => ({
      slug: vertical.slug,
      title: vertical.title,
      pairs: pages
        .filter((page) => page.row.filing.vertical === vertical.slug)
        .map(pairRow)
        .sort(byName),
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
  const files = Object.values(pairBundle()?.pages.PairClinicalCategoryPage ?? {});
  const known = new Set(files.map((file: any) => file.descriptor.descriptor_id));
  const short = (descriptor: any) => ({ descriptorId: descriptor.descriptor_id, label: descriptor.label });
  return files
    .map((file: any) => ({
      descriptorId: file.descriptor.descriptor_id,
      label: file.descriptor.label,
      treeNumbers: file.descriptor.tree_numbers,
      broader: file.broader.filter((one: any) => known.has(one.descriptor_id)).map(short),
      narrower: file.narrower
        .map((one: any) => ({ ...short(one), count: pairsBeneath(one.tree_numbers).length }))
        .filter((one: any) => one.count > 0 && known.has(one.descriptorId)),
      pairs: pairsBeneath(file.descriptor.tree_numbers),
    }))
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
  const topics = Object.values(pairBundle()?.pages.PairTopicsPage ?? {})[0];
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
