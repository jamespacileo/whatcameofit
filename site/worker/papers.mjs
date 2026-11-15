// The trial a paper reports, from Europe PMC. Terms and limits: docs/sources.md. A news
// page links to its paper far more often than it gives a registry number; the paper's
// abstract gives the number. Nothing of the abstract is returned or kept. The same rule
// as the pipeline's thenwhat.sources.europepmc.trial_numbers; keep the two in step.
// A paper's trial numbers may be reused for a day; the abstract itself is never kept.

import { withDeadline } from "./deadline.mjs";
import { SOURCE_TTL_SECONDS, makeShared, makeSourceCache } from "./public-cache.mjs";

const API = "https://www.ebi.ac.uk/europepmc/webservices/rest";
const VERSION = "1";
const REGISTRY_NUMBER = /NCT\d{8}/gi;
// A paper that reports a trial gives its number, sometimes two. One that lists more is a
// review of many trials and identifies none.
const MAX_TRIALS_OF_ONE_PAPER = 3;
// One request, its body included. A paper is optional to a lookup; it is not waited on
// long. Europe PMC answers a record it has served lately in under a second and one it
// has not in up to half a minute, so a paper passed over here is counted in the answer.
const TIMEOUT_MS = 5_000;
// A paper Europe PMC does not hold yet may be added soon: that answer is kept briefly.
const NO_RECORD_SECONDS = 3_600;
const REQUEST_SPACING_MS = 500;
const numbersOnly = (value) => Array.isArray(value) && value.length <= MAX_TRIALS_OF_ONE_PAPER &&
  value.every((number) => typeof number === "string" && /^NCT\d{8}$/.test(number));

export function makePapers({ fetch, contact, timeoutMs = TIMEOUT_MS, cache, cacheTimeoutMs, requestSpacingMs = REQUEST_SPACING_MS }) {
  const headers = { "User-Agent": `thenwhat-lookup/${VERSION} (mailto:${contact})`, Accept: "application/json" };
  const reuse = makeSourceCache(cache, { kind: "papers", timeoutMs: cacheTimeoutMs });
  const shared = makeShared();
  let starts = Promise.resolve();
  let lastStart = -Infinity;
  // Reserve origin starts after the cache check: variable cache latency must not
  // bunch misses together. Only starts are serialized, not response bodies.
  function start(url, signal) {
    const slot = starts.then(async () => {
      while (!signal.aborted && Date.now() - lastStart < requestSpacingMs) {
        await new Promise((resolve) => {
          const done = () => { clearTimeout(timer); signal.removeEventListener("abort", done); resolve(); };
          const timer = setTimeout(done, requestSpacingMs - (Date.now() - lastStart));
          signal.addEventListener("abort", done, { once: true });
        });
      }
      signal.throwIfAborted();
      // Wrap the promise so the next start does not wait for the response.
      // Measure after invoking fetch: its synchronous setup can cross a clock tick.
      const response = fetch(url, { headers, signal });
      lastStart = Date.now();
      return { response };
    });
    starts = slot.then(() => {}, () => {});
    return slot.then(({ response }) => response);
  }

  return {
    /**
     * The ClinicalTrials.gov numbers the paper's abstract gives for its own trial.
     * Aborting `signal` ends the request: the caller no longer needs the answer. A paper
     * not answered within the deadline is refused as timed out, never guessed at.
     */
    async trialNumbers({ doi, pubmedId }, { signal: parent } = {}) {
      let query;
      if (doi) query = `DOI:"${String(doi).replaceAll('"', "")}"`;
      else if (/^\d+$/.test(pubmedId ?? "")) query = `EXT_ID:${pubmedId} AND SRC:MED`;
      else return [];
      const url = new URL(`${API}/search`);
      for (const [name, value] of Object.entries({ query, format: "json", resultType: "core" })) {
        url.searchParams.set(name, value);
      }
      // The same paper asked twice at once is asked of Europe PMC once.
      return shared(url.href, async (signal) => {
        const key = await reuse.key(query);
        const saved = await reuse.get(key);
        if (numbersOnly(saved)) return [...saved];
        // Unavailable in time is an error, never a paper with no trial, and is not kept.
        const paper = await withDeadline(timeoutMs, async (deadline) => {
          const response = await start(url.href, deadline);
          if (!response.ok) throw new Error(`papers ${response.status}`);
          return (await response.json())?.resultList?.result?.[0];
        }, { label: "papers", parent: signal });
        const found = String(paper?.abstractText ?? "").match(REGISTRY_NUMBER) ?? [];
        const unique = [...new Set(found.map((number) => number.toUpperCase()))];
        const numbers = unique.length <= MAX_TRIALS_OF_ONE_PAPER ? unique : [];
        // Only the registry numbers are kept, never the abstract they were read from.
        await reuse.put(key, numbers, paper ? SOURCE_TTL_SECONDS : NO_RECORD_SECONDS);
        return [...numbers];
      }, parent);
    },
  };
}
