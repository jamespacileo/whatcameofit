// An Atom feed of one claim's status changes, newest first.
import type { APIRoute } from "astro";
import { SITE } from "../../../site.config.mjs";
import { changesFeed, changesOf } from "../../lib/changes";
import { claimPaths, data, type ExportedClaim } from "../../lib/export";

export const getStaticPaths = claimPaths;

export const GET: APIRoute = ({ props }) => {
  const claim = props.claim as ExportedClaim;
  const xml = changesFeed({
    title: `${SITE.name} ${claim.headline}`,
    self: `${SITE.url}/changes/${claim.slug}.xml`,
    page: `${SITE.url}/${claim.slug}`,
    site: SITE.url,
    changes: changesOf(claim).reverse(),
    generatedAt: data.generated_at,
  });
  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
