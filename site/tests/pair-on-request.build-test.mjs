// Pair pages made on request and the addresses of the claims the site once tracked (openspec
// pairs-site, tasks 3.4 and 4.1 to 4.3). The site is built from
// a copy of tests/bundle (real pair pages from the lab's recorded slice) in which two trial
// titles hold markup. The Worker is bundled as Wrangler bundles it and run in workerd
// (Miniflare) against a local D1 holding migration 0011 and that bundle, loaded by the store's
// own loader. The built files are served to it as the asset binding serves them.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { build as bundleWorker } from "esbuild";
import { parseHTML } from "linkedom";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";
import { movedAddresses, readBundle } from "../src/lib/bundle.ts";
import { categoryListing, interventionListing, topicListing } from "../src/lib/listing-view.ts";
import { renderListingBand, renderListingSheet } from "../src/lib/listing-render.ts";
import { shownName } from "../src/lib/pair-view.ts";
import { builtAhead } from "../src/lib/pair-view.ts";
import { STATUS_LABELS } from "../src/lib/status.ts";
import { assertNoOutcomeVerdict } from "../src/lib/trial-facts.ts";
import { UNREADABLE } from "../worker/pairs.mjs";

const MARKUP = 'A <script>alert("x")</script> & <b>bold</b> study';
const ON_REQUEST = "acoziborole--trypanosomiasis";
const BUILT_WITH_MARKUP = "apitegromab--obesity";
const COMPARED = "apitegromab--neuromuscular-diseases";
const BROKEN = "apitegromab--overweight";
const KEPT = "tulisokibart--scleroderma-diffuse";
// The addresses the site served while it tracked claims, frozen when they were removed.
const retired = JSON.parse(fs.readFileSync("data/retired-addresses.json", "utf8"));
// A claim the operator archived: its address stays gone even with a pair that came from it.
const ARCHIVED = retired.archived[0].slug;
// The one pair with posted results; given that claim's origin here, so it is also built ahead.
const WITH_RESULTS = "curcumin--gastritis-atrophic";
const ORIGIN = JSON.parse(fs.readFileSync(`tests/bundle/p12_pair_page/${BUILT_WITH_MARKUP}.json`, "utf8")).row.origin;

function copyBundle(change) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-on-request-"));
  fs.cpSync("tests/bundle", dir, { recursive: true });
  for (const [address, edit] of Object.entries(change)) {
    for (const folder of ["p12_pair_page", "p12_pair_data_file"]) {
      const file = path.join(dir, folder, `${address}.json`);
      const page = JSON.parse(fs.readFileSync(file, "utf8"));
      edit(folder === "p12_pair_page" ? page : page.pair);
      fs.writeFileSync(file, JSON.stringify(page));
    }
  }
  writeManifest(dir, { madeAt: "2026-11-20T00:00:00Z" });
  return dir;
}

const withMarkup = (page) => { page.trials[0].facts.title = MARKUP; };
// A claim whose slug is its pair's address: no redirect, the pair's page.
const SAME_ADDRESS = BUILT_WITH_MARKUP;
const bundle = copyBundle({
  [ON_REQUEST]: withMarkup,
  [BUILT_WITH_MARKUP]: (page) => { withMarkup(page); page.row.origin.claim_slug = SAME_ADDRESS; },
  [WITH_RESULTS]: (page) => {
    page.row.origin = { ...ORIGIN, claim_slug: ARCHIVED };
    // An estimate with its interval and no p value, as the lab's NCT05256017 posts one.
    const { findings } = page.trials[0];
    findings.comparisons.push({
      key: `${findings.outcomes[0].key}|099`, outcome_key: findings.outcomes[0].key, kind: "treated_vs_comparator",
      group_ids: ["OG000"], design: null, method: null, p_value: null,
      estimate_kind: "Risk Difference (RD)", estimate: "-1.5", interval_pct: "95", lower: "-7.2", upper: "3.7",
    });
    // A one-sided interval: only its lower bound is posted.
    findings.comparisons.push({
      key: `${findings.outcomes[0].key}|098`, outcome_key: findings.outcomes[0].key, kind: "treated_vs_comparator",
      group_ids: ["OG001"], design: null, method: null, p_value: null,
      estimate_kind: "Mean Difference (Final Values)", estimate: "0.4", interval_pct: "97.5", lower: "-0.2", upper: null,
    });
  },
});
// An intervention's name holding what a replacement string reads as patterns: a listing made on
// request shows it as written.
const DOLLARS = "ACOZIBOROLE $$ $& $'";
{
  const file = path.join(bundle, "p12_pair_intervention_page", "acoziborole.json");
  const listing = JSON.parse(fs.readFileSync(file, "utf8"));
  listing.intervention.preferred_name = DOLLARS;
  fs.writeFileSync(file, JSON.stringify(listing));
  fs.rmSync(path.join(bundle, "manifest.json"));
  writeManifest(bundle, { madeAt: "2026-11-20T00:00:00Z" });
}
// Which claim leads to which pair, by the bundle's own record of where each pair came from.
const moved = movedAddresses(fs.readdirSync(path.join(bundle, "p12_pair_page")).map((name) => JSON.parse(fs.readFileSync(path.join(bundle, "p12_pair_page", name), "utf8"))));
const leads = [...moved].filter(([slug]) => slug !== ARCHIVED && retired.pages.includes(slug));
// A claim with a pair, and one with none in this bundle.
const [[MATCHED]] = leads;
const UNMATCHED = retired.pages.find((slug) => !moved.has(slug) && !retired.archived.some((entry) => entry.slug === slug) && !retired.moved.some((entry) => entry.slug === slug));
const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-on-request-"));
const pages = Object.fromEntries(
  fs.readdirSync(path.join(bundle, "p12_pair_page")).map((name) => [name.slice(0, -5), JSON.parse(fs.readFileSync(path.join(bundle, "p12_pair_page", name), "utf8"))]),
);
// Paths whose built file the asset binding is told to leave out, so the Worker must make them.
const hidden = new Set();
// Appended to the frame, to stand for a redeploy with the same bundle and another frame.
let frameChange = "";
let mf;

