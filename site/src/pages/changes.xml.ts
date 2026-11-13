// An Atom feed of status changes across every published claim, newest first.
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { allChanges, changesFeed } from "../lib/changes";
import { data } from "../lib/export";

export const GET: APIRoute = () => {
  const xml = changesFeed({
    title: `${SITE.name} Status changes`,
    self: `${SITE.url}/changes.xml`,
    page: `${SITE.url}/`,
    site: SITE.url,
    changes: allChanges(data.claims),
    generatedAt: data.generated_at,
  });
  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
