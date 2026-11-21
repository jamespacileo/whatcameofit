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
import { heldClaims, heldRedirect, preventionClaims, verifiedRedirects } from "../scripts/redirect-scope.mjs";
import { categoryListing, interventionListing, topicListing } from "../src/lib/listing-view.ts";
import { renderListingBand, renderListingSheet } from "../src/lib/listing-render.ts";
import { shownName } from "../src/lib/pair-view.ts";
import { meshEdition } from "../src/lib/clinical.ts";
import { canonicalAddress } from "../src/lib/structured.ts";
import { narrowerPairs, pairView } from "../src/lib/pair-view.ts";
import { renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { pairRecordText } from "../src/lib/pair-record.ts";
import { embedTitle, oembedOf, renderEmbedArticle, renderEmbedRegistries } from "../src/lib/embed-render.ts";
import { SITE } from "../site.config.mjs";
import { STATUS_LABELS } from "../src/lib/status.ts";
import { assertNoOutcomeVerdict } from "../src/lib/trial-facts.ts";
import { SITE_HEADERS, UNREADABLE } from "../worker/pairs.mjs";
import { packLookup } from "../scripts/pack-lookup.mjs";
import { LEGACY_LOOKUP, PACKED_LOOKUP } from "../src/lib/lookup-assets.mjs";

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
// A claim held from a pair of another scope (scripts/redirect-scope.mjs) keeps its own page instead.
const scope = { prevention: preventionClaims(), verified: verifiedRedirects(), held: heldClaims() };
const leads = [...moved].filter(([slug, address]) => slug !== ARCHIVED && retired.pages.includes(slug) && !heldRedirect(slug, address, scope));
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
// A frame as another deployment would have it: each rewrites the built frame's text.
const frameEdits = { "/pair-shell": (text) => text, "/embed-shell": (text) => text };
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
      const body =
        clean === "/pair-shell" ? frameEdits[clean](fs.readFileSync(file, "utf8")) + frameChange
        : clean === "/embed-shell" ? frameEdits[clean](fs.readFileSync(file, "utf8"))
        : fs.readFileSync(file);
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

test("the Worker serves the complete legacy lookup with the original response bytes when packed", async () => {
  const original = path.join(dist, LEGACY_LOOKUP);
  const expected = fs.readFileSync(original, "utf8");
  try {
    packLookup(dist, Buffer.byteLength(expected) - 1);
    assert.ok(!fs.existsSync(original));
    const response = await get(LEGACY_LOOKUP);
    assert.equal(response.status, 200);
    assert.match(response.headers.get("Content-Type"), /^application\/json/i);
    assert.equal(await response.text(), expected);
    // A validator from the packed file: an asker who holds it is told it is unchanged, with
    // nothing sent and nothing decompressed.
    const tag = response.headers.get("ETag");
    assert.match(tag ?? "", /^W\/"lookup-/);
    const held = await mf.dispatchFetch(`https://site.test${LEGACY_LOOKUP}`, { headers: { "If-None-Match": tag } });
    assert.equal(held.status, 304);
    assert.equal(await held.text(), "");
    // A client that takes no gzip is sent the same bytes, decompressed by the Worker.
    const plain = await mf.dispatchFetch(`https://site.test${LEGACY_LOOKUP}`, { headers: { "Accept-Encoding": "identity" } });
    assert.equal(plain.headers.get("Content-Encoding"), null);
    assert.equal(await plain.text(), expected);
  } finally {
    fs.writeFileSync(original, expected);
    fs.rmSync(path.join(dist, PACKED_LOOKUP), { force: true });
  }
});
// A request no earlier answer is kept for: the Worker keeps each a day under a key that holds
// the host, so a test that changes the store asks on a host of its own.
let freshHosts = 0;
const getFresh = (pathname) => mf.dispatchFetch(`https://fresh-${(freshHosts += 1)}.test${pathname}`, { redirect: "manual" });
const documentOf = async (response) => parseHTML(await response.text()).document;

/** A pair's page as the shared renderer writes it, the Worker's own source of the page. */
function rendered(address) {
  const file = pages[address];
  const view = pairView(file);
  const intervention = readBundle(bundle).pages.PairInterventionPage[file.row.intervention.slug] ?? null;
  const narrower = narrowerPairs(file, intervention, new Set(Object.keys(pages)));
  return parseHTML(`<!doctype html><html><body>${renderPairBand(view)}${renderPairSheet(view, narrower)}</body></html>`).document;
}

test("no file is built per pair: every pair's page is made on request from D1, kept a day", async () => {
  for (const [address, page] of Object.entries(pages).filter(([one]) => one !== BROKEN)) {
    assert.ok(!fs.existsSync(path.join(dist, address)), `${address} is built`);
    const response = await get(`/${address}`);
    assert.equal(response.status, 200, address);
    assert.match(response.headers.get("Cache-Control"), /max-age=86400/);
    const document = await documentOf(response);
    assert.equal(document.querySelector("[data-pair-status]").dataset.pairStatus, page.row.status.code);
    assert.match(document.querySelector("[data-pair-status]").textContent, new RegExp(STATUS_LABELS[page.row.status.code]));
    assert.match(document.querySelector("title").textContent, new RegExp(page.row.descriptor.label.split(",")[0], "i"));
    assert.equal(document.querySelectorAll("[data-trial]").length, page.trials.length);
    for (const trial of page.trials) {
      // A trial's record: its own entry, or in a trials table the row under its own.
      const row = document.querySelector(`[data-trial="${trial.nct_id}"]`);
      const shown = row.matches("tr") ? row.nextElementSibling : row;
      if (row.matches("tr")) assert.ok(shown.matches(".trials-record"), `${address} ${trial.nct_id}`);
      assert.equal(shown.querySelectorAll("[data-outcome]").length, trial.findings?.outcomes.length ?? 0, `${address} ${trial.nct_id}`);
      assert.equal(shown.querySelectorAll("[data-paper]").length, trial.paper_ids.length, `${address} ${trial.nct_id}`);
    }
  }
});

test("a pair's page made on request is the shared renderer's for its file, with its own address, preview and oEmbed link", async () => {
  for (const address of Object.keys(pages).filter((one) => one !== BROKEN)) {
    const made = await documentOf(await get(`/${address}`));
    const expected = rendered(address);
    assert.equal(made.querySelector(".band.record").outerHTML, expected.querySelector(".band.record").outerHTML, address);
    assert.equal(made.querySelector(".frame").outerHTML, expected.querySelector(".frame").outerHTML, address);
    assert.equal(made.querySelector('link[rel="canonical"]').getAttribute("href"), canonicalAddress(`/${address}`));
    assert.equal(made.querySelector('meta[property="og:url"]')?.getAttribute("content") ?? canonicalAddress(`/${address}`), canonicalAddress(`/${address}`));
    // The site's own card: no pair has a picture of its own.
    assert.match(made.querySelector('meta[property="og:image"]').getAttribute("content"), /\/brand-card\.png/);
    assert.equal(made.querySelector('link[type="application/json+oembed"]').getAttribute("href"), canonicalAddress(`/oembed/${address}.json`));
    assert.equal(made.querySelector("footer.colophon").outerHTML, builtFooter(), address);
  }
});

test("a trial's posted results are shown as the registry wrote them", async () => {
  const file = pages[WITH_RESULTS];
  const made = await documentOf(await get(`/${WITH_RESULTS}`));
  const [trial] = file.trials;
  const section = made.querySelector(`[data-trial="${trial.nct_id}"] [data-results]`);
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

test("a trial's posted adverse events are shown as counts per group, and its results line states the record's fact", async () => {
  const file = pages[WITH_RESULTS];
  const made = await documentOf(await get(`/${WITH_RESULTS}`));
  const [trial] = file.trials;
  const shown = made.querySelector(`[data-trial="${trial.nct_id}"]`);
  const section = shown.querySelector("[data-harms]");
  const rows = [...section.querySelectorAll("[data-harm-group]")];
  assert.equal(rows.length, trial.findings.harms.length);
  // Affected of at risk, as posted, for deaths, serious and other events; nothing divided.
  const [first] = trial.findings.harms;
  assert.deepEqual(
    [...rows[0].querySelectorAll("td")].map((cell) => cell.textContent),
    [`${first.deaths_affected} of ${first.deaths_at_risk}`, `${first.serious_affected} of ${first.serious_at_risk}`, `${first.other_affected} of ${first.other_at_risk}`],
  );
  assert.doesNotMatch(section.textContent, /%\)|per cent of people/);
  // The bundle joins neither group to an arm, so neither is named from the outcome groups,
  // and the page says where the names are.
  assert.equal(trial.findings.arms.length, 0);
  assert.deepEqual(rows.map((row) => row.querySelector("th").textContent), ["Group 1", "Group 2"]);
  assert.equal(section.querySelector("[data-harms-groups]").getAttribute("href"), `https://clinicaltrials.gov/study/${trial.nct_id}`);
  assert.match(section.textContent, /whether or not the treatment caused it/);
  assert.match(section.textContent, new RegExp(`Counted over: ${first.time_frame}\\.`));
  // No serious event is listed for this trial, so no list of them is drawn.
  assert.equal(trial.findings.serious_events.length, 0);
  assert.equal(section.querySelector("[data-serious-events]"), null);
  assert.equal(trial.findings.due.code, "results_posted");
  assert.equal(shown.querySelector("[data-results-state]").textContent, "Posted on the registry");
  assertNoOutcomeVerdict([section.textContent]);
});

test("adverse event groups use their registry titles without a link to a registered arm", () => {
  const page = structuredClone(pages[WITH_RESULTS]);
  const { findings } = page.trials[0];
  const [totals, withoutTitle] = findings.harms;
  totals.group_title = "Registry treatment group";
  findings.serious_events.push({
    group_id: withoutTitle.group_id,
    group_title: "Registry comparison group",
    term: "Serious event",
    organ_system: null,
    affected: 1,
    at_risk: 20,
  });
  assert.deepEqual(findings.arms, []);

  const { document } = parseHTML(renderPairSheet(pairView(page), []));
  const section = document.querySelector("[data-harms]");
  const names = [...section.querySelectorAll("[data-harm-group] th")].map((cell) => cell.textContent);
  const eventHeaders = [...section.querySelectorAll("[data-serious-events] thead th")];

  assert.deepEqual(names, ["Registry treatment group", "Registry comparison group"]);
  assert.deepEqual(eventHeaders.map((cell) => cell.textContent), ["Event", ...names]);
  assert.equal(section.querySelector("[data-harms-groups]"), null);
});

test("every pair's open data record is served from D1, as the lab's data file with the licence, and none is built", async () => {
  // Task 4.6: no file per pair, so a full bundle does not grow the deployment.
  const files = readBundle(bundle).pages.PairDataFile;
  const index = JSON.parse(fs.readFileSync(path.join(dist, "data", "pairs.json"), "utf8"));
  assert.equal(index.entries.length, Object.keys(pages).length);
  for (const entry of index.entries) {
    assert.ok(!fs.existsSync(path.join(dist, entry.record.slice(1))), `${entry.record} is built`);
    const response = await get(entry.record);
    assert.equal(response.status, 200, entry.record);
    assert.match(response.headers.get("Content-Type"), /application\/json/);
    assert.match(response.headers.get("Cache-Control"), /max-age=86400/);
    // The text the shared writer gives for the lab's data file.
    assert.equal(await response.text(), pairRecordText(files[entry.address], SITE.name, SITE.url), entry.record);
  }
  assert.equal((await get("/data/pairs/no-such--pair.json")).status, 404);
});

test("a title holding markup is shown as text", async () => {
  for (const address of [BUILT_WITH_MARKUP, ON_REQUEST]) {
    const html = await (await get(`/${address}`)).text();
    const trial = parseHTML(html).document.querySelector("[data-trial] h3");
    assert.match(trial.textContent, /A <script>alert\("x"\)<\/script> & <b>bold<\/b> study/);
    assert.equal(trial.querySelector("script, b"), null);
    assert.ok(html.includes("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"));
  }
});

test("a pair's embed is made on request into the embed's frame, noindex, with the footer notices", async () => {
  for (const [address, file] of Object.entries(pages).filter(([one]) => one !== BROKEN)) {
    assert.ok(!fs.existsSync(path.join(dist, "embed", address)), `embed/${address} is built`);
    const response = await get(`/embed/${address}`);
    assert.equal(response.status, 200, address);
    assert.match(response.headers.get("Cache-Control"), /max-age=86400/);
    const made = await documentOf(response);
    const view = pairView(file);
    assert.equal(made.querySelector('meta[name="robots"]').getAttribute("content"), "noindex");
    assert.equal(made.querySelector("title").textContent, `${embedTitle(view)} | ${SITE.name}`);
    const article = parseHTML(`<!doctype html><html><body><article>${renderEmbedArticle(view, SITE.name, SITE.url)}</article></body></html>`).document;
    assert.equal(made.querySelector("[data-pair-status]").outerHTML, article.querySelector("[data-pair-status]").outerHTML, address);
    assert.ok(made.querySelector("footer").textContent.includes(renderEmbedRegistries(view).trim()), address);
    // Its stylesheet is the build's own, asked of no other host.
    assert.ok([...made.querySelectorAll('link[rel="stylesheet"]')].every((link) => link.getAttribute("href").startsWith("/")));
  }
  assert.equal((await get("/embed/no-such--pair")).status, 404);
  assert.equal((await get("/embed-shell")).status, 404);
});

test("a pair's oEmbed description is made on request, its picture the site's own card", async () => {
  const card = parseHTML(fs.readFileSync(path.join(dist, "pair-shell", "index.html"), "utf8")).document.querySelector('meta[property="og:image"]').getAttribute("content");
  for (const [address, file] of Object.entries(pages).filter(([one]) => one !== BROKEN)) {
    assert.ok(!fs.existsSync(path.join(dist, "oembed", `${address}.json`)));
    const response = await get(`/oembed/${address}.json`);
    assert.equal(response.status, 200, address);
    assert.match(response.headers.get("Content-Type"), /application\/json\+oembed/);
    assert.deepEqual(await response.json(), oembedOf(pairView(file), SITE.name, SITE.url, card));
  }
  assert.equal((await get("/oembed/no-such--pair.json")).status, 404);
});

test("a pair's card addresses answer with the site's own card, and no other address does", async () => {
  const card = new URL(parseHTML(fs.readFileSync(path.join(dist, "pair-shell", "index.html"), "utf8")).document.querySelector('meta[property="og:image"]').getAttribute("content"));
  const site = fs.readFileSync(path.join(dist, card.pathname.slice(1)));
  for (const folder of ["", "square/", "tall/"]) {
    const response = await get(`/og/${folder}${ON_REQUEST}.png`);
    assert.equal(response.status, 200, folder);
    assert.equal(response.headers.get("Content-Type"), "image/png");
    assert.ok(Buffer.from(await response.arrayBuffer()).equals(site), folder);
    assert.equal((await get(`/og/${folder}no-such--pair.png`)).status, 404, folder);
  }
});

test("an address the bundle does not hold answers the not-found page, and so does the frame", async () => {
  for (const pathname of ["/no-such--pair", "/pair-shell", "/embed-shell"]) {
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

const builtFooter = () => parseHTML(fs.readFileSync(path.join(dist, "about", "index.html"), "utf8")).document.querySelector("footer.colophon").outerHTML;
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
    // Its own canonical address, and the footer a built page carries (its notices and the site's
    // links, the extension page's among them when the build offers it).
    assert.equal(made.querySelector('link[rel="canonical"]').getAttribute("href"), canonicalAddress(pathname), pathname);
    assert.equal(made.querySelector("footer.colophon").outerHTML, builtFooter(), pathname);
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
  // The vocabulary's year as the bundle's manifest states it; this bundle states none.
  const edition = meshEdition(readBundle(bundle).manifest.snapshot?.mesh_years ?? []);
  assert.equal(meshEditionOfBuild(), edition);
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
    // The vocabulary's credit: the source by name, the year the bundle states, and that NLM does not endorse the site.
    const credit = squash(made.querySelector(".mesh-credit").textContent);
    assert.ok(credit.includes(`courtesy of the U.S. National Library of Medicine: ${edition}.`), `${id}: ${credit}`);
    assert.match(credit, /Medical Subject Headings \(MeSH\), U\.S\. National Library of Medicine/);
    assert.match(credit, /NLM does not endorse this site\./);
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
    // Asked on a fresh host: on this one its not-found answer is kept for five minutes.
    assert.notEqual((await getFresh("/intervention/no-such-treatment")).status, 404, "the well-formed address reads the table");
  } finally {
    await db.prepare("ALTER TABLE pair_page_away RENAME TO pair_page").run();
  }
});

// The address space (openspec pairs-site task 4.6c): only a pair's or a listing's address reads
// D1; an address of theirs the version holds nothing for is answered 404 and kept five minutes;
// the query string is no part of an address.
test("an address no pair or listing could have is answered by the assets, with no read of D1, whatever its family", async () => {
  const db = await mf.getD1Database("PAIRS");
  await db.prepare("ALTER TABLE pair_page RENAME TO pair_page_away").run();
  try {
    for (const pathname of [
      "/Acoziborole--trypanosomiasis", "/acoziborole---x", "/acoziborole--", "/acoziborole",
      "/data/pairs/A--b.json", "/data/pairs/a--b.JSON", "/data/pairs/a--b",
      "/embed/acoziborole", "/embed/a--b/extra", "/oembed/a--b.xml", "/og/a--b.jpg", "/og/huge/a--b.png", "/og/square/A--b.png",
      `/a--${"b".repeat(400)}`, `/embed/a--${"b".repeat(400)}`,
    ]) {
      const response = await getFresh(pathname);
      assert.equal(response.status, 404, pathname);
      await response.body?.cancel();
    }
  } finally {
    await db.prepare("ALTER TABLE pair_page_away RENAME TO pair_page").run();
  }
});

test("a well-formed address the version holds nothing for answers 404, kept five minutes, and is not read again", async () => {
  const host = "https://missing.test";
  for (const pathname of ["/no-such--pair", "/data/pairs/no-such--pair.json", "/embed/no-such--pair", "/oembed/no-such--pair.json", "/og/no-such--pair.png", "/topic/no-such-topic"]) {
    const first = await mf.dispatchFetch(`${host}${pathname}`, { redirect: "manual" });
    assert.equal(first.status, 404, pathname);
    assert.equal(first.headers.get("Cache-Control"), "public, max-age=300", pathname);
    await first.body?.cancel();
  }
  // With the page table gone, the same addresses are answered from what was kept.
  const db = await mf.getD1Database("PAIRS");
  await db.prepare("ALTER TABLE pair_page RENAME TO pair_page_away").run();
  try {
    for (const pathname of ["/no-such--pair", "/embed/no-such--pair", "/topic/no-such-topic", "/no-such--pair?x=1"]) {
      const again = await mf.dispatchFetch(`${host}${pathname}`, { redirect: "manual" });
      assert.equal(again.status, 404, pathname);
      await again.body?.cancel();
    }
  } finally {
    await db.prepare("ALTER TABLE pair_page_away RENAME TO pair_page").run();
  }
});

test("a miss first asked for with HEAD keeps nothing bodiless: the GET after it has the not-found page", async () => {
  const host = "https://head-first.test";
  const head = await mf.dispatchFetch(`${host}/no-such--pair`, { method: "HEAD", redirect: "manual" });
  assert.equal(head.status, 404);
  await head.body?.cancel();
  const page = await mf.dispatchFetch(`${host}/no-such--pair`, { redirect: "manual" });
  assert.equal(page.status, 404);
  assert.match(await page.text(), /<title>[^<]+<\/title>/);
});

test("only a confirmed miss in D1 is kept: a page whose frame failed answers again once the frame is back", async () => {
  const host = "https://frame-back.test";
  // The embed's frame is missing for a moment, as in a deployment still reaching a location.
  hidden.add("/embed-shell");
  try {
    const failed = await mf.dispatchFetch(`${host}/embed/${ON_REQUEST}`, { redirect: "manual" });
    assert.equal(failed.status, 404);
    assert.notEqual(failed.headers.get("Cache-Control"), "public, max-age=300", "a failure is no miss");
    await failed.body?.cancel();
  } finally {
    hidden.delete("/embed-shell");
  }
  assert.equal((await mf.dispatchFetch(`${host}/embed/${ON_REQUEST}`, { redirect: "manual" })).status, 200);
});

test("the query string is no part of an address: the same page, kept once, its canonical address bare", async () => {
  const host = "https://query.test";
  const plain = await (await mf.dispatchFetch(`${host}/${ON_REQUEST}`)).text();
  const db = await mf.getD1Database("PAIRS");
  await db.prepare("ALTER TABLE pair_page RENAME TO pair_page_away").run();
  try {
    // Answered from what was kept for the bare address, with no read of D1.
    const asked = await mf.dispatchFetch(`${host}/${ON_REQUEST}?utm_source=x&ref=y`);
    assert.equal(asked.status, 200);
    const text = await asked.text();
    assert.equal(text, plain);
    assert.equal(parseHTML(text).document.querySelector('link[rel="canonical"]').getAttribute("href"), canonicalAddress(`/${ON_REQUEST}`));
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

test("every address a page made here names is the build's, read from its frame, whatever the Worker's own setting", async () => {
  // A deployment built for another address: the frame says so, and the Worker follows it.
  const built = new URL(canonicalAddress("/")).origin;
  frameEdits["/pair-shell"] = (text) => text.replaceAll(built, "https://records.example.org");
  try {
    const oembed = await (await getFresh(`/oembed/${ON_REQUEST}.json`)).json();
    assert.match(oembed.html, new RegExp(`https://records\\.example\\.org/embed/${ON_REQUEST}`));
    assert.equal(oembed.provider_url, "https://records.example.org/");
    const record = await (await getFresh(`/data/pairs/${ON_REQUEST}.json`)).text();
    assert.ok(record.includes("https://records.example.org") && !record.includes(built), "the record names the build's address only");
    const embed = await (await getFresh(`/embed/${ON_REQUEST}`)).text();
    assert.ok(embed.includes(`https://records.example.org/${ON_REQUEST}`));
  } finally {
    frameEdits["/pair-shell"] = (text) => text;
  }
});

test("a response made here carries the site's own headers, the ones public/_headers gives every file", async () => {
  // The "/*" rule of public/_headers, as Cloudflare reads it.
  const lines = fs.readFileSync("public/_headers", "utf8").split("\n");
  const at = lines.findIndex((line) => line.trim() === "/*");
  const rule = {};
  for (const line of lines.slice(at + 1)) {
    if (!/^\s+\S/.test(line)) break;
    const colon = line.indexOf(":");
    rule[line.slice(0, colon).trim()] = line.slice(colon + 1).trim();
  }
  assert.deepEqual(SITE_HEADERS, rule);
  for (const pathname of [`/${ON_REQUEST}`, `/data/pairs/${ON_REQUEST}.json`, `/embed/${ON_REQUEST}`, `/oembed/${ON_REQUEST}.json`, `/og/${ON_REQUEST}.png`, "/topic/infections"]) {
    const response = await getFresh(pathname);
    for (const [name, value] of Object.entries(rule)) assert.equal(response.headers.get(name), value, `${pathname} ${name}`);
    await response.body?.cancel();
  }
});

test("the saved forms of a pair's page and embed address lead to the bare address, keeping the query", async () => {
  for (const [saved, bare] of [
    [`/${ON_REQUEST}/`, `/${ON_REQUEST}`],
    [`/${ON_REQUEST}/index.html`, `/${ON_REQUEST}`],
    [`/${ON_REQUEST}.html`, `/${ON_REQUEST}`],
    [`/embed/${ON_REQUEST}/`, `/embed/${ON_REQUEST}`],
    [`/embed/${ON_REQUEST}.html`, `/embed/${ON_REQUEST}`],
    [`/embed/${ON_REQUEST}/index.html`, `/embed/${ON_REQUEST}`],
  ]) {
    const response = await get(`${saved}?from=saved`);
    assert.equal(response.status, 301, saved);
    assert.equal(new URL(response.headers.get("Location")).pathname + new URL(response.headers.get("Location")).search, `${bare}?from=saved`, saved);
  }
});

test("an embed kept for one embed frame is not answered for another with the same bundle", async () => {
  const before = await (await get(`/embed/${ON_REQUEST}`)).text();
  assert.ok(!before.includes("<!--another-embed-frame-->"));
  frameEdits["/embed-shell"] = (text) => text.replace("</body>", "<!--another-embed-frame--></body>");
  try {
    assert.ok((await (await get(`/embed/${ON_REQUEST}`)).text()).includes("<!--another-embed-frame-->"));
  } finally {
    frameEdits["/embed-shell"] = (text) => text;
  }
});

test("an embed whose file fails its check is refused in the embed's own frame, with its footer notices", async () => {
  // BROKEN's file was made to fail its check by an earlier test.
  const response = await getFresh(`/embed/${BROKEN}`);
  assert.equal(response.status, 500);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  const document = await documentOf(response);
  assert.equal(document.querySelector("[data-pair-unreadable]").textContent, UNREADABLE);
  assert.ok(document.querySelector("footer").textContent.includes("Data sources:"));
  assert.doesNotMatch(document.body.textContent, /APITEGROMAB/i);
});

// Entity tags (openspec pairs-site task 4.6e): from what a page is made of, kept across bundle
// versions while that is unchanged, so an asker who holds a page is told so (304).
/** The pair frame a real build of a bundle leaves: its version, its bundle's date and all. */
function builtFrame(folder) {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-next-build-"));
  const made = spawnSync("npx", ["astro", "build", "--outDir", out], { encoding: "utf8", env: { ...process.env, PAIRS_BUNDLE: folder, ASTRO_TELEMETRY_DISABLED: "1" } });
  assert.equal(made.status, 0, made.stdout.slice(-2000) + made.stderr.slice(-2000));
  const frame = fs.readFileSync(path.join(out, "pair-shell", "index.html"), "utf8");
  fs.rmSync(out, { recursive: true, force: true });
  return frame;
}

const ON_REQUEST_KINDS = () => [`/${ON_REQUEST}`, `/data/pairs/${ON_REQUEST}.json`, `/embed/${ON_REQUEST}`, `/oembed/${ON_REQUEST}.json`, `/og/${ON_REQUEST}.png`, "/intervention/acoziborole", "/topic/infections"];

test("every page made on request carries a weak tag, and asking with it answers 304 with no body", async () => {
  for (const pathname of ON_REQUEST_KINDS()) {
    const full = await getFresh(pathname);
    assert.equal(full.status, 200, pathname);
    const tag = full.headers.get("ETag");
    assert.match(tag, /^W\/"[0-9a-f]{24}"$/, pathname);
    await full.body?.cancel();
    const host = `https://tag-${(freshHosts += 1)}.test`;
    // Made again on a new host, from D1, and answered before it is written.
    const asked = await mf.dispatchFetch(`${host}${pathname}`, { headers: { "If-None-Match": tag }, redirect: "manual" });
    assert.equal(asked.status, 304, pathname);
    assert.equal(asked.headers.get("ETag"), tag);
    assert.equal(asked.headers.get("Cache-Control"), full.headers.get("Cache-Control"));
    assert.equal(await asked.text(), "");
    // A tag it does not hold, or none, gets the page.
    assert.equal((await mf.dispatchFetch(`${host}${pathname}`, { headers: { "If-None-Match": 'W/"0000"' } })).status, 200, pathname);
  }
});

test("a kept page answers 304 to an asker who holds it, with no read of D1", async () => {
  const host = "https://tag-kept.test";
  const full = await mf.dispatchFetch(`${host}/${ON_REQUEST}`);
  const tag = full.headers.get("ETag");
  await full.body?.cancel();
  const db = await mf.getD1Database("PAIRS");
  await db.prepare("ALTER TABLE pair_page RENAME TO pair_page_away").run();
  try {
    const asked = await mf.dispatchFetch(`${host}/${ON_REQUEST}`, { headers: { "If-None-Match": `"other", ${tag}` } });
    assert.equal(asked.status, 304);
    assert.equal(asked.headers.get("ETag"), tag);
  } finally {
    await db.prepare("ALTER TABLE pair_page_away RENAME TO pair_page").run();
  }
});

test("a page whose file is unchanged keeps its tag under a new bundle version; a changed one does not", async () => {
  const CHANGED = "tulisokibart--scleroderma-diffuse";
  const before = new Map();
  for (const pathname of [`/${ON_REQUEST}`, `/${CHANGED}`, `/data/pairs/${ON_REQUEST}.json`]) {
    const response = await getFresh(pathname);
    before.set(pathname, response.headers.get("ETag"));
    await response.body?.cancel();
  }
  // The next bundle: this test's own, with one pair's trial title changed and every other file
  // as it was. Loaded beside the versions the other tests read, none of them dropped.
  const next = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-next-"));
  fs.cpSync(bundle, next, { recursive: true });
  for (const folder of ["p12_pair_page", "p12_pair_data_file"]) {
    const file = path.join(next, folder, `${CHANGED}.json`);
    const held = JSON.parse(fs.readFileSync(file, "utf8"));
    (folder === "p12_pair_page" ? held : held.pair).trials[0].facts.title = "A retitled study";
    fs.writeFileSync(file, JSON.stringify(held));
  }
  fs.rmSync(path.join(next, "manifest.json"));
  writeManifest(next, { madeAt: "2026-11-21T00:00:00Z" });
  const db = await mf.getD1Database("PAIRS");
  for (const sql of statements(next, { keep: 10 }).sql) await db.prepare(sql).run();
  const version = statements(next).version;
  assert.notEqual(version, statements(bundle).version);
  // The frame of a real build of the next bundle: another version and another bundle date.
  const nextFrame = builtFrame(next);
  assert.match(nextFrame, new RegExp(`data-pair-version="${version}"`));
  frameEdits["/pair-shell"] = () => nextFrame;
  try {
    const kept = await getFresh(`/${ON_REQUEST}`);
    assert.equal(kept.headers.get("ETag"), before.get(`/${ON_REQUEST}`), "an unchanged pair keeps its tag");
    await kept.body?.cancel();
    const asked = await mf.dispatchFetch(`https://tag-next-${(freshHosts += 1)}.test/${ON_REQUEST}`, { headers: { "If-None-Match": before.get(`/${ON_REQUEST}`) } });
    assert.equal(asked.status, 304);
    const record = await getFresh(`/data/pairs/${ON_REQUEST}.json`);
    assert.equal(record.headers.get("ETag"), before.get(`/data/pairs/${ON_REQUEST}.json`), "an unchanged record keeps its tag");
    await record.body?.cancel();
    const changed = await getFresh(`/${CHANGED}`);
    assert.notEqual(changed.headers.get("ETag"), before.get(`/${CHANGED}`), "a changed pair has a new tag");
    assert.match(await changed.text(), /A retitled study/);
  } finally {
    frameEdits["/pair-shell"] = (text) => text;
  }
});

test("a pair added or removed elsewhere leaves a page's tag as it was, even one of the same treatment", async () => {
  // The narrowest acoziborole pair links no narrower pair: removing the broadest one, of the same
  // treatment, and an unrelated pair, changes nothing it shows, and so not its tag.
  const KEPT = "acoziborole--trypanosomiasis-african";
  const before = await getFresh(`/${KEPT}`);
  const tag = before.headers.get("ETag");
  await before.body?.cancel();
  const next = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-fewer-"));
  fs.cpSync(bundle, next, { recursive: true });
  for (const gone of ["acoziborole--infections", "tulisokibart--scleroderma-diffuse"]) {
    for (const folder of ["p12_pair_page", "p12_pair_data_file"]) fs.rmSync(path.join(next, folder, `${gone}.json`));
  }
  fs.rmSync(path.join(next, "manifest.json"));
  writeManifest(next, { madeAt: "2026-11-21T01:00:00Z" });
  const db = await mf.getD1Database("PAIRS");
  for (const sql of statements(next, { keep: 10 }).sql) await db.prepare(sql).run();
  const version = statements(next).version;
  // The frame of a real build of the next bundle: another version and another bundle date.
  const nextFrame = builtFrame(next);
  assert.match(nextFrame, new RegExp(`data-pair-version="${version}"`));
  frameEdits["/pair-shell"] = () => nextFrame;
  try {
    const after = await getFresh(`/${KEPT}`);
    assert.equal(after.headers.get("ETag"), tag);
    await after.body?.cancel();
    assert.equal((await mf.dispatchFetch(`https://tag-fewer-${(freshHosts += 1)}.test/${KEPT}`, { headers: { "If-None-Match": tag } })).status, 304);
    // The broadest pair is gone from this version.
    assert.equal((await getFresh("/acoziborole--infections")).status, 404);
  } finally {
    frameEdits["/pair-shell"] = (text) => text;
  }
});

test("a pair names the same treatment's pairs for narrower conditions", async () => {
  // acoziborole--infections (C01) and acoziborole--trypanosomiasis (C01.610…) from the small
  // bundle; the African form sits beneath both.
  const named = async (address) => [...(await documentOf(await get(`/${address}`))).querySelectorAll("[data-pair-narrower] [data-narrower]")].map((link) => link.dataset.narrower);
  assert.deepEqual(await named("acoziborole--infections"), ["acoziborole--trypanosomiasis", "acoziborole--trypanosomiasis-african"]);
  assert.deepEqual(await named("acoziborole--trypanosomiasis"), ["acoziborole--trypanosomiasis-african"]);
  // The narrowest has nothing beneath it, and says nothing.
  assert.deepEqual(await named("acoziborole--trypanosomiasis-african"), []);
  assert.ok(!(await (await get("/acoziborole--trypanosomiasis-african")).text()).includes("data-pair-narrower"));
});

test("an intervention page that fails its check stops a page made on request", async () => {
  const db = await mf.getD1Database("PAIRS");
  const version = statements(bundle).version;
  // Asked on a fresh host, so the page is made again rather than taken from the day's cache.
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'apitegromab' AND part > 0").bind(version).run();
  await db.prepare("UPDATE pair_page SET body = ?2 WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'apitegromab'").bind(version, JSON.stringify({ pairs: "not a list" })).run();
  const response = await getFresh("/apitegromab--obesity");
  assert.equal(response.status, 500);
  assert.equal(parseHTML(await response.text()).document.querySelector("[data-pair-unreadable]").textContent, UNREADABLE);
});

test("a narrower pair the version holds no page for is not linked, and a stored null is checked", async () => {
  const db = await mf.getD1Database("PAIRS");
  const version = statements(bundle).version;
  // A slice without the African form's page: its intervention listing still names it.
  await db.prepare("DELETE FROM pair WHERE version = ?1 AND address = 'acoziborole--trypanosomiasis-african'").bind(version).run();
  const made = await getFresh("/acoziborole--infections");
  assert.equal(made.status, 200);
  const named = [...parseHTML(await made.text()).document.querySelectorAll("[data-narrower]")].map((link) => link.dataset.narrower);
  assert.deepEqual(named, ["acoziborole--trypanosomiasis"]);
  // An intervention page file stored as JSON null is a body like any other, and fails its check.
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'tulisokibart' AND part > 0").bind(version).run();
  await db.prepare("UPDATE pair_page SET body = 'null' WHERE version = ?1 AND model = 'PairInterventionPage' AND key = 'tulisokibart'").bind(version).run();
  assert.equal((await getFresh("/tulisokibart--lung-diseases-interstitial")).status, 500);
});

test("the code that writes a page is in its tag: a renderer or wording change gives every page a new one", async () => {
  const before = await getFresh(`/${ON_REQUEST}`);
  const tag = before.headers.get("ETag");
  await before.body?.cancel();
  // The frame of a build whose renderer digest differs, as after a change to the site's wording.
  frameEdits["/pair-shell"] = (text) => text.replace(/data-renderer="[0-9a-f]+"/, 'data-renderer="000000000000000000000000"');
  try {
    const after = await getFresh(`/${ON_REQUEST}`);
    assert.notEqual(after.headers.get("ETag"), tag);
    await after.body?.cancel();
    const asked = await mf.dispatchFetch(`https://tag-renderer-${(freshHosts += 1)}.test/${ON_REQUEST}`, { headers: { "If-None-Match": tag } });
    assert.equal(asked.status, 200, "an outdated page is never called unchanged");
    await asked.body?.cancel();
  } finally {
    frameEdits["/pair-shell"] = (text) => text;
  }
});

// The rate limit on addresses made on request (openspec pairs-site task 4.6g), in a Worker of its
// own with a limit of three, so the other tests here are never counted.
/**
 * Asks `requests` of a fresh asker inside one window of the limiter: Miniflare counts in fixed
 * minutes of the clock, so a sequence that crosses one is asked again, from another address.
 */
async function inOneWindow(ask) {
  for (let attempt = 1; ; attempt += 1) {
    const window = Math.floor(Date.now() / 60_000);
    const answers = await ask(`192.0.2.${attempt}`);
    if (Math.floor(Date.now() / 60_000) === window) return answers;
    for (const answer of answers) await answer.body?.cancel();
    assert.ok(attempt < 3, "the limiter's window kept changing");
  }
}

test("past its limit an asker gets 429 with Retry-After and the site's headers, never 403 or 404, and files are never counted", async () => {
  const worker = await bundleWorker({ entryPoints: ["worker/with-pairs.mjs"], bundle: true, format: "esm", platform: "browser", conditions: ["workerd", "worker", "browser"], target: "es2022", write: false });
  const limited = new Miniflare(convertV4MiniflareOptions({
    modules: true,
    script: worker.outputFiles[0].text,
    compatibilityDate: "2026-10-01",
    cf: false,
    d1Databases: ["PAIRS"],
    ratelimits: { ON_REQUEST_LIMIT: { namespace_id: "9001", simple: { limit: 3, period: 60 } } },
    serviceBindings: { ASSETS: assets },
  }));
  try {
    const db = await limited.getD1Database("PAIRS");
    for (const sql of migration()) await db.prepare(sql).run();
    await load(db, bundle);
    const ask = (host, pathname, from) => limited.dispatchFetch(`https://${host}${pathname}`, { headers: { "CF-Connecting-IP": from }, redirect: "manual" });
    const [first, second, third, refused, elsewhere, otherHost, file] = await inOneWindow(async (from) => [
      await ask("limited.test", `/${ON_REQUEST}`, from),
      await ask("limited.test", `/${ON_REQUEST}`, from),
      await ask("limited.test", `/${ON_REQUEST}`, from),
      await ask("limited.test", "/intervention/acoziborole", from),
      await ask("limited.test", `/${ON_REQUEST}`, `${from}0`),
      await ask("other-preview.test", `/${ON_REQUEST}`, from),
      await ask("limited.test", "/about", from),
    ]);
    for (const [at, response] of [first, second, third].entries()) assert.equal(response.status, 200, `request ${at + 1}`);
    assert.equal(refused.status, 429);
    assert.equal(refused.headers.get("Retry-After"), "60");
    assert.equal(refused.headers.get("Cache-Control"), "no-store");
    // The site's headers, and the deployment's robots mark as its pages carry it (a preview's
    // noindex), on the refusal too.
    for (const [name, value] of Object.entries(SITE_HEADERS)) assert.equal(refused.headers.get(name), value, name);
    assert.ok(first.headers.get("X-Robots-Tag"), "the preview build marks its pages");
    assert.equal(refused.headers.get("X-Robots-Tag"), first.headers.get("X-Robots-Tag"));
    // Another address is counted on its own, and so is another preview's hostname; a file of
    // the site is never counted.
    assert.equal(elsewhere.status, 200);
    assert.equal(otherHost.status, 200);
    assert.equal(file.status, 200);
    for (const response of [first, second, third, refused, elsewhere, otherHost, file]) await response.body?.cancel();
  } finally {
    await limited.dispose();
  }
});

test("a fault of the limiter never takes a page down: a limit() that throws answers the page", async () => {
  const worker = await bundleWorker({ entryPoints: ["worker/with-pairs.mjs"], bundle: true, format: "esm", platform: "browser", conditions: ["workerd", "worker", "browser"], target: "es2022", write: false });
  const faulty = new Miniflare(convertV4MiniflareOptions({
    modules: [
      { type: "ESModule", path: "entry.mjs", contents: `import site from "./site.mjs";
export default { fetch(request, env, ctx) { return site.fetch(request, { ...env, ON_REQUEST_LIMIT: { limit() { throw new Error("limiter unavailable"); } } }, ctx); } };` },
      { type: "ESModule", path: "site.mjs", contents: worker.outputFiles[0].text },
    ],
    compatibilityDate: "2026-10-01",
    cf: false,
    d1Databases: ["PAIRS"],
    serviceBindings: { ASSETS: assets },
  }));
  try {
    const db = await faulty.getD1Database("PAIRS");
    for (const sql of migration()) await db.prepare(sql).run();
    await load(db, bundle);
    const response = await faulty.dispatchFetch(`https://faulty.test/${ON_REQUEST}`, { headers: { "CF-Connecting-IP": "192.0.2.9" } });
    assert.equal(response.status, 200);
    await response.body?.cancel();
  } finally {
    await faulty.dispose();
  }
});
