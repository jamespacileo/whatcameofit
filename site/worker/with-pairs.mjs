// The Worker of a deployment that serves pair pages on request (openspec pairs-site): the
// site's own Worker, and, for a pair address the build did not make, the page from D1
// (worker/pairs.mjs), and so for a pair's open data record. Only a pull request's preview uses it (wrangler.preview.jsonc and the
// PAIRS binding it is given); production's Worker is worker/index.mjs alone until the cutover.
// The validators are those the build wrote from the bundle's schemas (scripts/bundle-code.mjs).
import * as validators from "../.bundle-code/validators.mjs";
import { handle } from "./index.mjs";
import { listingOf, listingPage } from "./listings.mjs";
import { SHELL_PATH, pairAddress, pairPage, pairRecord, recordAddress } from "./pairs.mjs";

const { validatePairDataFile, validatePairInterventionPage, validatePairPage } = validators;

export async function handleWithPairs(request, env, cache = globalThis.caches?.default ?? null) {
  const url = new URL(request.url);
  // The frame is the Worker's to fill, never a page of its own.
  if (url.pathname === SHELL_PATH || url.pathname === `${SHELL_PATH}/`) {
    return handle(new Request(new URL("/__no-such-page__", url), request), env);
  }
  const answer = await handle(request, env);
  if (answer.status !== 404) return answer;
  if (pairAddress(url.pathname)) return (await pairPage(request, env, validatePairPage, cache, validatePairInterventionPage)) ?? answer;
  // A pair's open data record the build did not write (task 1.3).
  if (recordAddress(url.pathname)) return (await pairRecord(request, env, validatePairDataFile, cache)) ?? answer;
  // An intervention's, clinical category's or topic's page: every one is made here.
  if (listingOf(url.pathname)) return (await listingPage(request, env, validators, cache)) ?? answer;
  return answer;
}

/**
 * The answer with the robots mark set, whatever made it: a page made here, a file from the
 * assets, a redirect, a not-found or gone page, an error or a 304. Staging's configuration
 * sets ROBOTS_NOINDEX (wrangler.staging.jsonc); production and previews do not.
 */
export function markedNoindex(answer) {
  const headers = new Headers(answer.headers);
  headers.set("X-Robots-Tag", "noindex");
  return new Response(answer.body, { status: answer.status, statusText: answer.statusText, headers });
}

export default {
  fetch: async (request, env) => {
    const answer = await handleWithPairs(request, env);
    return env.ROBOTS_NOINDEX === "1" ? markedNoindex(answer) : answer;
  },
};
