// A pair page made on request (openspec pairs-site, decision 3 as revised): a pair the build
// did not make ahead is read from D1, from the one bundle version the build read, checked with
// the compiled validator, and written with the same renderer as a built page into the frame
// the build left at /pair-shell. The answer is kept a day under a key that holds the version,
// so a new deployment needs no purge.
import { pairView } from "../src/lib/pair-view.ts";
import { escape, pairDescription, renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { narrowerPairs } from "../src/lib/pair-view.ts";
import { pairRecordText } from "../src/lib/pair-record.ts";
import { SITE } from "../site.config.mjs";

/** A pair's address: two slugs joined by a double hyphen. */
const ADDRESS = /^\/([a-z0-9]+(?:-[a-z0-9]+)*--[a-z0-9]+(?:-[a-z0-9]+)*)$/;
const VERSION = /data-pair-version="([0-9a-f]{16})"/;
const MESH_EDITION = /data-mesh-edition="([^"]*)"/;
// The site's address as the build wrote it into the frame's canonical link: the Worker's own
// SITE_URL is not the build's, so every address a page made here names comes from the frame.
const SITE_ORIGIN = /<link rel="canonical" href="(https?:\/\/[^/"]+)\/__PAIR_ADDRESS__"/;

/** The headers public/_headers sends with every file of the site ("/*"). A response made here
 * is no file, so the Worker sets them itself; tests/pair-on-request.build-test.mjs holds the
 * two lists the same. */
export const SITE_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Strict-Transport-Security": "max-age=31536000",
};
export const SHELL_PATH = "/pair-shell";
const DAY_SECONDS = 86400;
// Said when a pair's file does not pass its check: nothing of the file is shown.
export const UNREADABLE = "This page could not be shown. Its record did not pass the site's checks.";

/** The address a path names, or null when it is no pair's. */
export function pairAddress(pathname) {
  return ADDRESS.exec(pathname)?.[1] ?? null;
}

const RECORD = /^\/data\/pairs\/([a-z0-9]+(?:-[a-z0-9]+)*--[a-z0-9]+(?:-[a-z0-9]+)*)\.json$/;

/** The address of the pair whose open data record a path names, or null. */
export function recordAddress(pathname) {
  return RECORD.exec(pathname)?.[1] ?? null;
}

/**
 * The frame the build left, with what a page made in it needs, or null on a deployment without:
 * - `version`, the bundle version the build read, the only one the Worker reads pages of;
 * - `build`, a digest of the frame, which a cached page is keyed by: a redeploy with the same
 *   bundle but another frame (a renderer, style or asset change) never answers an older page;
 * - `robots`, the frame's own X-Robots-Tag: a preview's `_headers` mark every asset noindex, and
 *   a page made here carries the same mark as the files beside it;
 * - `meshEdition`, the MeSH vocabulary's year as the build states it.
 */
// The frame as read for a request, kept for the rest of that request: the address check, the
// cache of not-found answers and the page's own step all read it, and the asset is fetched once.
const framesRead = new WeakMap();

/** `builtVersion` for one request, read once however many steps ask. */
export function builtFor(request, env) {
  if (!framesRead.has(request)) framesRead.set(request, builtVersion(env, new URL(request.url)));
  return framesRead.get(request);
}

export async function builtVersion(env, url) {
  const frame = await env.ASSETS.fetch(new Request(new URL(SHELL_PATH, url)));
  if (!frame.ok) return null;
  const shell = await frame.text();
  const version = VERSION.exec(shell)?.[1];
  if (!version) return null;
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(shell)));
  const build = [...digest.slice(0, 8)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  const meshEdition = (MESH_EDITION.exec(shell)?.[1] ?? "").replaceAll("&amp;", "&").replaceAll("&#39;", "'").replaceAll("&quot;", '"').replaceAll("&lt;", "<").replaceAll("&gt;", ">");
  const siteUrl = SITE_ORIGIN.exec(shell)?.[1];
  if (!siteUrl) return null;
  // The frame as a page's content sees it: the same whatever bundle version it records, so a page
  // whose file is unchanged keeps its tag from one bundle to the next.
  const frameTag = await digestOf(shell.replace(VERSION, 'data-pair-version=""'));
  return { shell, version, build, frameTag, siteUrl, robots: frame.headers.get("X-Robots-Tag"), meshEdition };
}

