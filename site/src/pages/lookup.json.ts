// The article lookup file: which published claim each source article reports, with
// the claim's status already in the site's wording. The browser extension downloads
// it and compares addresses inside the browser. It holds no article text.
import type { APIRoute } from "astro";
import { articleKey } from "../lib/article-key.mjs";
import { data, listedTopics } from "../lib/export";
import { lookupClaim } from "../lib/lookup-claim";
import { NOTICES } from "../lib/notices";
import { STAGE_PATH } from "../lib/status";
import { SITE } from "../../site.config.mjs";
import { formatDate } from "../lib/timetable";

export const GET: APIRoute = () => {
  const articles: Record<string, string[]> = {};
  const claims: Record<string, unknown> = {};

  for (const claim of data.claims) {
    // The topic is the site's search answer's, for its topic counts and links; the
    // extension does not read it.
    claims[claim.slug] = { ...lookupClaim(claim), topic: claim.vertical };
    for (const article of claim.articles) {
      const key = articleKey(article.url);
      if (key === null) continue;
      const slugs = (articles[key] ??= []);
      if (!slugs.includes(claim.slug)) slugs.push(claim.slug);
    }
  }

  const body = {
    schema_version: 1,
    generated_at: data.generated_at,
    last_checked: data.last_checked_at ? formatDate(data.last_checked_at) : null,
    preview: data.preview,
    notices: NOTICES,
    // Where a registry search may be asked for, or null when this site offers none.
    // The browser extension reads it here, so it need not be rebuilt when that changes.
    live: SITE.lookupUrl,
    places: STAGE_PATH.length,
    // Each listed topic's name and how many published claims it holds.
    topics: Object.fromEntries(
      listedTopics.map((topic) => [
        topic.slug,
        { title: topic.title, count: data.claims.filter((claim) => claim.vertical === topic.slug).length },
      ]),
    ),
    articles,
    claims,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
