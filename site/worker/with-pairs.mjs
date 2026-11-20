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

// The saved forms of a pair's page and embed address that the static files answered while they
// were built (Cloudflare's html_handling: "/<pair>/", "/<pair>/index.html", and the embed's):
// each leads to the bare address, keeping its query. Nothing is read to answer it.
const PAIR = "[a-z0-9]+(?:-[a-z0-9]+)*--[a-z0-9]+(?:-[a-z0-9]+)*";
const ALIAS = new RegExp(`^/((?:embed/)?${PAIR})(?:/|/index\\.html|\\.html)$`);

export async function handleWithPairs(request, env, cache = globalThis.caches?.default ?? null) {
  const url = new URL(request.url);
  // The frames are the Worker's to fill, never pages of their own.
  if ([SHELL_PATH, EMBED_SHELL_PATH].some((frame) => url.pathname === frame || url.pathname === `${frame}/`)) {
    return handle(new Request(new URL("/__no-such-page__", url), request), env);
  }
  const answer = await handle(request, env);
  if (answer.status !== 404) return answer;
  const alias = ALIAS.exec(url.pathname)?.[1];
  if (alias) {
    await answer.body?.cancel();
    return new Response(null, { status: 301, headers: { Location: new URL(`/${alias}${url.search}`, url).href, "Cache-Control": "public, max-age=86400" } });
  }
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
