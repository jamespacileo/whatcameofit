// The article lookup file: which published claim each source article reports, with
// the claim's status already in the site's wording. The browser extension downloads
// it and compares addresses inside the browser. It holds no article text.
import type { APIRoute } from "astro";
import { articleKey } from "../lib/article-key.mjs";
import { data } from "../lib/export";
import { NOTICES, UNCHECKED_NOTE } from "../lib/notices";
import { STATUS_LABELS, STATUS_MEANINGS, latestPromise, overlayText } from "../lib/status";
import { formatDate } from "../lib/timetable";

export const GET: APIRoute = () => {
  const articles: Record<string, string[]> = {};
  const claims: Record<string, unknown> = {};

  for (const claim of data.claims) {
    const promise = latestPromise(claim);
    claims[claim.slug] = {
      headline: claim.headline,
      page: `/${claim.slug}`,
      status: STATUS_LABELS[claim.status.code],
      meaning: STATUS_MEANINGS[claim.status.code],
      no_signal: overlayText(claim.status.overlay_years),
      first_reported: claim.first_reported_date ? formatDate(claim.first_reported_date) : null,
      latest_promise: promise
        ? `${promise.description} (by ${promise.parsed_date!.slice(0, 4)})`
        : null,
      unchecked: claim.checked_by_person ? null : UNCHECKED_NOTE,
    };
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
    articles,
    claims,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
