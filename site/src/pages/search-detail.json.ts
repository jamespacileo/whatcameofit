// What the site's search says a match rests on: each pair's first report, where the bundle
// holds one, by outlet, title and date, and its trials, by registry identifier and title.
// The lookup box reads it only when words are searched, to say under each pair which
// report or trial the words were found in, and to answer a registry identifier with its
// trial. It holds no article text. `pairs` is every pair, by address.
import type { APIRoute } from "astro";
import { formatDate } from "../lib/timetable";
import { PHASE_WORDS } from "../lib/trial-facts";
import { pairPages } from "../lib/pairs";

/** An article's host without a leading www. */
const outletDomain = (url: string): string => (URL.canParse(url) ? new URL(url).hostname.replace(/^www\./, "") : "");

export const GET: APIRoute = () => {
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
              // The bundle carries no outlet icon; the lookup box draws a letter tile.
              icon: null,
              url: report.url,
              date: report.published ? formatDate(report.published) : null,
            },
          ]
        : [],
      trials: page.trials.map((trial: any) => ({
        id: trial.nct_id,
        title: trial.facts.title,
        phases: (trial.facts.phases ?? []).map((phase: string) => PHASE_WORDS[phase] ?? phase),
      })),
    };
  }
  // Each trial by its identifier alone: its registry and address are the same rule for
  // every trial, and the reader adds them (readSearchDetail in src/lib/lookup-file.mjs).
  return Response.json({ schema_version: 3, pairs });
};