/** The first 12 bytes of a text's SHA-256, in hex. */
async function digestOf(text) {
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)));
  return [...digest.slice(0, 12)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

/**
 * A page's entity tag, from what it is made of (openspec pairs-site task 4.6e): the files it reads
 * from D1, as read, and the sets it reads with them, and the frame as a page sees it. A page
 * whose file is unchanged keeps its tag across bundle versions, so a crawler asking again is told
 * it is unchanged (304) rather than sent it whole after every load.
 *
 * Weak (`W/`): two pages with one tag are the same page but not the same bytes, since the frame
 * carries the bundle version it was built from. RFC 9110 8.8.1: a weak validator "might not
 * change for every change to the representation data"; If-None-Match compares tags weakly, so a
 * weak tag answers a conditional GET in full (8.8.3.2, 13.1.2).
 * https://www.rfc-editor.org/rfc/rfc9110#section-8.8
 */
export async function contentTag(built, ...parts) {
  const text = [built.frameTag, ...parts.map((part) => (part === ABSENT ? "absent" : typeof part === "string" ? part : JSON.stringify(part)))].join("\u0000");
  return `W/"${await digestOf(text)}"`;
}

/** Whether the asker holds this tag already (If-None-Match, compared weakly: RFC 9110 13.1.2). */
export function unchanged(request, tag) {
  const asked = request.headers.get("If-None-Match");
  if (!asked || !tag) return false;
  if (asked.trim() === "*") return true;
  const opaque = (one) => one.trim().replace(/^W\//, "");
  return asked.split(",").some((one) => opaque(one) === opaque(tag));
}

/** The answer for an asker who holds the page: its tag and caching, no body (RFC 9110 15.4.5). */
export function notModified(built, tag, cacheControl) {
  const headers = new Headers({ ...SITE_HEADERS, ETag: tag, "Cache-Control": cacheControl });
  if (built.robots) headers.set("X-Robots-Tag", built.robots);
  return new Response(null, { status: 304, headers });
}

/** A kept page, or 304 for an asker who holds it, read from what the cache kept: no D1 read. */
export function fromCache(request, built, kept) {
  const tag = kept.headers.get("ETag");
  if (kept.status === 200 && tag && unchanged(request, tag)) return notModified(built, tag, kept.headers.get("Cache-Control"));
  return kept;
}

/** The headers of a page or file made here: the site's own, its type and caching, and the
 * frame's robots mark. */
export function madeHeaders(built, type, cacheControl) {
  const headers = new Headers({ ...SITE_HEADERS, "Content-Type": type, "Cache-Control": cacheControl });
  if (built.robots) headers.set("X-Robots-Tag", built.robots);
  return headers;
}

/** What a page's step answers when D1 confirms the version holds no such file: the key its page
 * would be kept under, where the Worker's entry keeps the not-found answer instead. */
export const notHeld = (key) => ({ notHeld: key });

/** What `bundleFile` gives for a file the version does not hold: distinct from any parsed body,
 * JSON `null` included, so every body found is checked. */
export const ABSENT = Symbol("absent");

export const FILE_SQL = "SELECT body FROM pair_page WHERE version = ?1 AND model = ?2 AND key = ?3 ORDER BY part";

/** A file's parts as read, joined and parsed: the parsed file, undefined when it does not parse,
 * or ABSENT when there are none. */
export function parsedFile(results) {
  if (!results.length) return ABSENT;
  try {
    return JSON.parse(results.map((row) => row.body).join(""));
  } catch {
    return undefined;
  }
}

/** One file of the bundle as the loader kept it, its parts joined. */
export async function bundleFile(env, version, model, key) {
  const { results } = await env.PAIRS.prepare(FILE_SQL).bind(version, model, key).all();
  return parsedFile(results);
}

/** The frame with a page's parts in their places. Each part is put in by a function, so it goes
 * in as written: a replacement string would read "$$" or "$&" in it as patterns. */
// The frame's oEmbed link (PairShell.astro): kept for a pair's page, removed for a listing's.
const OEMBED_LINK = /<link[^>]*type="application\/json\+oembed"[^>]*>/;

export function fill(shell, { title, description, address, band, sheet, oembed = false }) {
  return (oembed ? shell : shell.replace(OEMBED_LINK, ""))
    .replaceAll("__PAIR_TITLE__", () => escape(title))
    .replaceAll("__PAIR_DESCRIPTION__", () => escape(description))
    .replaceAll("__PAIR_ADDRESS__", () => escape(address))
    .replace("<!--pair-band-->", () => band)
    .replace("<!--pair-sheet-->", () => sheet);
}

/** The error page for a file that failed its check: nothing of the file is shown. */
export function unreadablePage(built, address) {
  const page = fill(built.shell, {
    title: "Page not shown",
    description: UNREADABLE,
    address,
    band: `<section class="band record"><div class="wrap"><h1 class="title">Page not shown</h1><p class="lede" data-pair-unreadable>${escape(UNREADABLE)}</p></div></section>`,
    sheet: "",
  });
  return new Response(page, { status: 500, headers: madeHeaders(built, "text/html; charset=utf-8", "no-store") });
}

/**
 * The page of a pair the build did not make, or null when this deployment has no frame, no
 * store, or no such pair in the version it was built from.
 * @param {Request} request
 * @param {{ ASSETS: { fetch: (request: Request) => Promise<Response> }, PAIRS?: any }} env
 * @param {(file: unknown) => boolean} validate the compiled validator of `PairPage`
 * @param {{ match: Function, put: Function } | null} cache
 * @param {(file: unknown) => boolean} validateIntervention the compiled validator of `PairInterventionPage`
 */
export async function pairPage(request, env, validate, cache, validateIntervention) {
  const url = new URL(request.url);
  const address = pairAddress(url.pathname);
  if (!address || !env.PAIRS || typeof validate !== "function") return null;
  const built = await builtFor(request, env);
  if (!built) return null;
  const { shell, version } = built;

  const key = new Request(new URL(`/__pair/${version}/${built.build}/${address}`, url));
  const kept = cache ? await cache.match(key) : undefined;
  if (kept) return fromCache(request, built, kept);

  const file = await bundleFile(env, version, "PairPage", address);
  if (file === ABSENT) return notHeld(key);
  let intervention = ABSENT;
  let published = new Set();
  const valid = validate(file);
  if (valid) {
    // The same treatment's narrower pairs: its intervention page file (by the table's key) and
    // the addresses of its pairs in this version (the pair_by_intervention index), in one round
    // trip, as the built page reads the same file and the bundle's own pair pages. A version with
    // no such file lists none; a file that fails its check stops the page.
    const [listing, pairs] = await env.PAIRS.batch([
      env.PAIRS.prepare(FILE_SQL).bind(version, "PairInterventionPage", file.row.intervention.slug),
      env.PAIRS.prepare("SELECT address FROM pair WHERE version = ?1 AND intervention_id = ?2").bind(version, file.row.intervention.id),
    ]);
    intervention = parsedFile(listing.results);
    published = new Set(pairs.results.map((row) => row.address));
  }
  if (!valid || (intervention !== ABSENT && !(typeof validateIntervention === "function" && validateIntervention(intervention)))) {
    return unreadablePage(built, address);
  }
  // The narrower pairs the page links: of the intervention's file and its published pairs, only
  // these reach the page, so only these go into its tag. A pair added or removed elsewhere, of
  // this treatment or another, leaves the tag as it was.
  const narrower = narrowerPairs(file, intervention === ABSENT ? null : intervention, published);
  // Answered before the page is written: an asker who holds it is told so.
  const tag = await contentTag(built, "pair", file, narrower);
  const caching = `public, max-age=${DAY_SECONDS}`;
  if (unchanged(request, tag)) return notModified(built, tag, caching);

  const view = pairView(file);
  const page = fill(shell, {
    title: view.title,
    description: pairDescription(view),
    address,
    band: renderPairBand(view),
    oembed: true,
    sheet: renderPairSheet(view, narrower),
  });
  const headers = madeHeaders(built, "text/html; charset=utf-8", caching);
  headers.set("ETag", tag);
  const answer = new Response(page, { headers });
  if (cache) await cache.put(key, answer.clone());
  return answer;
}

/**
 * The open data record of a pair the build did not write (task 1.3: one file a pair would pass
 * the deployment's file limit), from the `PairDataFile` of the version the build read, checked
 * with its compiled validator and written as the build writes a record. Null when this
 * deployment has no frame or store, or the version holds no such pair.
 * @param {Request} request
 * @param {{ ASSETS: { fetch: (request: Request) => Promise<Response> }, PAIRS?: any }} env
 * @param {(file: unknown) => boolean} validate the compiled validator of `PairDataFile`
 * @param {{ match: Function, put: Function } | null} cache
 */
export async function pairRecord(request, env, validate, cache) {
  const url = new URL(request.url);
  const address = recordAddress(url.pathname);
  if (!address || !env.PAIRS || typeof validate !== "function") return null;
  const built = await builtFor(request, env);
  if (!built) return null;

  const key = new Request(new URL(`/__pair-record/${built.version}/${built.build}/${address}`, url));
  const kept = cache ? await cache.match(key) : undefined;
  if (kept) return fromCache(request, built, kept);

  const file = await bundleFile(env, built.version, "PairDataFile", address);
  if (file === ABSENT) return notHeld(key);
  if (!validate(file)) {
    return new Response(JSON.stringify({ error: UNREADABLE }), { status: 500, headers: madeHeaders(built, "application/json; charset=utf-8", "no-store") });
  }
  const tag = await contentTag(built, "record", file);
  const caching = `public, max-age=${DAY_SECONDS}`;
  if (unchanged(request, tag)) return notModified(built, tag, caching);
  const headers = madeHeaders(built, "application/json; charset=utf-8", caching);
  headers.set("ETag", tag);
  const answer = new Response(pairRecordText(file, SITE.name, built.siteUrl), { headers });
  if (cache) await cache.put(key, answer.clone());
  return answer;
}
