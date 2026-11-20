// A pair's oEmbed description (openspec pairs-site): how a site that turns pasted links into
// embeds finds the pair's embed. The pair page announces it.
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { pairPages, pairView } from "../lib/pairs";
import { EMBED_SIZE, embedSnippet } from "../lib/share";
import { canonicalAddress } from "../lib/structured";

export function getStaticPaths() {
  return Object.entries(pairPages()).map(([address, page]) => ({ params: { address }, props: { page } }));
}

export const GET: APIRoute = ({ props }) => {
  const view = pairView(props.page);
  const title = `${view.intervention} for ${view.condition.toLowerCase()}`;
  const body = {
    version: "1.0",
    type: "rich",
    title,
    provider_name: SITE.name,
    provider_url: canonicalAddress("/"),
    html: embedSnippet(SITE.url, view.address, title),
    width: EMBED_SIZE.width,
    height: EMBED_SIZE.height,
    thumbnail_url: canonicalAddress(`/og/${view.address}.png`),
    thumbnail_width: 1200,
    thumbnail_height: 630,
    // A day: the registries are checked at most twice a day.
    cache_age: 86400,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json+oembed; charset=utf-8" },
  });
};
