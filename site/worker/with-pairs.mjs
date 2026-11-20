// The Worker of a deployment that serves pair pages on request (openspec pairs-site): the
// site's own Worker, and every pair's page, open data record, embed, oEmbed description and
// card from D1 (worker/pairs.mjs, worker/shares.mjs), and every listing (worker/listings.mjs):
// the build makes none of them. Only a pull request's preview uses it (wrangler.preview.jsonc and the
// PAIRS binding it is given); production's Worker is worker/index.mjs alone until the cutover.
// The validators are those the build wrote from the bundle's schemas (scripts/bundle-code.mjs).
import * as validators from "../.bundle-code/validators.mjs";
import { handle } from "./index.mjs";
import { listingOf, listingPage } from "./listings.mjs";
import { SHELL_PATH, pairAddress, pairPage, pairRecord, recordAddress } from "./pairs.mjs";
import { EMBED_SHELL_PATH, shareAnswer, shareOf } from "./shares.mjs";

const { validatePairDataFile, validatePairInterventionPage, validatePairPage } = validators;

export async function handleWithPairs(request, env, cache = globalThis.caches?.default ?? null) {
  const url = new URL(request.url);
  // The frames are the Worker's to fill, never pages of their own.
  if ([SHELL_PATH, EMBED_SHELL_PATH].some((frame) => url.pathname === frame || url.pathname === `${frame}/`)) {
    return handle(new Request(new URL("/__no-such-page__", url), request), env);
  }
  const answer = await handle(request, env);
  if (answer.status !== 404) return answer;
  if (pairAddress(url.pathname)) return (await pairPage(request, env, validatePairPage, cache, validatePairInterventionPage)) ?? answer;
  // A pair's open data record the build did not write (task 1.3).
  if (recordAddress(url.pathname)) return (await pairRecord(request, env, validatePairDataFile, cache)) ?? answer;
  // A pair's embed, oEmbed description and card address: every one is made here.
  if (shareOf(url.pathname)) return (await shareAnswer(request, env, validatePairPage, cache)) ?? answer;
  // An intervention's, clinical category's or topic's page: every one is made here.
  if (listingOf(url.pathname)) return (await listingPage(request, env, validators, cache)) ?? answer;
  return answer;
}

export default { fetch: (request, env) => handleWithPairs(request, env) };
