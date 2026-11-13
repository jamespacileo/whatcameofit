// Each claim's oEmbed description: how a site that turns pasted links into embeds
// (WordPress, Ghost, Notion and others) finds the claim's embed. The claim page
// announces it; the embed itself is the same as the snippet the claim page gives.
import type { APIRoute, GetStaticPaths } from "astro";
import { SITE } from "../../../site.config.mjs";
import { data, type ExportedClaim } from "../../lib/export";
import { EMBED_SIZE, embedSnippet } from "../../lib/share";
import { canonicalAddress } from "../../lib/structured";

export const getStaticPaths: GetStaticPaths = () =>
  data.claims.map((claim) => ({ params: { slug: claim.slug }, props: { claim } }));

export const GET: APIRoute = ({ props }) => {
  const { claim } = props as { claim: ExportedClaim };
  const body = {
    version: "1.0",
    type: "rich",
    title: claim.headline,
    provider_name: SITE.name,
    provider_url: canonicalAddress("/"),
    html: embedSnippet(SITE.url, claim.slug, claim.headline),
    width: EMBED_SIZE.width,
    height: EMBED_SIZE.height,
    thumbnail_url: canonicalAddress(`/og/${claim.slug}.png`),
    thumbnail_width: 1200,
    thumbnail_height: 630,
    // A day: the registries are checked at most twice a day.
    cache_age: 86400,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json+oembed; charset=utf-8" },
  });
};
