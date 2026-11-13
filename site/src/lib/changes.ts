// A claim's status changes, as feeds. The history comes from the pipeline, which runs
// the status rules on what was dated up to each day; nothing is derived here. An export
// made before the history existed carries none, and then a feed has no entries.
import type { ExportedClaim, StatusCode } from "./export";
import { STATUS_LABELS, assertNeutral } from "./status.ts";

export interface StatusChange {
  claim: ExportedClaim;
  /** The day the status became `code`, as YYYY-MM-DD. */
  on: string;
  code: StatusCode;
  /** The status before, or null for the claim's first status. */
  before: StatusCode | null;
}

/** One claim's changes, oldest first. */
export function changesOf(claim: ExportedClaim): StatusChange[] {
  return (claim.status.history ?? []).map((change, index, history) => ({
    claim,
    on: change.on,
    code: change.code,
    before: index > 0 ? history[index - 1].code : null,
  }));
}

/** Every claim's changes, newest first; on one day, by headline. */
export function allChanges(claims: ExportedClaim[]): StatusChange[] {
  return claims
    .flatMap(changesOf)
    .sort((a, b) =>
      a.on === b.on ? a.claim.headline.localeCompare(b.claim.headline) : a.on < b.on ? 1 : -1,
    );
}

/** What changed, in the site's own status wording and nothing more. */
export function changeSummary(change: StatusChange): string {
  const now = STATUS_LABELS[change.code];
  return change.before === null
    ? `First status: ${now}.`
    : `Was: ${STATUS_LABELS[change.before]}. Now: ${now}.`;
}

const escape = (text: string) =>
  text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

interface Feed {
  title: string;
  /** The feed's own address. */
  self: string;
  /** The page a reader would open instead. */
  page: string;
  /** The site's address, to build each claim's link. */
  site: string;
  /** Newest first. */
  changes: StatusChange[];
  /** The date the export was made, used when there is no change to date the feed by. */
  generatedAt: string;
}

/** An Atom feed. Each entry is dated to its change, never to the build. */
export function changesFeed(feed: Feed): string {
  const { title, self, page, site, changes, generatedAt } = feed;
  const updated = `${changes[0]?.on ?? generatedAt.slice(0, 10)}T00:00:00Z`;
  const summaries = changes.map(changeSummary);
  assertNeutral(summaries);
  const entries = changes.map((change, index) => {
    const link = `${site}/${change.claim.slug}`;
    return [
      "  <entry>",
      `    <title>${escape(change.claim.headline)}</title>`,
      `    <id>${escape(`${link}#status-${change.on}-${change.code}`)}</id>`,
      `    <link href="${escape(link)}"/>`,
      `    <updated>${change.on}T00:00:00Z</updated>`,
      `    <summary>${escape(summaries[index])}</summary>`,
      "  </entry>",
    ].join("\n");
  });
  return [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    `  <title>${escape(title)}</title>`,
    `  <id>${escape(self)}</id>`,
    `  <link rel="self" href="${escape(self)}"/>`,
    `  <link href="${escape(page)}"/>`,
    `  <updated>${updated}</updated>`,
    ...entries,
    "</feed>",
    "",
  ].join("\n");
}
