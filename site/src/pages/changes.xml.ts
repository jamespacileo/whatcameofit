// An Atom feed of every pair's status changes, newest first.
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { changesFeed, type StatusChange } from "../lib/changes";
import { bundleMadeAt, pairChanges } from "../lib/pairs";

export const GET: APIRoute = () => {
  const xml = changesFeed({
    title: `${SITE.name} Status changes`,
    self: `${SITE.url}/changes.xml`,
    page: `${SITE.url}/`,
    site: SITE.url,
    changes: pairChanges() as StatusChange[],
    generatedAt: bundleMadeAt(),
  });
  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
