// What the site's search says a match rests on: each published claim's reports, by
// outlet, title and date, and the trials matched to it, by registry identifier and
// title. The lookup box reads it only when words are searched, to say under each
// claim which report or trial the words were found in, and to answer a registry
// identifier with its trial. It holds no article text.
import type { APIRoute } from "astro";
import { data } from "../lib/export";
import { outletDomain, outletIconPath } from "../lib/outlets";
import { sourceName } from "../lib/status";
import { formatDate } from "../lib/timetable";
import { PHASE_WORDS } from "../lib/trial-facts";

export const GET: APIRoute = () => {
  const claims: Record<string, unknown> = {};
  for (const claim of data.claims) {
    claims[claim.slug] = {
      reports: claim.articles.map((article) => {
        const domain = outletDomain(article.url);
        return {
          title: article.title,
          outlet: article.outlet.trim() || domain,
          domain,
          icon: outletIconPath(domain) ?? null,
          url: article.url,
          date: article.published_date ? formatDate(article.published_date) : null,
        };
      }),
      trials: (claim.trials ?? []).map((trial) => ({
        id: trial.trial_id,
        title: trial.title,
        registry: sourceName(trial.source_name),
        url: trial.url,
        phases: trial.phases.map((phase) => PHASE_WORDS[phase] ?? phase),
      })),
    };
  }
  return Response.json({ schema_version: 1, claims });
};
