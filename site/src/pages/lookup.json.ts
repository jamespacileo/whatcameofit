// The lookup file: every pair by its address, with its status already in the site's
// wording, and the articles that report a pair where the bundle holds one. The browser
// extension downloads it and compares addresses inside the browser. It holds no article
// text. Its keys are the ones the released extension reads (`claims` is every pair, keyed by
// address), so the extension needs no release.
import type { APIRoute } from "astro";
import { bundleMadeAt, pairLookupMaps, topicsIndex } from "../lib/pairs";
import { NOTICES } from "../lib/notices";
import { STAGE_PATH } from "../lib/status";
import { SITE } from "../../site.config.mjs";
import { formatDate } from "../lib/timetable";

export const GET: APIRoute = () => {
  const { articles, claims } = pairLookupMaps();
  const body = {
    schema_version: 1,
    generated_at: bundleMadeAt(),
    last_checked: formatDate(bundleMadeAt()),
    // The released extension reads this key; a bundle holds published records only.
    preview: false,
    notices: NOTICES,
    // Where a registry search may be asked for, or null when this site offers none.
    // The browser extension reads it here, so it need not be rebuilt when that changes.
    live: SITE.lookupUrl,
    places: STAGE_PATH.length,
    // Each listed topic's name and how many it holds.
    topics: Object.fromEntries(topicsIndex().map((topic) => [topic.slug, { title: topic.title, count: topic.count }])),
    articles,
    claims,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
