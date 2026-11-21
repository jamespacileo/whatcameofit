// The pages of claims with no verified pair, kept at their own addresses as production last
// served them (the operator, 2026-11-21: "preserve unmatched claim content and associated
// existing URLs while keeping verified redirects").
//
// Until 2026-11-20 the site tracked claims. Production's last build of them is commit
// KEPT_CLAIMS_COMMIT, and the files a claim had there are kept byte for byte: its page, its
// embed, its oEmbed description, its three cards, its open data record and its feed, with the
// styles, scripts and fonts those files load. Nothing renders a claim any more; the files are
// copied.
//
//   node scripts/kept-claims.mjs freeze <old dist> <folder>   once, from that commit's build
//
// `freeze` writes the folder: every kept file under files/, and manifest.json naming the commit,
// each claim's files and each file's SHA-256. make kept-claims builds the commit and freezes it
// (scripts/freeze-kept-claims.sh). At each build scripts/redirects.mjs places the files of each
// claim no published pair came from (`placeKept`), so the host serves them before the Worker;
// a claim a pair came from still leads to it (301), and an archived one stays gone (410).
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

/** Production's build revision when claims were removed: the bytes kept are its build's. */
export const KEPT_CLAIMS_COMMIT = "4ea7f23613d9bd390c601b1ef00048c864064e81";

/** The shape of a frozen folder. 2: each claim's year indexes, icons and assets are named in
 * `needs`, so a build places only what its kept claims reach. A folder frozen in another shape
 * is refused, never read as if it were this one. */
export const KEPT_FORMAT = 2;

/** The files a claim had, by its slug, as built paths. */
export function claimFiles(slug) {
  return [
    `${slug}/index.html`,
    `embed/${slug}/index.html`,
    `oembed/${slug}.json`,
    `og/${slug}.png`,
    `og/square/${slug}.png`,
    `og/tall/${slug}.png`,
    `data/claims/${slug}.json`,
    `changes/${slug}.xml`,
  ];
}

const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

