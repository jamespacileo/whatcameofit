// Runs after every build. Says what each address the site once served answers now.
//
// Until 2026-11-20 the site tracked claims, each with a page at /<slug> and files of its own
// (an embed, an oEmbed description, three cards, an open data record, a feed). The operator
// removed claims that day; data/retired-addresses.json is the frozen list of those addresses.
// A claim that exactly one published pair came from leads to that pair with a permanent
// redirect (approved by the operator on 2026-11-20, openspec pairs-site task 3.4). A claim the
// operator archived answers 410 Gone, as it always did. The Worker answers both from
// dist/gone.json (worker/index.mjs, worker/gone.mjs).
//
// Every other claim keeps its page and its files at their own addresses, as production last
// built them (the operator, 2026-11-21): KEPT_CLAIMS_DIR names the folder they were frozen
// into (scripts/kept-claims.mjs, make kept-claims), and they are placed in the build, so the
// host serves them before the Worker runs. Without that folder (a test's or a local build) such
// a claim answers 410, and deploy.mjs refuses to publish staging or production.
//
// A topic renamed while claims were tracked keeps its redirect, in dist/_redirects, which
// Cloudflare serves before the files.
import fs from "node:fs";
import path from "node:path";
import { movedAddresses, readBundle } from "../src/lib/bundle.ts";
import { placeKept, readKept } from "./kept-claims.mjs";

const DIST = path.resolve(process.env.DIST_DIR ?? "dist");
const retired = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "../data/retired-addresses.json"), "utf8"));
if (!process.env.PAIRS_BUNDLE) throw new Error("No bundle: set PAIRS_BUNDLE to the folder the site was built from.");
const bundle = readBundle(path.resolve(process.env.PAIRS_BUNDLE));
const pairs = bundle.pages.PairPage ?? {};

/** What old addresses answer, for the Worker: `to` a pair's address (301), `to` a kept claim
 * (`kept`, 301 to its own files), or gone (410), with the day an archived claim was taken down
 * where the operator archived it. A kept claim's own address is in `keep`, not the list. */
function goneEntries(retiredAddresses, pairPages, dataFiles, keptClaims = new Set()) {
  // Each claim slug with the one pair that came from it. A claim behind several pairs leads
  // to none of them by rule (`movedAddresses`), and so answers 410.
  const leads = movedAddresses(Object.values(pairPages));
  const archived = new Map(retiredAddresses.archived.map(({ slug, on }) => [slug, on]));
  const merged = new Map(retiredAddresses.moved.map(({ slug, to }) => [slug, to]));
  const entries = [];
  const keep = new Set();
  for (const slug of new Set([...retiredAddresses.pages, ...archived.keys(), ...merged.keys()])) {
    // An address that is a pair's own is a page of the site and answers as one.
    if (Object.hasOwn(pairPages, slug)) continue;
    // A claim the operator archived stays gone, whatever came of its records.
    if (archived.has(slug)) {
      entries.push({ slug, on: archived.get(slug) });
      continue;
    }
    // A claim merged into another, or renamed, goes where the claim it became goes.
    let claim = slug;
    for (let hops = 0; merged.has(claim) && hops < 10; hops += 1) claim = merged.get(claim);
    const to = Object.hasOwn(pairPages, claim) ? claim : leads.get(claim);
    if (archived.has(claim)) {
      entries.push({ slug, gone: true });
      continue;
    }
    if (!to) {
      // No pair came from it: its own page, where it was kept, or else gone.
      if (!keptClaims.has(claim)) entries.push({ slug, gone: true });
      else if (claim === slug) keep.add(slug);
      else entries.push({ slug, to: claim, kept: true });
      continue;
    }
    // The pair's record is where the claim's record leads, so it must exist to be led to.
    if (!Object.hasOwn(dataFiles, to)) {
      throw new Error(`The address ${slug} leads to the pair ${to}, which has no data file in the bundle.`);
    }
    entries.push({ slug, to });
  }
  return { entries: entries.sort((a, b) => (a.slug < b.slug ? -1 : 1)), keep: [...keep].sort() };
}

const lines = retired.topics.map(({ slug, successor }) => `/topic/${slug} /topic/${successor} 301`);
const file = path.join(DIST, "_redirects");
if (lines.length > 0) fs.writeFileSync(file, `${lines.join("\n")}\n`);
else fs.rmSync(file, { force: true });

const keptFolder = process.env.KEPT_CLAIMS_DIR ? path.resolve(process.env.KEPT_CLAIMS_DIR) : null;
const kept = keptFolder ? readKept(keptFolder) : null;
const { entries: gone, keep } = goneEntries(retired, pairs, bundle.pages.PairDataFile ?? {}, new Set(Object.keys(kept?.claims ?? {})));
fs.writeFileSync(path.join(DIST, "gone.json"), `${JSON.stringify(gone)}\n`);
// Which claims kept their pages, for the build check and the staging smoke check.
fs.writeFileSync(path.join(DIST, "kept-claims.json"), `${JSON.stringify(keep)}\n`);
const placed = keptFolder ? placeKept({ folder: keptFolder, dist: DIST, slugs: keep }) : 0;

const led = gone.filter((entry) => entry.to && !entry.kept).length;
const archivedCount = gone.filter((entry) => entry.on).length;
const unkept = gone.length - gone.filter((entry) => entry.to).length - archivedCount;
console.log(
  `Old addresses: ${led} lead to a pair, ${keep.length} claims keep their pages (${placed.toLocaleString("en-GB")} files), ` +
    `${archivedCount} archived stay gone, ${unkept} more answer gone; ${lines.length} renamed topic ${lines.length === 1 ? "address" : "addresses"}.`,
);
