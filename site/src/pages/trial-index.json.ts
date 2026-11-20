// Which pairs each trial supports, by registry number. The trial reader (worker/trials.mjs)
// reads it to decide whether a trial has a page and where the page leads; the lookup box
// reads it to send a searched registry number to its pair.
import type { APIRoute } from "astro";
import { pairPages, shownName } from "../lib/pairs";

export const GET: APIRoute = () => {
  const trials: Record<string, { slug: string; headline: string }[]> = {};
  for (const page of Object.values(pairPages())) {
    // The keys are the ones the trial reader and the lookup box already read.
    const pair = {
      slug: page.row.pair.address,
      headline: `${shownName(page.row.intervention.preferred_name)} for ${page.row.descriptor.label.toLowerCase()}`,
    };
    for (const trial of page.trials) (trials[trial.nct_id] ??= []).push(pair);
  }
  return Response.json({ trials });
};
