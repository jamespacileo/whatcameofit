// Runs after every build. Keeps every topic address that was ever published working.
//
// The export lists vertical slugs retired after launch, each with its successor; each
// becomes a permanent redirect in dist/_redirects, which Cloudflare serves before the
// files. `make deploy` records the topic slugs it published in data/published-topics.json.
// A slug recorded there that is neither a current topic nor retired would leave a
// published address broken, so the build fails and names it.
import fs from "node:fs";
import path from "node:path";
import { movedAddresses, readBundle } from "../src/lib/bundle.ts";

const DIST = path.resolve(process.env.DIST_DIR ?? "dist");

function exportPath() {
  if (process.env.EXPORT_FILE) return path.resolve(process.env.EXPORT_FILE);
  const live = path.resolve("data/export.json");
  return fs.existsSync(live) ? live : path.resolve("data/seed-export.json");
}

const data = JSON.parse(fs.readFileSync(exportPath(), "utf8"));
const current = new Set(data.verticals.map((vertical) => vertical.slug));
const retired = new Map((data.retired_verticals ?? []).map((entry) => [entry.slug, entry.successor]));

const recordFile = path.resolve(process.env.PUBLISHED_TOPICS_FILE ?? "data/published-topics.json");
const published = fs.existsSync(recordFile) ? JSON.parse(fs.readFileSync(recordFile, "utf8")) : [];
// The old transplant topic split across organs, so no one health area replaces it.
// Send its readers to the directory rather than choosing an unrelated organ.
const directoryRedirects = published.filter(slug => slug === "transplants" && !current.has(slug) && !retired.has(slug));
const lost = published.filter((slug) => !current.has(slug) && !retired.has(slug) && !directoryRedirects.includes(slug));
if (lost.length > 0) {
  console.error(
    `Redirect check failed: these published topics are neither current nor retired: ${lost.join(", ")}.` +
      " Record each with its successor in RETIRED_VERTICALS (pipeline/src/thenwhat/claims/verticals.py) and export again.",
  );
  process.exit(1);
}

const lines = [...retired].map(([slug, successor]) => `/topic/${slug} /topic/${successor} 301`);
lines.push(...directoryRedirects.map(slug => `/topic/${slug} /topics 301`));
const file = path.join(DIST, "_redirects");
if (lines.length > 0) fs.writeFileSync(file, `${lines.join("\n")}\n`);
else fs.rmSync(file, { force: true });
// Archived claims, for the Worker: each address answers 410 (worker/gone.mjs). Written
// even when empty, so a claim put back is served again after the next deploy. A claim
// merged into another, or renamed, is listed with the slug its address now leads to,
// and the Worker answers it with a permanent redirect.
const gone = [
  ...(data.archived ?? []).map(({ slug, on }) => ({ slug, on })),
  ...(data.moved ?? []).map(({ slug, to }) => ({ slug, to })),
];
// A build that reads a bundle (openspec pairs-site, task 4.3): each claim whose pair is
// published leads to the pair's address. An archived claim still answers 410, and a claim
// already moved keeps its own redirect. A claim whose slug is its pair's address, or that
// stands behind more than one pair, moves nowhere (`movedAddresses`).
if (process.env.PAIRS_BUNDLE) {
  const listed = new Set(gone.map((entry) => entry.slug));
  const pairs = Object.values(readBundle(path.resolve(process.env.PAIRS_BUNDLE)).pages.PairPage ?? {});
  // `pair: true` marks a claim that leads to its pair, whose page and files the build does not
  // make (src/lib/pairs.ts, claimsWithAPair): the Worker sends its files' addresses to the
  // pair's too. A claim whose slug is its pair's address is listed so, and is not redirected.
  const single = new Map();
  for (const page of pairs) {
    const slug = page.row.origin?.claim_slug;
    if (slug) single.set(slug, single.has(slug) ? null : page.row.pair.address);
  }
  const moved = movedAddresses(pairs);
  for (const [slug, to] of single) {
    if (to === null || listed.has(slug)) continue;
    if (to !== slug && moved[slug] !== to) throw new Error(`The rule for ${slug} disagrees with movedAddresses: ${to} and ${moved[slug]}.`);
    gone.push({ slug, to, pair: true });
  }
}
fs.writeFileSync(path.join(DIST, "gone.json"), `${JSON.stringify(gone)}\n`);

console.log(`Redirect check passed: ${lines.length} retired topic ${lines.length === 1 ? "address" : "addresses"}.`);
