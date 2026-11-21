// The Worker of a deployment that serves pair pages on request (openspec pairs-site): the
// site's own Worker, and every pair's page, open data record, embed, oEmbed description and
// card from D1 (worker/pairs.mjs, worker/shares.mjs), and every listing (worker/listings.mjs):
// the build makes none of them. Only a pull request's preview uses it (wrangler.preview.jsonc and the
// PAIRS binding it is given); production's Worker is worker/index.mjs alone until the cutover.
// The validators are those the build wrote from the bundle's schemas (scripts/bundle-code.mjs).
import * as validators from "../.bundle-code/validators.mjs";
import { handle } from "./index.mjs";
import { listingOf, listingPage } from "./listings.mjs";
import { SHELL_PATH, SITE_HEADERS, builtFor, madeHeaders, pairAddress, pairPage, pairRecord, recordAddress } from "./pairs.mjs";
import { EMBED_SHELL_PATH, shareAnswer, shareOf } from "./shares.mjs";
import { LEGACY_LOOKUP, PACKED_LOOKUP } from "../src/lib/lookup-assets.mjs";

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

/**
 * The site's not-found page for an answer that has none: in a deployment with pairs the files
 * give none of their own (not_found_handling "none", so an address no file has reaches this
 * Worker). It keeps the answer's headers; an answer with no caching policy takes the page's,
 * which asks again before reusing it, so a 404 is never kept after the page appears.
 */
async function notFoundPage(request, env, answer) {
  if (answer.headers.get("Content-Type")?.startsWith("text/html")) return answer;
  const page = await env.ASSETS.fetch(new Request(new URL("/404", request.url)));
  if (!page.ok) return answer;
  await answer.body?.cancel();
  const headers = new Headers(answer.headers);
  headers.set("Content-Type", page.headers.get("Content-Type") ?? "text/html; charset=utf-8");
  if (!headers.has("Cache-Control")) headers.set("Cache-Control", page.headers.get("Cache-Control") ?? "public, max-age=0, must-revalidate");
  return new Response(page.body, { status: 404, headers });
}

// The methods an address the Worker makes answers. A file answers others with 405 itself; an
// address no file has reaches the Worker whatever the method, so it says the same here.
const READ = new Set(["GET", "HEAD"]);

/**
 * How many on-request answers one address may ask for, per Cloudflare location (openspec
 * pairs-site task 4.6g): the ON_REQUEST_LIMIT binding, which pairsConfig gives every deployment
 * with pairs. Past it, 429 with Retry-After, never 403 or 404: Google's crawlers read 429 as the
 * server asking them to slow down, while a 403 or 404 would drop the page from the index
 * (https://developers.google.com/crawling/docs/crawlers-fetchers/reduce-crawl-rate). The limit
 * is far above what a search engine's crawler asks of one location from one address, and is
 * counted by the asker's address, the only key a crawler or a scraper brings: the binding's
 * counts are approximate and per location
 * (https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).
 */
const RETRY_SECONDS = 60;

// A fault of the limiter never takes pages down: with no binding, or a limit() call that throws,
// the request is answered and the fault is logged. The deploy checks refuse a configuration with
// pairs that lacks the binding (limitProblems in scripts/pairs-preview.mjs), so a deployment
// never goes without it.
// Counted by the asker's address on each hostname: pull request previews share one namespace,
// and a reviewer's requests to one preview never count against another.
async function overLimit(request, env, url) {
  if (!env.ON_REQUEST_LIMIT) {
    console.warn("ON_REQUEST_LIMIT is not bound: answering without a rate limit");
    return false;
  }
  const asker = request.headers.get("CF-Connecting-IP") ?? "unknown";
  try {
    const { success } = await env.ON_REQUEST_LIMIT.limit({ key: `${url.hostname} ${asker}` });
    return !success;
  } catch (error) {
    console.warn(`ON_REQUEST_LIMIT failed, answering without a rate limit: ${error?.message ?? error}`);
    return false;
  }
}

/**
 * The cache pages made here are kept in: the Cache API (caches.default), kept for launch. Its
 * contents stay in the data centre that kept them and outlast a deployment
 * (https://developers.cloudflare.com/workers/runtime-apis/cache/), and the keys hold the bundle
 * version and the frame's digest, so a new deployment never answers an older page. Not Workers
 * Cache: it bills requests that are otherwise free, static asset requests among them, and keys
 * by the Worker's version by default, so it would start empty after each deployment
 * (https://developers.cloudflare.com/workers/cache/).
 */
export async function handleWithPairs(request, env, cache = globalThis.caches?.default ?? null) {
  const url = new URL(request.url);
  // The frames are the Worker's to fill, never pages of their own.
  if ([SHELL_PATH, EMBED_SHELL_PATH].some((frame) => url.pathname === frame || url.pathname === `${frame}/`)) {
    return notFoundPage(request, env, await handle(new Request(new URL("/__no-such-page__", url), request), env));
  }
  const answer = await handle(request, env);
  if (answer.status !== 404) return answer;
  if (!READ.has(request.method)) {
    await answer.body?.cancel();
    return new Response(null, { status: 405, headers: { Allow: "GET, HEAD", "Cache-Control": "no-store" } });
  }
  if (url.pathname === LEGACY_LOOKUP) {
    const packed = await env.ASSETS.fetch(new Request(new URL(PACKED_LOOKUP, url), { method: request.method }));
    if (packed.ok) {
      await answer.body?.cancel();
      const headers = new Headers(packed.headers);
      headers.set("Content-Type", "application/json; charset=utf-8");
      for (const name of ["Content-Length", "Content-Encoding", "ETag"]) headers.delete(name);
      const body = packed.body?.pipeThrough(new DecompressionStream("gzip")) ?? null;
      return new Response(body, { headers });
    }
    await packed.body?.cancel();
  }
  const alias = ALIAS.exec(url.pathname)?.[1];
  if (alias) {
    await answer.body?.cancel();
    return new Response(null, { status: 301, headers: { Location: new URL(`/${alias}${url.search}`, url).href, "Cache-Control": "public, max-age=86400" } });
  }
  // Every pair's page, record, embed, oEmbed description and card address, and every listing,
  // is made here; any other path that the assets do not hold answers their not-found page.
  const make = onRequest(url.pathname);
  if (!make) return notFoundPage(request, env, answer);
  if (await overLimit(request, env, url)) {
    await answer.body?.cancel();
    // The site's headers and the deployment's robots mark, as on the pages themselves; the frame
    // is a file, so nothing is read from D1.
    const built = await builtFor(request, env);
    const headers = built ? madeHeaders(built, "text/plain; charset=utf-8", "no-store") : new Headers({ ...SITE_HEADERS, "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" });
    headers.set("Retry-After", String(RETRY_SECONDS));
    return new Response("Too many requests. Please slow down and try again shortly.", { status: 429, headers });
  }
  const made = await make(request, env, cache);
  if (made instanceof Response) return made;
  // No frame or store, or a dependency of the page that failed: the asset's answer, kept nowhere.
  if (!made?.notHeld) return notFoundPage(request, env, answer);
  // The query string is never part of a key: an address is one page however it is asked for.
  const built = await builtFor(request, env);
  const page = await notFoundPage(request, env, answer);
  const headers = new Headers(page.headers);
  headers.set("Cache-Control", `public, max-age=${MISSING_SECONDS}`);
  if (built?.robots) headers.set("X-Robots-Tag", built.robots);
  const notFound = new Response(page.body, { status: 404, headers });
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
