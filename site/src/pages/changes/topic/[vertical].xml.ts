// An Atom feed of one topic's status changes, newest first.
import type { APIRoute } from "astro";
import { SITE } from "../../../../site.config.mjs";
import { allChanges, changesFeed } from "../../../lib/changes";
import { data } from "../../../lib/export";

export function getStaticPaths() {
  return data.verticals.map((vertical) => ({
    params: { vertical: vertical.slug },
    props: { vertical },
  }));
}

export const GET: APIRoute = ({ props }) => {
  const vertical = props.vertical as (typeof data.verticals)[number];
  const claims = data.claims.filter((claim) => claim.vertical === vertical.slug);
  const xml = changesFeed({
    title: `${SITE.name} ${vertical.title}`,
    self: `${SITE.url}/changes/topic/${vertical.slug}.xml`,
    page: `${SITE.url}/topic/${vertical.slug}`,
    site: SITE.url,
    changes: allChanges(claims),
    generatedAt: data.generated_at,
  });
  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
