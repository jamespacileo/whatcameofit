// A page that lists pairs, made on request (openspec pairs-site, design decision 2 as chosen on
// 2026-11-20): an intervention's, a clinical category's or a topic's page, which the build no
// longer makes, is read from D1 as the lab's page file for it, one read by the table's key (version, model,
// key), at the bundle version the build recorded, checked with its compiled validator, and
// written with the same renderer as a built listing into the frame at /pair-shell. Never the row
// tables: a topic joined from them read about 6,000 rows a view on the rehearsal, a page file
// 6 to 170. An address that cannot be a listing is refused by its pattern before any read.
import { categoryListing, interventionListing, namedPairs, topicListing } from "../src/lib/listing-view.ts";
import { renderListingBand, renderListingSheet } from "../src/lib/listing-render.ts";
import { ABSENT, FILE_SQL, builtFor, contentTag, fill, fromCache, madeHeaders, notHeld, notModified, parsedFile, unchanged, unreadablePage } from "./pairs.mjs";

const DAY_SECONDS = 86400;
const SLUG = "[a-z0-9]+(?:-[a-z0-9]+)*";

/** The listing families: the path's pattern, the page model whose file holds the listing, and
 * how the view is read from it. */
const LISTINGS = [
  { pattern: new RegExp(`^/intervention/(${SLUG})$`), model: "PairInterventionPage", view: interventionListing, check: "validatePairInterventionPage" },
  { pattern: /^\/clinical\/(D\d{6,9})$/, model: "PairClinicalCategoryPage", view: categoryListing, check: "validatePairClinicalCategoryPage" },
  { pattern: new RegExp(`^/topic/(${SLUG})$`), model: "PairTopicPage", view: topicListing, check: "validatePairTopicPage" },
];

/** Which listing a path is, or null. */
export function listingOf(pathname) {
  for (const listing of LISTINGS) {
    const key = listing.pattern.exec(pathname)?.[1];
    if (key) return { ...listing, key };
  }
  return null;
}

/**
 * The listing page the build did not make, or null when the deployment has no frame or store,
 * the path is no listing's, or the version holds no such file.
 * @param {Record<string, (file: unknown) => boolean>} validators the compiled validators
 */
export async function listingPage(request, env, validators, cache) {
  const url = new URL(request.url);
  const listing = listingOf(url.pathname);
  if (!listing || !env.PAIRS) return null;
  const validate = validators[listing.check];
  if (typeof validate !== "function") return null;
  const built = await builtFor(request, env);
  if (!built) return null;
  const { shell, version } = built;

  const key = new Request(new URL(`/__listing/${version}/${built.build}${url.pathname}`, url));
  const kept = cache ? await cache.match(key) : undefined;
  if (kept) return fromCache(request, built, kept);

  const { results: parts } = await env.PAIRS.prepare(FILE_SQL).bind(version, listing.model, listing.key).all();
  const file = parsedFile(parts);
  if (file === ABSENT) return notHeld(key);
  if (!validate(file)) return unreadablePage(built, url.pathname.slice(1));

  // Which of the pairs the file names this version publishes (the pair table's address index),
  // and for a category which of its broader and narrower categories have a page (the page
  // table's key), in one round trip: a listing links only pages that answer.
  const reads = [
    env.PAIRS.prepare("SELECT address FROM pair WHERE version = ?1 AND address IN (SELECT value FROM json_each(?2))").bind(version, JSON.stringify(namedPairs(file))),
  ];
  if (listing.model === "PairClinicalCategoryPage") {
    const related = [...file.broader, ...file.narrower].map((one) => one.descriptor_id);
    reads.push(
      env.PAIRS.prepare("SELECT key FROM pair_page WHERE version = ?1 AND model = 'PairClinicalCategoryPage' AND part = 0 AND key IN (SELECT value FROM json_each(?2))").bind(version, JSON.stringify(related)),
    );
  }
  const [pairs, categories] = await env.PAIRS.batch(reads);
  const published = new Set(pairs.results.map((row) => row.address));
  const known = new Set((categories?.results ?? []).map((row) => row.key));
  // Both sets are this page's own: the pairs its file names that are published, and its own
  // broader and narrower categories that have a page. Nothing elsewhere in a bundle changes them.
  // Answered before the page is written: an asker who holds it is told so.
  const tag = await contentTag(built, "listing", built.pageFrame, file, [...published].sort(), [...known].sort(), built.meshEdition);
  const caching = `public, max-age=${DAY_SECONDS}`;
  if (unchanged(request, tag)) return notModified(built, tag, caching);
  const view = listing.view(file, published, known);
  const page = fill(shell, {
    title: view.title,
    description: view.description,
    address: view.path.slice(1),
    band: renderListingBand(view),
    sheet: renderListingSheet(view, built.meshEdition),
  });
  const headers = madeHeaders(built, "text/html; charset=utf-8", caching);
  headers.set("ETag", tag);
  const answer = new Response(page, { headers });
  if (cache) await cache.put(key, answer.clone());
  return answer;
}
