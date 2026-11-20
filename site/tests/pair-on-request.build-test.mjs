// Pair pages made on request and old claim addresses (openspec pairs-site, tasks 4.1 to 4.3). The site is built from
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
import { movedAddresses } from "../src/lib/bundle.ts";
import { builtAhead } from "../src/lib/pair-view.ts";
import { STATUS_LABELS } from "../src/lib/status.ts";
import { UNREADABLE } from "../worker/pairs.mjs";

const MARKUP = 'A <script>alert("x")</script> & <b>bold</b> study';
const ON_REQUEST = "acoziborole--trypanosomiasis";
const BUILT_WITH_MARKUP = "apitegromab--obesity";
const COMPARED = "apitegromab--neuromuscular-diseases";
const BROKEN = "apitegromab--overweight";
const KEPT = "tulisokibart--scleroderma-diffuse";

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
  return dir;
}

const withMarkup = (page) => { page.trials[0].facts.title = MARKUP; };
// A claim whose slug is its pair's address: no redirect, the pair's page.
const SAME_ADDRESS = BUILT_WITH_MARKUP;
const bundle = copyBundle({
  [ON_REQUEST]: withMarkup,
  [BUILT_WITH_MARKUP]: (page) => { withMarkup(page); page.row.origin.claim_slug = SAME_ADDRESS; },
});
// The claims export, with the first moved claim also archived: its address still answers 410.
const moved = movedAddresses(Object.values(Object.fromEntries(
  fs.readdirSync(path.join(bundle, "p12_pair_page")).map((name) => [name, JSON.parse(fs.readFileSync(path.join(bundle, "p12_pair_page", name), "utf8"))]),
)));
const [ARCHIVED] = Object.keys(moved).sort();
const exportFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-export-")), "export.json");
// No topic address was published from the fixture export.
const publishedTopics = path.join(path.dirname(exportFile), "published-topics.json");
fs.writeFileSync(publishedTopics, "[]");
fs.writeFileSync(exportFile, JSON.stringify({ ...JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8")), archived: [{ slug: ARCHIVED, on: "2026-11-01" }] }));
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
    env: { ...process.env, EXPORT_FILE: "tests/fixture-export.json", PAIRS_BUNDLE: bundle, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const redirects = spawnSync(process.execPath, ["scripts/redirects.mjs"], {
    env: { ...process.env, DIST_DIR: dist, EXPORT_FILE: exportFile, PAIRS_BUNDLE: bundle, PUBLISHED_TOPICS_FILE: publishedTopics },
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
  // curcumin--gastritis-atrophic, made on request, posts its outcomes and a comparison.
  const curcumin = await documentOf(await get("/curcumin--gastritis-atrophic"));
  assert.ok(curcumin.querySelectorAll("[data-outcome]").length > 0);
  assert.match(curcumin.querySelector("[data-results]").textContent, /p = 0\.3990, Wilcoxon Rank-Sum test \(superiority test\)/);
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
  const leads = Object.entries(moved).filter(([slug]) => slug !== ARCHIVED);
  assert.ok(leads.length > 0);
  for (const [slug, address] of leads) {
    const response = await get(`/${slug}?from=share`);
    assert.equal(response.status, 301, slug);
    assert.equal(new URL(response.headers.get("Location")).pathname + new URL(response.headers.get("Location")).search, `/${address}?from=share`);
  }
  assert.equal((await get(`/${ARCHIVED}`)).status, 410);
  assert.equal(moved[SAME_ADDRESS], undefined);
  const same = await get(`/${SAME_ADDRESS}`);
  assert.equal(same.status, 200);
  assert.ok((await documentOf(same)).querySelector("[data-pair-status]"));
});
