// The trial a paper reports, from Europe PMC. Terms and limits: docs/sources.md. A news
// page links to its paper far more often than it gives a registry number; the paper's
// abstract gives the number. Nothing of the abstract is returned or kept. The same rule
// as the pipeline's thenwhat.sources.europepmc.trial_numbers; keep the two in step.

import { withDeadline } from "./deadline.mjs";

const API = "https://www.ebi.ac.uk/europepmc/webservices/rest";
const VERSION = "1";
const REGISTRY_NUMBER = /NCT\d{8}/gi;
// A paper that reports a trial gives its number, sometimes two. One that lists more is a
// review of many trials and identifies none.
const MAX_TRIALS_OF_ONE_PAPER = 3;
// One request, its body included. A paper is optional to a lookup; it is not waited on long.
const TIMEOUT_MS = 5_000;

export function makePapers({ fetch, contact, timeoutMs = TIMEOUT_MS }) {
  const headers = { "User-Agent": `thenwhat-lookup/${VERSION} (mailto:${contact})`, Accept: "application/json" };

  return {
    /** The ClinicalTrials.gov numbers the paper's abstract gives for its own trial. */
    async trialNumbers({ doi, pubmedId }) {
      let query;
      if (doi) query = `DOI:"${String(doi).replaceAll('"', "")}"`;
      else if (/^\d+$/.test(pubmedId ?? "")) query = `EXT_ID:${pubmedId} AND SRC:MED`;
      else return [];
      const url = new URL(`${API}/search`);
      for (const [name, value] of Object.entries({ query, format: "json", resultType: "core" })) {
        url.searchParams.set(name, value);
      }
      // Unavailable in time is an error, never a paper with no trial.
      const paper = await withDeadline(timeoutMs, async (signal) => {
        const response = await fetch(url.href, { headers, signal });
        if (!response.ok) throw new Error(`papers ${response.status}`);
        return (await response.json())?.resultList?.result?.[0];
      }, { label: "papers" });
      const found = String(paper?.abstractText ?? "").match(REGISTRY_NUMBER) ?? [];
      const numbers = [...new Set(found.map((number) => number.toUpperCase()))];
      return numbers.length <= MAX_TRIALS_OF_ONE_PAPER ? numbers : [];
    },
  };
}
