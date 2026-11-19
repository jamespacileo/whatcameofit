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
import { pairBundleFolder, pairPages } from "../lib/pairs";

/** The same on the pair path (openspec pairs-site): each pair's first report, where the lab
 * holds one, and its trials, keyed by the pair's address. */
function pairDetail(): Record<string, unknown> {
  const pairs: Record<string, unknown> = {};
  for (const [address, page] of Object.entries(pairPages())) {
    const report = page.row.first_report;
    const domain = report ? outletDomain(report.url) : null;
    pairs[address] = {
      reports: report
        ? [
            {
              title: report.title,
              outlet: report.outlet.trim() || domain,
              domain,
              icon: outletIconPath(domain!) ?? null,
              url: report.url,
              date: report.published ? formatDate(report.published) : null,
            },
          ]
        : [],
      trials: page.trials.map((trial: any) => ({
        id: trial.nct_id,
        title: trial.facts.title,
        registry: "ClinicalTrials.gov",
        url: `https://clinicaltrials.gov/study/${trial.nct_id}`,
        phases: (trial.facts.phases ?? []).map((phase: string) => PHASE_WORDS[phase] ?? phase),
      })),
    };
  }
  return pairs;
}

export const GET: APIRoute = () => {
  if (pairBundleFolder()) return Response.json({ schema_version: 1, claims: pairDetail() });
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