/** The built files, as the asset binding serves them: a page at its address, else the 404 page. */
function assets(request) {
  const { pathname } = new URL(request.url);
  const clean = pathname.replace(/\/$/, "") || "/";
  const candidates = clean === "/" ? ["index.html"] : [`${clean.slice(1)}/index.html`, clean.slice(1), `${clean.slice(1)}.html`];
  for (const candidate of candidates) {
    const file = path.join(dist, candidate);
    if (!hidden.has(clean) && fs.existsSync(file) && fs.statSync(file).isFile()) {
      const type = file.endsWith(".html") ? "text/html; charset=utf-8" : file.endsWith(".json") ? "application/json" : "application/octet-stream";
      const body = clean === "/pair-shell" ? fs.readFileSync(file, "utf8") + frameChange : fs.readFileSync(file);
      // As a preview's _headers mark every asset (scripts/pr-preview.mjs).
      return new Response(body, { headers: { "Content-Type": type, "X-Robots-Tag": "noindex" } });
    }
  }
  return new Response(fs.readFileSync(path.join(dist, "404.html")), { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

/** Migration 0011, one statement at a time, as D1 applies it. */
function migration() {
  const text = fs.readFileSync("../store/ingest/migrations/0011_pairs.sql", "utf8")
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n");
  return text.split(/;\s*\n/).map((one) => one.trim()).filter(Boolean);
}

async function load(db, folder) {
  for (const sql of statements(folder).sql) await db.prepare(sql).run();
}

before(async () => {
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: { ...process.env, PAIRS_BUNDLE: bundle, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const redirects = spawnSync(process.execPath, ["scripts/redirects.mjs"], {
    env: { ...process.env, DIST_DIR: dist, PAIRS_BUNDLE: bundle },
    encoding: "utf8",
  });
  assert.equal(redirects.status, 0, redirects.stdout + redirects.stderr);
  const worker = await bundleWorker({
    entryPoints: ["worker/with-pairs.mjs"],
    bundle: true,
    format: "esm",
    platform: "browser",
    conditions: ["workerd", "worker", "browser"],
    target: "es2022",
    write: false,
  });
  mf = new Miniflare(convertV4MiniflareOptions({
    modules: true,
    script: worker.outputFiles[0].text,
    compatibilityDate: "2026-10-01",
    cf: false,
    d1Databases: ["PAIRS"],
    serviceBindings: { ASSETS: assets },
  }));
  const db = await mf.getD1Database("PAIRS");
  for (const sql of migration()) await db.prepare(sql).run();
  await load(db, bundle);
});

after(async () => { if (mf) await mf.dispose(); });

const get = (pathname) => mf.dispatchFetch(`https://site.test${pathname}`, { redirect: "manual" });
const documentOf = async (response) => parseHTML(await response.text()).document;

test("the rule builds a pair ahead when it came from a claim or rests on more than one trial", () => {
  for (const [address, page] of Object.entries(pages)) {
    const expected = page.row.origin !== null || page.trials.length > 1;
    assert.equal(builtAhead(page), expected, address);
    assert.equal(fs.existsSync(path.join(dist, address, "index.html")), expected, address);
    assert.equal(fs.existsSync(path.join(dist, "og", `${address}.png`)), expected, address);
  }
  assert.ok(Object.values(pages).some((page) => !builtAhead(page)));
});

test("a pair not built ahead is made on request from D1, kept a day", async () => {
  for (const [address, page] of Object.entries(pages).filter(([one, file]) => !builtAhead(file) && one !== BROKEN)) {
    const response = await get(`/${address}`);
    assert.equal(response.status, 200, address);
    assert.match(response.headers.get("Cache-Control"), /max-age=86400/);
    const document = await documentOf(response);
    assert.equal(document.querySelector("[data-pair-status]").dataset.pairStatus, page.row.status.code);
    assert.match(document.querySelector("[data-pair-status]").textContent, new RegExp(STATUS_LABELS[page.row.status.code]));
    assert.match(document.querySelector("title").textContent, new RegExp(page.row.descriptor.label.split(",")[0], "i"));
    assert.equal(document.querySelectorAll("[data-trial]").length, page.trials.length);
    // Posted results and papers are shown on a page made on request as on a built one.
    for (const trial of page.trials) {
      const shown = document.querySelector(`[data-trial="${trial.nct_id}"]`);
      assert.equal(shown.querySelectorAll("[data-outcome]").length, trial.findings?.outcomes.length ?? 0, `${address} ${trial.nct_id}`);
      assert.equal(shown.querySelectorAll("[data-paper]").length, trial.paper_ids.length, `${address} ${trial.nct_id}`);
    }
  }
});

test("a trial's posted results are shown as the registry wrote them, built ahead and made on request", async () => {
  const file = pages[WITH_RESULTS];
  assert.ok(builtAhead(file));
  const built = parseHTML(fs.readFileSync(path.join(dist, WITH_RESULTS, "index.html"), "utf8")).document;
  hidden.add(`/${WITH_RESULTS}`);
  let made;
  try {
    const response = await get(`/${WITH_RESULTS}`);
    assert.equal(response.status, 200);
    made = await documentOf(response);
  } finally {
    hidden.delete(`/${WITH_RESULTS}`);
  }
  assert.equal(made.querySelector(".frame").outerHTML, built.querySelector(".frame").outerHTML);
  const [trial] = file.trials;
  const section = built.querySelector(`[data-trial="${trial.nct_id}"] [data-results]`);
  assert.equal(section.querySelectorAll("[data-outcome]").length, trial.findings.outcomes.length);
  assert.equal(section.querySelectorAll("[data-comparison]").length, trial.findings.comparisons.length);
  // A comparison says which groups it covers, by the outcome's own group titles.
  assert.match(section.textContent, /p = 0\.3990, Wilcoxon Rank-Sum test \(superiority test\)\. Posted for: Arm I \(Curcumin\), Arm II \(Placebo\)/);
  // An estimate and its interval are kept, and are not called a comparison with no p value.
  const estimate = [...section.querySelectorAll("[data-comparison]")].find((line) => /Risk Difference/.test(line.textContent));
  assert.equal(estimate.textContent, "Risk Difference (RD) -1.5, 95% interval -7.2 to 3.7. Posted for: Arm I (Curcumin)");
  const oneSided = [...section.querySelectorAll("[data-comparison]")].find((line) => /Mean Difference/.test(line.textContent));
  assert.equal(oneSided.textContent, "Mean Difference (Final Values) 0.4, 97.5% interval from -0.2. Posted for: Arm II (Placebo)");
  assertNoOutcomeVerdict([section.textContent]);
});

test("the same file gives the same page built ahead and made on request", async () => {
  const built = parseHTML(fs.readFileSync(path.join(dist, COMPARED, "index.html"), "utf8")).document;
  hidden.add(`/${COMPARED}`);
  try {
    const response = await get(`/${COMPARED}`);
    assert.equal(response.status, 200);
    const made = await documentOf(response);
    assert.equal(made.querySelector(".band.record").outerHTML, built.querySelector(".band.record").outerHTML);
    assert.equal(made.querySelector(".frame").outerHTML, built.querySelector(".frame").outerHTML);
    assert.equal(made.querySelector("title").textContent, built.querySelector("title").textContent);
  } finally {
    hidden.delete(`/${COMPARED}`);
  }
});

test("a pair's open data record is written by the build only with its page, and served from D1 otherwise", async () => {
  // Task 1.3: one record a pair would pass the deployment's file limit at full size.
  for (const [address, page] of Object.entries(pages)) {
    assert.equal(fs.existsSync(path.join(dist, "data", "pairs", `${address}.json`)), builtAhead(page), address);
  }
  const index = JSON.parse(fs.readFileSync(path.join(dist, "data", "pairs.json"), "utf8"));
  assert.equal(index.entries.length, Object.keys(pages).length);
  for (const entry of index.entries) {
    const response = await get(entry.record);
    assert.equal(response.status, 200, entry.record);
    assert.match(response.headers.get("Content-Type"), /application\/json/);
    const record = await response.json();
    assert.equal(record.format, "pair-record");
    assert.equal(record.pair.row.pair.address, entry.address);
  }
  // The record made on request is the build's own text for the same file.
  const recordPath = `/data/pairs/${COMPARED}.json`;
  const built = fs.readFileSync(path.join(dist, recordPath.slice(1)), "utf8");
  hidden.add(recordPath);
  try {
    const response = await get(recordPath);
    assert.equal(response.status, 200);
    assert.match(response.headers.get("Cache-Control"), /max-age=86400/);
    assert.equal(await response.text(), built);
  } finally {
    hidden.delete(recordPath);
  }
  assert.equal((await get("/data/pairs/no-such--pair.json")).status, 404);
});

test("a title holding markup is shown as text, built ahead and made on request", async () => {
  const built = fs.readFileSync(path.join(dist, BUILT_WITH_MARKUP, "index.html"), "utf8");
  const made = await (await get(`/${ON_REQUEST}`)).text();
  for (const html of [built, made]) {
    const document = parseHTML(html).document;
    const trial = document.querySelector("[data-trial] h3");
    assert.match(trial.textContent, /A <script>alert\("x"\)<\/script> & <b>bold<\/b> study/);
    assert.equal(trial.querySelector("script, b"), null);
    assert.ok(html.includes("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"));
  }
});

test("an address the bundle does not hold answers the not-found page, and so does the frame", async () => {
  for (const pathname of ["/no-such--pair", "/pair-shell"]) {
    const response = await get(pathname);
    assert.equal(response.status, 404, pathname);
    assert.doesNotMatch(await response.text(), /__PAIR_TITLE__/);
  }
});

test("a file that fails its validator gets the error page, with nothing from the file", async () => {
  const db = await mf.getD1Database("PAIRS");
  const version = statements(bundle).version;
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairPage' AND key = ?2 AND part > 0").bind(version, BROKEN).run();
  await db.prepare("UPDATE pair_page SET body = ?3 WHERE version = ?1 AND model = 'PairPage' AND key = ?2").bind(version, BROKEN, JSON.stringify({ row: { pair: { address: BROKEN } }, names: [{ name: "APITEGROMAB" }] })).run();
  const response = await get(`/${BROKEN}`);
  assert.equal(response.status, 500);
  const document = await documentOf(response);
  assert.equal(document.querySelector("[data-pair-unreadable]").textContent, UNREADABLE);
  assert.doesNotMatch(document.querySelector(".band.record").textContent + (document.querySelector(".frame")?.textContent ?? ""), /apitegromab/i);
});

test("the Worker reads only the bundle version the build read, whatever is current", async () => {
  const newer = copyBundle({ [KEPT]: (page) => { page.row.intervention.preferred_name = "RENAMEDINLATER"; } });
  const db = await mf.getD1Database("PAIRS");
  await load(db, newer);
  const current = await db.prepare("SELECT version FROM pair_bundle WHERE current = 1").first();
  assert.equal(current.version, statements(newer).version);
  assert.notEqual(current.version, statements(bundle).version);
  const text = await (await get(`/${KEPT}`)).text();
  assert.match(text, /Tulisokibart for scleroderma/);
  assert.doesNotMatch(text, /Renamedinlater/i);
});

test("a claim whose pair is published leads to it, an archived one is still gone", async () => {
  assert.ok(leads.length > 0);
  for (const [slug, address] of leads) {
    const response = await get(`/${slug}?from=share`);
    assert.equal(response.status, 301, slug);
    assert.equal(new URL(response.headers.get("Location")).pathname + new URL(response.headers.get("Location")).search, `/${address}?from=share`);
  }
  // Archived by the operator: gone, with the day, though a pair came from it.
  assert.equal(moved.get(ARCHIVED), WITH_RESULTS);
  const archived = await get(`/${ARCHIVED}`);
  assert.equal(archived.status, 410);
  assert.match(await archived.text(), /taken down on \d+ \w+ 20\d\d/);
  assert.equal(moved.get(SAME_ADDRESS), undefined);
  const same = await get(`/${SAME_ADDRESS}`);
  assert.equal(same.status, 200);
  assert.ok((await documentOf(same)).querySelector("[data-pair-status]"));
});

test("no file is built for a claim, and every address of one with a pair leads to the pair's", async () => {
  const address = moved.get(MATCHED);
  const files = [`${MATCHED}/index.html`, `data/claims/${MATCHED}.json`, `embed/${MATCHED}/index.html`, `oembed/${MATCHED}.json`,
    `og/${MATCHED}.png`, `og/square/${MATCHED}.png`, `og/tall/${MATCHED}.png`, `changes/${MATCHED}.xml`, "data/claims.json"];
  for (const file of files) assert.ok(!fs.existsSync(path.join(dist, file)), file);
  // What each of its addresses answers now, the saved aliases of its page and embed among them.
  const to = {
    [`/${MATCHED}`]: `/${address}`,
    [`/${MATCHED}/`]: `/${address}`,
    [`/${MATCHED}/index.html`]: `/${address}`,
    [`/data/claims/${MATCHED}.json`]: `/data/pairs/${address}.json`,
    [`/embed/${MATCHED}`]: `/embed/${address}`,
    [`/embed/${MATCHED}.html`]: `/embed/${address}`,
    [`/embed/${MATCHED}/index.html`]: `/embed/${address}`,
    [`/oembed/${MATCHED}.json`]: `/oembed/${address}.json`,
    [`/og/${MATCHED}.png`]: `/og/${address}.png`,
    [`/og/square/${MATCHED}.png`]: `/og/square/${address}.png`,
    [`/og/tall/${MATCHED}.png`]: `/og/tall/${address}.png`,
    [`/changes/${MATCHED}.xml`]: "/changes.xml",
  };
  for (const [from, target] of Object.entries(to)) {
    const response = await get(from);
    assert.equal(response.status, 301, from);
    assert.equal(new URL(response.headers.get("Location")).pathname, target, from);
    // And the pair's own file answers.
    assert.equal((await get(target)).status, 200, target);
  }
});

test("every address of a claim with no pair answers gone, and so does the claims' data file", async () => {
  assert.ok(UNMATCHED);
  for (const pathname of [`/${UNMATCHED}`, `/${UNMATCHED}/index.html`, `/data/claims/${UNMATCHED}.json`, `/embed/${UNMATCHED}`, `/oembed/${UNMATCHED}.json`,
    `/og/${UNMATCHED}.png`, `/og/square/${UNMATCHED}.png`, `/og/tall/${UNMATCHED}.png`, `/changes/${UNMATCHED}.xml`, "/data/claims.json"]) {
    const response = await get(pathname);
    assert.equal(response.status, 410, pathname);
  }
  const page = await get(`/${UNMATCHED}`);
  const text = await page.text();
  assert.match(text, /This page has been removed\./);
  assert.match(text, /noindex/);
  // An address the site never served is not found, not gone.
  assert.equal((await get("/never-a-claim-of-this-site")).status, 404);
});


// Listing pages (openspec pairs-site task 4.6a): none is built; the Worker makes each from the
// lab's page file, with the shared renderer. These run before the tests below change the store.
const bundleFiles = () => readBundle(bundle).pages;
const publishedSet = () => new Set(Object.keys(pages));
const categorySet = () => new Set(Object.keys(bundleFiles().PairClinicalCategoryPage));
const shellDocument = () => parseHTML(fs.readFileSync(path.join(dist, "pair-shell", "index.html"), "utf8")).document;
const meshEditionOfBuild = () => shellDocument().querySelector("[data-mesh-edition]").getAttribute("data-mesh-edition");

/** Every listing of the bundle: its path and the view the shared reader gives for its file. */
function everyListing() {
  const files = bundleFiles();
  return [
    ...Object.entries(files.PairInterventionPage).map(([slug, file]) => [`/intervention/${slug}`, interventionListing(file, publishedSet())]),
    ...Object.entries(files.PairClinicalCategoryPage).map(([id, file]) => [`/clinical/${id}`, categoryListing(file, publishedSet(), categorySet())]),
    ...Object.entries(files.PairTopicPage).map(([slug, file]) => [`/topic/${slug}`, topicListing(file, publishedSet())]),
  ];
}

/** The bundle's codes that are codes only: those with an underscore, and intervention ids. */
function bundleCodes() {
  const codes = new Set(Object.values(pages).map((page) => page.row.intervention.id));
  for (const name of fs.readdirSync(path.join(bundle, "schemas"))) {
    JSON.stringify(JSON.parse(fs.readFileSync(path.join(bundle, "schemas", name), "utf8")), (key, value) => {
      if (key === "enum") for (const code of value) if (typeof code === "string" && code.includes("_")) codes.add(code);
      return value;
    });
  }
  return codes;
}

const listedOn = (document) => [...document.querySelectorAll("[data-pair]")].map((row) => row.dataset.pair).sort();
const filedIn = (file) => [...new Set(file.pairs.map((row) => row.pair.address))].filter((address) => address in pages).sort();
const squash = (text) => text.replace(/\s+/g, " ").trim();

test("no listing page is built, and the Worker makes each from its file with the shared renderer", async () => {
  const edition = meshEditionOfBuild();
  assert.ok(edition.length > 0);
  for (const [pathname, view] of everyListing()) {
    assert.ok(!fs.existsSync(path.join(dist, pathname.slice(1))), `${pathname} is built`);
    const response = await get(pathname);
    assert.equal(response.status, 200, pathname);
    assert.match(response.headers.get("Cache-Control"), /max-age=86400/);
    assert.equal(response.headers.get("X-Robots-Tag"), "noindex", pathname);
    const made = await documentOf(response);
    const band = parseHTML(`<main>${renderListingBand(view)}</main>`).document;
    const sheet = parseHTML(`<main>${renderListingSheet(view, edition)}</main>`).document;
    assert.equal(made.querySelector(".band.record").outerHTML, band.querySelector(".band.record").outerHTML, pathname);
    assert.equal(made.querySelector(".frame").outerHTML, sheet.querySelector(".frame").outerHTML, pathname);
    assert.equal(made.querySelector("title").textContent.startsWith(view.title), true, pathname);
    assert.deepEqual(listedOn(made), view.rows.map((row) => row.address).sort(), pathname);
    // No code of the bundle where its words belong.
    for (const element of made.querySelectorAll("script, style, template")) element.remove();
    for (const code of bundleCodes()) assert.ok(!made.body.textContent.includes(code), `${pathname} shows the code ${code}`);
  }
});

test("a listing lists its file's pairs that have a page, and none the slice left out", async () => {
  const files = bundleFiles();
  for (const [slug, file] of Object.entries(files.PairInterventionPage)) {
    assert.deepEqual(listedOn(await documentOf(await get(`/intervention/${slug}`))), filedIn(file), slug);
  }
  for (const [slug, file] of Object.entries(files.PairTopicPage)) {
    assert.deepEqual(listedOn(await documentOf(await get(`/topic/${slug}`))), filedIn(file), slug);
  }
  for (const [id, file] of Object.entries(files.PairClinicalCategoryPage)) {
    assert.deepEqual(listedOn(await documentOf(await get(`/clinical/${id}`))), filedIn(file), id);
  }
  // The slice's ambroxol file names a pair whose page the slice left out.
  const named = files.PairInterventionPage.ambroxol.pairs.map((row) => row.pair.address);
  assert.ok(named.some((address) => !(address in pages)));
  assert.deepEqual(listedOn(await documentOf(await get("/intervention/ambroxol"))), named.filter((address) => address in pages).sort());
});

test("a category's page links only categories with a page, says how many pairs sit beneath each narrower one, and credits MeSH", async () => {
  const known = categorySet();
  const built = parseHTML(fs.readFileSync(path.join(dist, "clinical", "index.html"), "utf8")).document;
  for (const id of known) {
    const made = await documentOf(await get(`/clinical/${id}`));
    for (const link of made.querySelectorAll("[data-links] a")) {
      assert.ok(known.has(link.getAttribute("href").slice("/clinical/".length)), `${id} links ${link.getAttribute("href")}`);
    }
    for (const link of made.querySelectorAll('[data-links="narrower"] a')) {
      const count = Number(link.nextElementSibling.textContent);
      const below = await documentOf(await get(link.getAttribute("href")));
      // The narrower page lists at least the pairs this page counts beneath it.
      assert.ok(count > 0 && listedOn(below).length >= count, `${id}: ${link.textContent} ${count}`);
    }
    // The vocabulary's credit, in the words the built clinical index shows.
    assert.equal(squash(made.querySelector(".mesh-credit").textContent), squash(built.querySelector(".mesh-credit").textContent), id);
  }
  // The slice's Infections file names Hidradenitis Suppurativa beneath it, which has no page.
  assert.ok(bundleFiles().PairClinicalCategoryPage.D007239.narrower.some((one) => !known.has(one.descriptor_id)));
});

test("a listing's page carries the trail above it as structured data", async () => {
  for (const [pathname, view] of everyListing()) {
    const made = await documentOf(await get(pathname));
    const trails = [...made.querySelectorAll('script[type="application/ld+json"]')].map((script) => JSON.parse(script.textContent)).filter((one) => one["@type"] === "BreadcrumbList");
    assert.equal(trails.length, 1, pathname);
    const names = trails[0].itemListElement.map((item) => item.name);
    assert.deepEqual(names.slice(1), [...view.crumbs.map((crumb) => crumb.label), view.title], pathname);
    assert.equal(new URL(trails[0].itemListElement.at(-1).item).pathname, pathname);
  }
});

test("a listing's name is shown as written, whatever a replacement string would read in it", async () => {
  const made = await documentOf(await get("/intervention/acoziborole"));
  assert.equal(made.querySelector("[data-listing]").textContent, shownName(DOLLARS));
  assert.match(made.querySelector("title").textContent, new RegExp(shownName(DOLLARS).replace(/[$&']/g, "\\$&")));
});

test("the directory pages count the pairs each listing they link lists", async () => {
  const topics = parseHTML(fs.readFileSync(path.join(dist, "topics", "index.html"), "utf8")).document;
  for (const item of topics.querySelectorAll("[data-topic]")) {
    const count = Number(item.querySelector(".count").firstChild.textContent.trim());
    assert.equal(listedOn(await documentOf(await get(`/topic/${item.dataset.topic}`))).length, count, item.dataset.topic);
  }
  const clinical = parseHTML(fs.readFileSync(path.join(dist, "clinical", "index.html"), "utf8")).document;
  for (const item of clinical.querySelectorAll("[data-category]")) {
    const count = Number(item.querySelector(".count").textContent.trim());
    assert.equal(listedOn(await documentOf(await get(`/clinical/${item.dataset.category}`))).length, count, item.dataset.category);
  }
});

test("a pair filed under no topic is listed on its intervention's page and on no topic's", async () => {
  const unfiled = Object.values(pages).find((page) => page.row.filing === null);
  assert.ok(unfiled);
  const address = unfiled.row.pair.address;
  assert.ok(listedOn(await documentOf(await get(`/intervention/${unfiled.row.intervention.slug}`))).includes(address));
  for (const slug of Object.keys(bundleFiles().PairTopicPage)) {
    assert.ok(!listedOn(await documentOf(await get(`/topic/${slug}`))).includes(address), slug);
  }
});

test("a listing cached for one frame is not answered for another with the same bundle", async () => {
  const first = await (await get("/topic/infections")).text();
  assert.ok(!first.includes("<!--another-frame-->"));
  frameChange = "<!--another-frame-->";
  try {
    assert.ok((await (await get("/topic/infections")).text()).includes("<!--another-frame-->"));
  } finally {
    frameChange = "";
  }
});

test("a listing address no file holds is not found, and one no listing could have is refused before any read", async () => {
  for (const pathname of ["/intervention/no-such-treatment", "/clinical/D000000001", "/topic/no-such-topic"]) {
    assert.equal((await get(pathname)).status, 404, pathname);
  }
  // With the page table gone, a well-formed address fails on its read; a malformed one never reads.
  const db = await mf.getD1Database("PAIRS");
  await db.prepare("ALTER TABLE pair_page RENAME TO pair_page_away").run();
  try {
    for (const pathname of ["/intervention/Not_A_Slug", "/intervention/a--b", "/clinical/X007239", "/clinical/D12", "/topic/x/y", "/topic/"]) {
      assert.equal((await get(pathname)).status, 404, pathname);
    }
    assert.notEqual((await get("/intervention/no-such-treatment")).status, 404, "the well-formed address reads the table");
  } finally {
    await db.prepare("ALTER TABLE pair_page_away RENAME TO pair_page").run();
  }
});

test("a listing file stored as JSON null is checked, and gives the error page", async () => {
  const db = await mf.getD1Database("PAIRS");
  const version = statements(bundle).version;
  const [row] = (await db.prepare("SELECT key FROM pair_page WHERE version = ?1 AND model = 'PairTopicPage' ORDER BY key LIMIT 1").bind(version).all()).results;
  const { results: kept } = await db.prepare("SELECT part, body FROM pair_page WHERE version = ?1 AND model = 'PairTopicPage' AND key = ?2").bind(version, row.key).all();
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairTopicPage' AND key = ?2 AND part > 0").bind(version, row.key).run();
  await db.prepare("UPDATE pair_page SET body = 'null' WHERE version = ?1 AND model = 'PairTopicPage' AND key = ?2").bind(version, row.key).run();
  try {
    frameChange = "<!--null-check-->";
    const response = await get(`/topic/${row.key}`);
    assert.equal(response.status, 500);
    assert.ok((await documentOf(response)).querySelector("[data-pair-unreadable]"));
  } finally {
    frameChange = "";
    await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairTopicPage' AND key = ?2").bind(version, row.key).run();
    for (const part of kept) await db.prepare("INSERT INTO pair_page (version, model, key, part, body) VALUES (?1, 'PairTopicPage', ?2, ?3, ?4)").bind(version, row.key, part.part, part.body).run();
  }
});

test("a pair names the same treatment's pairs for narrower conditions, built ahead and made on request", async () => {
  // acoziborole--infections (C01, built ahead) and acoziborole--trypanosomiasis (C01.610…, made
  // on request) from the small bundle; the African form sits beneath both.
  const named = (html) => [...parseHTML(html).document.querySelectorAll("[data-pair-narrower] [data-narrower]")].map((link) => link.dataset.narrower);
  assert.deepEqual(named(fs.readFileSync(path.join(dist, "acoziborole--infections", "index.html"), "utf8")), [
    "acoziborole--trypanosomiasis", "acoziborole--trypanosomiasis-african",
  ]);
  const made = await get("/acoziborole--trypanosomiasis");
  assert.equal(made.status, 200);
  assert.ok(!fs.existsSync(path.join(dist, "acoziborole--trypanosomiasis", "index.html")), "made on request");
  assert.deepEqual(named(await made.text()), ["acoziborole--trypanosomiasis-african"]);
  // The narrowest has nothing beneath it, and says nothing.
  assert.deepEqual(named(fs.readFileSync(path.join(dist, "acoziborole--trypanosomiasis-african", "index.html"), "utf8")), []);
  assert.ok(!fs.readFileSync(path.join(dist, "acoziborole--trypanosomiasis-african", "index.html"), "utf8").includes("data-pair-narrower"));
});

test("an intervention page that fails its check stops a page made on request", async () => {
  const db = await mf.getD1Database("PAIRS");
  const version = statements(bundle).version;
  // apitegromab--obesity is built ahead; hidden from the asset binding, the Worker makes it, for
  // the first time in this run (its answers are kept a day, so a page made earlier would be).
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'apitegromab' AND part > 0").bind(version).run();
  await db.prepare("UPDATE pair_page SET body = ?2 WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'apitegromab'").bind(version, JSON.stringify({ pairs: "not a list" })).run();
  hidden.add("/apitegromab--obesity");
  let response;
  try {
    response = await get("/apitegromab--obesity");
  } finally {
    hidden.delete("/apitegromab--obesity");
  }
  assert.equal(response.status, 500);
  assert.equal(parseHTML(await response.text()).document.querySelector("[data-pair-unreadable]").textContent, UNREADABLE);
});

test("a narrower pair the version holds no page for is not linked, and a stored null is checked", async () => {
  const db = await mf.getD1Database("PAIRS");
  const version = statements(bundle).version;
  // A slice without the African form's page: its intervention listing still names it.
  await db.prepare("DELETE FROM pair WHERE version = ?1 AND address = 'acoziborole--trypanosomiasis-african'").bind(version).run();
  hidden.add("/acoziborole--infections");
  try {
    const made = await get("/acoziborole--infections");
    assert.equal(made.status, 200);
    const named = [...parseHTML(await made.text()).document.querySelectorAll("[data-narrower]")].map((link) => link.dataset.narrower);
    assert.deepEqual(named, ["acoziborole--trypanosomiasis"]);
  } finally {
    hidden.delete("/acoziborole--infections");
  }
  // An intervention page file stored as JSON null is a body like any other, and fails its check.
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'tulisokibart' AND part > 0").bind(version).run();
  await db.prepare("UPDATE pair_page SET body = 'null' WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'tulisokibart'").bind(version).run();
  hidden.add("/tulisokibart--lung-diseases-interstitial");
  try {
    assert.equal((await get("/tulisokibart--lung-diseases-interstitial")).status, 500);
  } finally {
    hidden.delete("/tulisokibart--lung-diseases-interstitial");
  }
});
