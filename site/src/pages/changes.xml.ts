// An Atom feed of status changes across every published claim, newest first. A build that
// reads a bundle (openspec pairs-site) lists every pair's status changes instead.
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { allChanges, changesFeed, type StatusChange } from "../lib/changes";
import { data, type ExportedClaim, type StatusCode } from "../lib/export";
import { pairBundleFolder, pairChanges } from "../lib/pairs";

/** A pair's change in the feed's shape: an entry links to and is titled by the pair. */
function pairEntries(): StatusChange[] {
  return pairChanges().map((change) => ({
    claim: { slug: change.address, headline: change.title } as ExportedClaim,
    on: change.on,
    code: change.code as StatusCode,
    before: change.before as StatusCode | null,
  }));
}

export const GET: APIRoute = () => {
  const xml = changesFeed({
    title: `${SITE.name} Status changes`,
    self: `${SITE.url}/changes.xml`,
    page: `${SITE.url}/`,
    site: SITE.url,
    changes: pairBundleFolder() ? pairEntries() : allChanges(data.claims),
    generatedAt: data.generated_at,
  });
  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