/** The site-relative files a page, style or script loads, as built paths. */
function references(builtPath, text) {
  const found = new Set();
  for (const match of text.matchAll(/(?:href|src)="(\/[^"#?]+)"/g)) found.add(match[1].slice(1));
  for (const match of text.matchAll(/url\((\/[^)"'#?]+)\)/g)) found.add(match[1].slice(1));
  // A script's own imports, relative to it.
  for (const match of text.matchAll(/(?:from\s*|import\s*\(\s*)"(\.\.?\/[^"]+)"/g)) {
    found.add(path.posix.normalize(path.posix.join(path.posix.dirname(builtPath), match[1])));
  }
  return found;
}

/**
 * Copy the kept claims' files out of an old build with their assets and year indexes.
 * Each claim links its first report date to a year index. The pair site does not build
 * those indexes, so take the original pages and follow the assets they load too.
 * Other site addresses are listed as `linked`.
 * @param {{ from: string, to: string, slugs: string[], commit: string }} options
 */
export function freeze({ from, to, slugs, commit }) {
  if (fs.existsSync(to)) throw new Error(`${to} exists; freeze writes a new folder.`);
  const claims = {};
  const missing = [];
  const kept = new Set();
  for (const slug of slugs) {
    const files = claimFiles(slug).filter((file) => fs.existsSync(path.join(from, file)));
    if (!files.includes(`${slug}/index.html`)) {
      missing.push(slug);
      continue;
    }
    claims[slug] = files;
    for (const file of files) kept.add(file);
  }
  const own = new Set(kept);
  const linked = new Set();
  // What each file loads or links to, read once however many claims reach it.
  const refs = new Map();
  const refsOf = (file) => {
    if (!refs.has(file)) refs.set(file, references(file, fs.readFileSync(path.join(from, file), "utf8")));
    return refs.get(file);
  };
  // Each claim's own reach: the assets, icons and year indexes it needs, followed through
  // those it needs in turn, so a build places a year index only when a claim it keeps links it.
  const needs = {};
  for (const [slug, files] of Object.entries(claims)) {
    const reached = new Set();
    const queue = files.filter((file) => /\.(html|css|js)$/.test(file));
    const seen = new Set(queue);
    while (queue.length > 0) {
      const file = queue.pop();
      for (const ref of refsOf(file)) {
        const yearIndex = /^year\/\d{4}\/?$/.test(ref);
        const built = yearIndex ? `${ref.replace(/\/$/, "")}/index.html` : ref;
        if (own.has(built) || reached.has(built)) continue;
        const outletIcon = /^outlet-icons\/[^/]+\.[a-z]+$/.test(built);
        if ((built.startsWith("_astro/") || outletIcon || yearIndex) && fs.existsSync(path.join(from, built))) {
          reached.add(built);
          if (/\.(html|css|js)$/.test(built) && !seen.has(built)) {
            seen.add(built);
            queue.push(built);
          }
        } else if (!claimFiles(ref.replace(/\/$/, "")).some((one) => kept.has(one))) {
          linked.add(`/${ref}`);
        }
      }
    }
    needs[slug] = [...reached].sort();
  }
  const shared = new Set(Object.values(needs).flat());
  const sums = {};
  for (const file of [...kept, ...shared].sort()) {
    const target = path.join(to, "files", file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(path.join(from, file), target);
    sums[file] = sha256(target);
  }
  const manifest = {
    about: "Claim pages kept at their own addresses, byte for byte as production built them (site/scripts/kept-claims.mjs).",
    format: KEPT_FORMAT,
    commit,
    claims,
    shared: [...shared].sort(),
    needs,
    linked: [...linked].sort(),
    sha256: sums,
  };
  fs.writeFileSync(path.join(to, "manifest.json"), `${JSON.stringify(manifest, null, 1)}\n`);
  return { claims: Object.keys(claims).length, files: Object.keys(sums).length, missing };
}

/** The kept folder's manifest, checked to be from the pinned commit. */
export function readKept(folder) {
  const manifest = JSON.parse(fs.readFileSync(path.join(folder, "manifest.json"), "utf8"));
  if (manifest.commit !== KEPT_CLAIMS_COMMIT) {
    throw new Error(`${folder} was frozen from ${manifest.commit}, not ${KEPT_CLAIMS_COMMIT}: run make kept-claims.`);
  }
  if (manifest.format !== KEPT_FORMAT) {
    throw new Error(`${folder} was frozen in format ${manifest.format ?? 1}, not ${KEPT_FORMAT}: freeze it again into a new folder (make kept-claims).`);
  }
  return manifest;
}

/** The claims that keep their pages: every claim the site served but those archived or merged. */
export function keptSlugs(retired) {
  // An archived claim stays gone, and a merged or renamed one leads to the claim it became.
  const away = new Set([...retired.archived, ...retired.moved].map(({ slug }) => slug));
  return retired.pages.filter((slug) => !away.has(slug));
}

const RETIRED = path.resolve(import.meta.dirname, "../data/retired-addresses.json");

/** Why a folder cannot be published from: none, not the pinned commit's, or a claim missing. */
export function keptProblems(folder) {
  if (!folder) return ["KEPT_CLAIMS_DIR names no folder of kept claims: run make kept-claims (scripts/kept-claims.mjs)."];
  if (!fs.existsSync(path.join(folder, "manifest.json"))) return [`${folder} holds no kept claims: run make kept-claims.`];
  let manifest;
  try {
    manifest = readKept(folder);
  } catch (error) {
    return [error.message];
  }
  if (manifest.fixture) return [`${folder} holds the tests' kept claims, not production's: run make kept-claims.`];
  const missing = keptSlugs(JSON.parse(fs.readFileSync(RETIRED, "utf8"))).filter((slug) => !manifest.claims[slug]);
  return missing.length > 0 ? [`${folder} lacks the pages of ${missing.length === 1 ? "1 claim" : `${missing.length} claims`}, such as ${missing[0]}: freeze it again.`] : [];
}

/**
 * Put the files of each slug in the build, with the shared files they need, each checked
 * against its SHA-256. A shared file the build already holds is the build's own. Returns
 * how many files were placed.
 * @param {{ folder: string, dist: string, slugs: string[] }} options
 */
export function placeKept({ folder, dist, slugs }) {
  const manifest = readKept(folder);
  let placed = 0;
  const place = (file) => {
    const source = path.join(folder, "files", file);
    if (sha256(source) !== manifest.sha256[file]) throw new Error(`${file} in ${folder} is not the file frozen: freeze it again.`);
    const target = path.join(dist, file);
    if (fs.existsSync(target)) throw new Error(`The build already holds ${file}, which a kept claim needs.`);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(source, target);
    placed += 1;
  };
  for (const slug of slugs) for (const file of manifest.claims[slug]) place(file);
  // Only what the claims kept in this build reach: a year index whose claims all lead to pairs
  // now is not published.
  const needed = new Set(slugs.flatMap((slug) => manifest.needs[slug] ?? []));
  for (const file of [...needed].sort()) if (!fs.existsSync(path.join(dist, file))) place(file);
  return placed;
}

if (import.meta.main && process.argv[2] === "freeze") {
  const [, , , from, to] = process.argv;
  if (!from || !to) throw new Error("Usage: node scripts/kept-claims.mjs freeze <old dist> <folder>");
  const slugs = keptSlugs(JSON.parse(fs.readFileSync(RETIRED, "utf8")));
  const { claims, files, missing } = freeze({ from: path.resolve(from), to: path.resolve(to), slugs, commit: process.env.KEPT_CLAIMS_FROM ?? KEPT_CLAIMS_COMMIT });
  console.log(`Kept ${claims} claims' pages in ${files.toLocaleString("en-GB")} files at ${to}.`);
  if (missing.length > 0) {
    console.error(`No page was built for ${missing.length} of them: ${missing.join(", ")}`);
    process.exit(1);
  }
}
