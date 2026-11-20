// A pair page made on request (openspec pairs-site, decision 3 as revised): a pair the build
// did not make ahead is read from D1, from the one bundle version the build read, checked with
// the compiled validator, and written with the same renderer as a built page into the frame
// the build left at /pair-shell. The answer is kept a day under a key that holds the version,
// so a new deployment needs no purge.
import { pairView } from "../src/lib/pair-view.ts";
import { escape, pairDescription, renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";

/** A pair's address: two slugs joined by a double hyphen. */
const ADDRESS = /^\/([a-z0-9]+(?:-[a-z0-9]+)*--[a-z0-9]+(?:-[a-z0-9]+)*)$/;
const VERSION = /data-pair-version="([0-9a-f]{16})"/;
export const SHELL_PATH = "/pair-shell";
const DAY_SECONDS = 86400;
// Said when a pair's file does not pass its check: nothing of the file is shown.
export const UNREADABLE = "This page could not be shown. Its record did not pass the site's checks.";

/** The address a path names, or null when it is no pair's. */
export function pairAddress(pathname) {
  return ADDRESS.exec(pathname)?.[1] ?? null;
}

function fill(shell, { title, description, address, band, sheet }) {
  return shell
    .replaceAll("__PAIR_TITLE__", escape(title))
    .replaceAll("__PAIR_DESCRIPTION__", escape(description))
    .replaceAll("__PAIR_ADDRESS__", escape(address))
    .replace("<!--pair-band-->", band)
    .replace("<!--pair-sheet-->", sheet);
}

/**
 * The page of a pair the build did not make, or null when this deployment has no frame, no
 * store, or no such pair in the version it was built from.
 * @param {Request} request
 * @param {{ ASSETS: { fetch: (request: Request) => Promise<Response> }, PAIRS?: any }} env
 * @param {(file: unknown) => boolean} validate the compiled validator of `PairPage`
 * @param {{ match: Function, put: Function } | null} cache
 */
export async function pairPage(request, env, validate, cache) {
  const url = new URL(request.url);
  const address = pairAddress(url.pathname);
  if (!address || !env.PAIRS || typeof validate !== "function") return null;
  const frame = await env.ASSETS.fetch(new Request(new URL(SHELL_PATH, url)));
  if (!frame.ok) return null;
  const shell = await frame.text();
  const version = VERSION.exec(shell)?.[1];
  if (!version) return null;

  const key = new Request(new URL(`/__pair/${version}/${address}`, url));
  const kept = cache ? await cache.match(key) : undefined;
  if (kept) return kept;

  const { results } = await env.PAIRS.prepare(
    "SELECT body FROM pair_page WHERE version = ?1 AND model = 'PairPage' AND key = ?2 ORDER BY part",
  )
    .bind(version, address)
    .all();
  if (!results.length) return null;

  let file;
  try {
    file = JSON.parse(results.map((row) => row.body).join(""));
  } catch {
    file = undefined;
  }
  if (!validate(file)) {
    const page = fill(shell, {
      title: "Page not shown",
      description: UNREADABLE,
      address,
      band: `<section class="band record"><div class="wrap"><h1 class="title">Page not shown</h1><p class="lede" data-pair-unreadable>${escape(UNREADABLE)}</p></div></section>`,
      sheet: "",
    });
    return new Response(page, { status: 500, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
  }

  const view = pairView(file);
  const page = fill(shell, {
    title: view.title,
    description: pairDescription(view),
    address,
    band: renderPairBand(view),
    sheet: renderPairSheet(view),
  });
  const answer = new Response(page, {
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": `public, max-age=${DAY_SECONDS}` },
  });
  if (cache) await cache.put(key, answer.clone());
  return answer;
}
