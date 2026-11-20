// The lookup file, version 2: every pair by its address, with its status already in the
// site's wording, and the articles that report a pair where the bundle holds one. The
// site's lookup box and search, and the lookup Worker, read it; the next release of the
// browser extension will too. It holds no article text. One static file, served without the
// Worker: about 18 MB at 30,000 pairs (version 1 measured 2.56 MB for the rehearsal's 3,825
// pairs, and this version is 12% smaller; site/tests/pair-pages.build-test.mjs holds it),
// under the 25 MiB a static file may be. Version 1, `/lookup.json`, is built beside it for
// the released extension until a release reads this one.
// Shape: /mnt/project-files/claims-removal/lookup-index-by-pair.md (proposal, 2026-11-20).
import type { APIRoute } from "astro";
import { bundleMadeAt, pairLookupIndex, topicsIndex } from "../../lib/pairs";
import { NOTICES } from "../../lib/notices";
import { STAGE_PATH } from "../../lib/status";
import { SITE } from "../../../site.config.mjs";
import { formatDate } from "../../lib/timetable";
import { LOOKUP_FORMAT } from "../../lib/lookup-file.mjs";

export const GET: APIRoute = () => {
  const { articles, pairs } = pairLookupIndex();
  const body = {
    ...LOOKUP_FORMAT,
    generated_at: bundleMadeAt(),
    checked_on: formatDate(bundleMadeAt()),
    notices: NOTICES,
    // Where a registry search may be asked for, or null when this site offers none.
    live: SITE.lookupUrl,
    places: STAGE_PATH.length,
    // Each listed topic's name and how many it holds.
    topics: Object.fromEntries(topicsIndex().map((topic) => [topic.slug, { title: topic.title, count: topic.count }])),
    articles,
    pairs,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
