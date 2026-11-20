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
import { movedAddresses } from "../src/lib/bundle.ts";
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
      return new Response(fs.readFileSync(file), { headers: { "Content-Type": type } });
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
