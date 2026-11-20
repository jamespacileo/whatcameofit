// The Worker of a deployment that serves pair pages on request (openspec pairs-site): the
// site's own Worker, and every pair's page, open data record, embed, oEmbed description and
// card from D1 (worker/pairs.mjs, worker/shares.mjs), and every listing (worker/listings.mjs):
// the build makes none of them. Only a pull request's preview uses it (wrangler.preview.jsonc and the
// PAIRS binding it is given); production's Worker is worker/index.mjs alone until the cutover.
// The validators are those the build wrote from the bundle's schemas (scripts/bundle-code.mjs).
import * as validators from "../.bundle-code/validators.mjs";
import { handle } from "./index.mjs";
import { listingOf, listingPage } from "./listings.mjs";
import { SHELL_PATH, builtFor, pairAddress, pairPage, pairRecord, recordAddress } from "./pairs.mjs";
import { EMBED_SHELL_PATH, shareAnswer, shareOf } from "./shares.mjs";

const { validatePairDataFile, validatePairInterventionPage, validatePairPage } = validators;

// The saved forms of a pair's page and embed address that the static files answered while they
// were built (Cloudflare's html_handling: "/<pair>/", "/<pair>/index.html", and the embed's):
// each leads to the bare address, keeping its query. Nothing is read to answer it.
const PAIR = "[a-z0-9]+(?:-[a-z0-9]+)*--[a-z0-9]+(?:-[a-z0-9]+)*";
const ALIAS = new RegExp(`^/((?:embed/)?${PAIR})(?:/|/index\\.html|\\.html)$`);

// The address space the Worker reads D1 for, and nothing else (openspec pairs-site task 4.6c):
// a pair's page, record, embed, oEmbed description and card addresses, and a listing's page,
// each matched by its own pattern; any other path is the asset binding's alone and never reads
// D1. A path longer than any address the lab writes is refused before it is matched.
const LONGEST_ADDRESS = 300;
// A well-formed address the version holds nothing for: its not-found answer is kept five
// minutes under the very key its page would be kept under (the handler's), so one cache lookup
// answers either, and asking again reads nothing. Short, so an address a new bundle adds is
// answered within minutes of its deployment. Only a confirmed miss in D1 is kept, and only
// from a GET, whose answer has the not-found page's body.
const MISSING_SECONDS = 300;

/** The handler a path's family is answered by, or null when the path is no on-request address. */
function onRequest(pathname) {
  if (pathname.length > LONGEST_ADDRESS) return null;
  if (pairAddress(pathname)) return (request, env, cache) => pairPage(request, env, validatePairPage, cache, validatePairInterventionPage);
  if (recordAddress(pathname)) return (request, env, cache) => pairRecord(request, env, validatePairDataFile, cache);
  if (shareOf(pathname)) return (request, env, cache) => shareAnswer(request, env, validatePairPage, cache);
  if (listingOf(pathname)) return (request, env, cache) => listingPage(request, env, validators, cache);
  return null;
}

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
  // Every pair's page, record, embed, oEmbed description and card address, and every listing,
  // is made here; any other path that the assets do not hold answers their not-found page.
  const make = onRequest(url.pathname);
  if (!make) return answer;
  const made = await make(request, env, cache);
  if (made instanceof Response) return made;
  // No frame or store, or a dependency of the page that failed: the asset's answer, kept nowhere.
  if (!made?.notHeld) return answer;
  // The query string is never part of a key: an address is one page however it is asked for.
  const built = await builtFor(request, env);
  const headers = new Headers(answer.headers);
  headers.set("Cache-Control", `public, max-age=${MISSING_SECONDS}`);
  if (built?.robots) headers.set("X-Robots-Tag", built.robots);
  const notFound = new Response(answer.body, { status: 404, headers });
  if (cache && request.method === "GET") await cache.put(made.notHeld, notFound.clone());
  return notFound;
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
