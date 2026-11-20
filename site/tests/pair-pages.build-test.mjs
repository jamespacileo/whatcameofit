// The pair page and the pages that list pairs (openspec pairs-site, tasks 3.1 to 3.3), built
// from tests/bundle: real pair pages the lab's own pipeline test writes from its recorded
// slice. The claims site is built beside it from tests/fixture-export.json, and a build given
// no bundle makes no pair page. A third build drops the ancestor pair the lab will stop
// making, to show the listings roll pairs up the MeSH tree themselves.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { UNCHECKED_BYLINE } from "../src/lib/notices.ts";
import { builtAhead } from "../src/lib/pair-view.ts";
import { STATUS_LABELS } from "../src/lib/status.ts";
import { SITE } from "../site.config.mjs";
// The released extension's own decision of what its popup shows, run on the built file.
import { stateFor } from "../../extension/src/lookup.js";

const withBundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-"));
const without = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-off-"));
const narrowest = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-narrowest-"));
// The bundle as the lab will cut it: a pair only at the most specific MeSH term, so no pair
// for acoziborole and "Infections" itself.
const ANCESTOR = "acoziborole--infections";
const narrowestBundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-narrowest-"));
// A pair filed under no topic, as lab pull request 119 writes one: tulisokibart for hidradenitis
// suppurativa, its page, data file and intervention page and the schemas copied unchanged from
// the lab's own page test on that branch (tests/pipelines/test_pages.py, its recorded slice).
const UNFILED = "tulisokibart--hidradenitis-suppurativa";
// Pairs added to the bundle after its listing files were cut: the lab's own category lists
// predate them, so the site's roll-up is held to those lists without them.
const ADDED_AFTER_CUT = new Set([UNFILED]);
fs.cpSync("tests/bundle", narrowestBundle, { recursive: true });
for (const folder of ["p12_pair_page", "p12_pair_data_file"]) fs.rmSync(path.join(narrowestBundle, folder, `${ANCESTOR}.json`));
const pages = readBundle("tests/bundle").pages.PairPage;
// The pairs whose page, card and embed the build makes (decision 2); the rest are made on
// request by the Worker (tests/pair-on-request.build-test.mjs).
const built = Object.fromEntries(Object.entries(pages).filter(([, file]) => builtAhead(file)));
const TWO_TRIALS = "acoziborole--infections";

function build(outDir, env = {}) {
  return spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: { ...process.env, EXPORT_FILE: "tests/fixture-export.json", ASTRO_TELEMETRY_DISABLED: "1", ...env },
    encoding: "utf8",
  });
}

function page(dir, address) {
  return parseHTML(fs.readFileSync(path.join(dir, address, "index.html"), "utf8")).document;
}

/** The pairs a listing page lists, by address. */
function listed(dir, address) {
  return [...page(dir, address).querySelectorAll("[data-pair]")].map((row) => row.dataset.pair).sort();
}

const isBeneath = (file, tops) =>
  file.row.descriptor.tree_numbers.some((number) => tops.some((top) => number === top || number.startsWith(`${top}.`)));
const addresses = (files) => files.map((file) => file.row.pair.address).sort();

before(() => {
  for (const [dir, env] of [
    [withBundle, { PAIRS_BUNDLE: "tests/bundle" }],
    [without, { PAIRS_BUNDLE: "" }],
    [narrowest, { PAIRS_BUNDLE: narrowestBundle }],
  ]) {
    const result = build(dir, env);
    assert.equal(result.status, 0, result.stdout + result.stderr);
  }
});

test("every pair built ahead has a page at its address, beside the claims site", () => {
  assert.ok(Object.keys(built).length > 0);
  for (const address of Object.keys(pages)) assert.equal(fs.existsSync(path.join(withBundle, address)), address in built, address);
  for (const [address, file] of Object.entries(built)) {
    const document = page(withBundle, address);
    assert.match(document.querySelector("h1").textContent, new RegExp(file.row.descriptor.label, "i"), address);
    assert.equal(document.querySelector("[data-pair-status]").dataset.pairStatus, file.row.status.code);
    assert.match(document.querySelector("[data-pair-status]").textContent, new RegExp(STATUS_LABELS[file.row.status.code]));
  }
  // The claims site is still built in full.
  assert.ok(fs.existsSync(path.join(withBundle, "approved-claim", "index.html")));
});

test("a pair with two trials shows both, and lists the events that set its status", () => {
  const file = pages[TWO_TRIALS];
  assert.equal(file.trials.length, 2);
  const document = page(withBundle, TWO_TRIALS);
  const trials = [...document.querySelectorAll("[data-trial]")].map((element) => element.dataset.trial);
  assert.deepEqual(trials.sort(), file.trials.map((trial) => trial.nct_id).sort());
  for (const trial of file.trials) {
    assert.ok(document.querySelector(`a[href="https://clinicaltrials.gov/study/${trial.nct_id}"]`), trial.nct_id);
  }
  const explained = [...document.querySelectorAll("[data-pair-explained] [data-event]")].map((item) => item.dataset.event);
  assert.deepEqual([...explained].sort(), [...file.row.status.explained_by].sort());
  const days = explained.map((key) => key.split("|")[2]);
  assert.deepEqual(days, [...days].sort(), "oldest first");
  assert.equal(document.querySelectorAll("[data-pair-history] li").length, file.history.length);
});

test("a pair no person checked says so, and one a person checked does not", () => {
  const checked = Object.entries(built).filter(([, file]) => file.checked_by_person);
  const unchecked = Object.entries(built).filter(([, file]) => !file.checked_by_person);
  assert.ok(checked.length > 0 && unchecked.length > 0);
  for (const [address] of unchecked) {
    assert.match(page(withBundle, address).querySelector("[data-pair-unchecked]").textContent, new RegExp(UNCHECKED_BYLINE[1]));
  }
  for (const [address] of checked) assert.equal(page(withBundle, address).querySelector("[data-pair-unchecked]"), null);
});

test("a condition's page lists every pair for it or a condition beneath it, each with its status", () => {
  const conditions = new Map(Object.values(pages).map((file) => [file.row.condition.slug, file.row.descriptor]));
  for (const [slug, descriptor] of conditions) {
    const expected = Object.values(pages).filter((file) => isBeneath(file, descriptor.tree_numbers));
    assert.deepEqual(listed(withBundle, `condition/${slug}`), addresses(expected), slug);
    const document = page(withBundle, `condition/${slug}`);
    for (const file of expected) {
      const row = document.querySelector(`[data-pair="${file.row.pair.address}"]`);
      assert.match(row.textContent, new RegExp(STATUS_LABELS[file.row.status.code]));
      assert.ok(row.querySelector(`a[href="/${file.row.pair.address}"]`));
    }
  }
});

test("an intervention's page lists every pair for it", () => {
  for (const file of Object.values(readBundle("tests/bundle").pages.PairInterventionPage)) {
    const expected = Object.values(pages).filter((one) => one.row.intervention.id === file.intervention.id);
    assert.ok(expected.length > 0);
    assert.deepEqual(listed(withBundle, `intervention/${file.intervention.slug}`), addresses(expected));
  }
});

test("a topic's page lists the pairs filed under it, and a category's the pairs at or beneath it", () => {
  const bundle = readBundle("tests/bundle");
  for (const file of Object.values(bundle.pages.PairTopicPage)) {
    const expected = Object.values(pages).filter((one) => one.row.filing?.vertical === file.vertical.slug);
    assert.deepEqual(listed(withBundle, `topic/${file.vertical.slug}`), addresses(expected));
  }
  for (const file of Object.values(bundle.pages.PairClinicalCategoryPage)) {
    const expected = Object.values(pages).filter((one) => isBeneath(one, file.descriptor.tree_numbers));
    // The lab's own list for the category agrees with the site's roll-up.
    assert.deepEqual(addresses(expected).filter((address) => !ADDED_AFTER_CUT.has(address)), file.pairs.map((one) => one.pair.address).sort());
    assert.deepEqual(listed(withBundle, `clinical/${file.descriptor.descriptor_id}`), addresses(expected));
  }
});

test("with no pair at an ancestor term, the category and topic still list the pairs beneath it", () => {
  const beneath = ["acoziborole--trypanosomiasis", "acoziborole--trypanosomiasis-african"];
  // The category also lists any other pair beneath C01, filed or not.
  const underInfections = Object.values(pages).filter((file) => file.row.pair.address !== ANCESTOR && isBeneath(file, ["C01"]));
  assert.deepEqual(listed(narrowest, "clinical/D007239"), addresses(underInfections));
  assert.ok(beneath.every((address) => listed(narrowest, "clinical/D007239").includes(address)));
  assert.deepEqual(listed(narrowest, "topic/infections"), beneath);
  assert.ok(!fs.existsSync(path.join(narrowest, ANCESTOR)));
  assert.ok(!fs.existsSync(path.join(narrowest, "condition", "infections")));
});

test("the topics page counts the pairs filed under each topic, and the clinical index starts at the top categories", () => {
  const bundle = readBundle("tests/bundle");
  const document = page(withBundle, "topics");
  assert.ok(document.querySelector('[data-listing="topics"]'));
  const counts = Map.groupBy(Object.values(pages).filter((file) => file.row.filing), (file) => file.row.filing.vertical);
  const shown = [...document.querySelectorAll("[data-topic]")];
  assert.deepEqual(shown.map((item) => item.dataset.topic).sort(), [...counts.keys()].sort());
  for (const item of shown) {
    assert.equal(item.querySelector(".count").firstChild.textContent.trim(), String(counts.get(item.dataset.topic).length));
  }
  const categories = Object.values(bundle.pages.PairClinicalCategoryPage);
  const known = new Set(categories.map((file) => file.descriptor.descriptor_id));
  const tops = categories
    .filter((file) => !file.broader.some((one) => known.has(one.descriptor_id)))
    .map((file) => file.descriptor.descriptor_id);
  const listedTops = [...page(withBundle, "clinical").querySelectorAll("[data-category]")].map((item) => item.dataset.category);
  assert.deepEqual(listedTops.sort(), tops.sort());
});

test("the changes feed has an entry for each change in each pair's history, linking the pair", () => {
  const xml = fs.readFileSync(path.join(withBundle, "changes.xml"), "utf8");
  const links = [...xml.matchAll(/<entry>[\s\S]*?<link href="([^"]+)"\/>/g)].map((match) => new URL(match[1]).pathname.slice(1));
  const expected = Object.values(pages).flatMap((file) => file.history.map(() => file.row.pair.address));
  assert.deepEqual(links.sort(), expected.sort());
  for (const file of Object.values(pages)) {
    for (const change of file.history) assert.ok(xml.includes(STATUS_LABELS[change.after]), change.after);
  }
});

test("the lookup file lists every pair by its address, in the shape the released extension reads", () => {
  const lookup = JSON.parse(fs.readFileSync(path.join(withBundle, "lookup.json"), "utf8"));
  const claimsLookup = JSON.parse(fs.readFileSync(path.join(without, "lookup.json"), "utf8"));
  assert.deepEqual(Object.keys(lookup).sort(), Object.keys(claimsLookup).sort());
  assert.deepEqual(Object.keys(lookup.claims).sort(), Object.keys(pages).sort());
  const claimKeys = Object.keys(Object.values(claimsLookup.claims)[0]).sort();
  for (const entry of Object.values(lookup.claims)) assert.deepEqual(Object.keys(entry).sort(), claimKeys);
  const site = new URL(SITE.url).host;
  for (const [address, file] of Object.entries(pages)) {
    const state = stateFor(`${site}/${address}`, { index: lookup, savedAt: null }, site);
    assert.equal(state.kind, "tracked", address);
    assert.deepEqual(state.claims.map((entry) => entry.page), [`/${address}`]);
    assert.equal(state.claims[0].status, STATUS_LABELS[file.row.status.code]);
    assert.equal(state.claims[0].unchecked === null, file.checked_by_person, address);
  }
  // A page of the site that is no pair's, and an article no pair came from.
  assert.equal(stateFor(`${site}/how-it-works`, { index: lookup, savedAt: null }, site).kind, "no-page");
  assert.equal(stateFor("news.example.org/story", { index: lookup, savedAt: null }, site).kind, "untracked");
});

test("each pair's open data record is the lab's data file as written, with the licence", () => {
  const files = readBundle("tests/bundle").pages.PairDataFile;
  const index = JSON.parse(fs.readFileSync(path.join(withBundle, "data", "pairs.json"), "utf8"));
  assert.deepEqual(index.entries.map((entry) => entry.address), Object.keys(files).sort());
  // The build writes the record of a pair it builds ahead; the Worker serves the rest from D1
  // (task 1.3, tests/pair-on-request.build-test.mjs).
  for (const [address, file] of Object.entries(files)) {
    const written = path.join(withBundle, "data", "pairs", `${address}.json`);
    assert.equal(fs.existsSync(written), builtAhead(pages[address]), address);
    if (!builtAhead(pages[address])) continue;
    const record = JSON.parse(fs.readFileSync(written, "utf8"));
    assert.equal(record.format, "pair-record");
    assert.match(record.licence, /CC BY 4\.0/);
    assert.deepEqual(record.pair, file.pair);
  }
  assert.ok(!fs.existsSync(path.join(without, "data", "pairs")));
});

test("the sitemap lists pair addresses and the pages that list pairs, and no claim's page", () => {
  const locations = (dir) =>
    [...fs.readFileSync(path.join(dir, "sitemap.xml"), "utf8").matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => new URL(match[1]).pathname);
  const listed = new Set(locations(withBundle));
  for (const address of Object.keys(pages)) assert.ok(listed.has(`/${address}`), address);
  for (const file of Object.values(readBundle("tests/bundle").pages.PairInterventionPage)) {
    assert.ok(listed.has(`/intervention/${file.intervention.slug}`));
  }
  assert.ok(!listed.has("/approved-claim"));
  assert.ok(locations(without).includes("/approved-claim"));
  for (const address of Object.keys(pages)) assert.ok(!locations(without).includes(`/${address}`));
});

test("the home page opens with the lookup box, then the latest changes, topics and treatments of pairs", () => {
  const document = page(withBundle, "");
  assert.ok(document.querySelector("#lookup-title"));
  const latest = [...document.querySelectorAll('[data-home="changes"] [data-pair]')].map((item) => item.dataset.pair);
  const changes = Object.values(pages).flatMap((file) => file.history.map((change) => ({ on: change.on, address: file.row.pair.address })));
  assert.equal(latest.length, Math.min(10, changes.length));
  for (const address of latest) assert.ok(pages[address], address);
  const topics = [...document.querySelectorAll('[data-home="topics"] [data-topic]')].map((item) => item.dataset.topic);
  assert.deepEqual(topics.sort(), [...new Set(Object.values(pages).filter((file) => file.row.filing).map((file) => file.row.filing.vertical))].sort());
  const treatments = [...document.querySelectorAll('[data-home="treatments"] [data-intervention]')].map((item) => item.dataset.intervention);
  assert.deepEqual(treatments.sort(), [...new Set(Object.values(pages).map((file) => file.row.intervention.slug))].sort());
  // The claims home is left out whole, with its scripts.
  assert.equal(page(without, "").querySelector("[data-home]"), null);
  assert.ok(fs.readFileSync(path.join(without, "index.html"), "utf8").length > fs.readFileSync(path.join(withBundle, "index.html"), "utf8").length);
});

test("the search detail file gives each pair its trials, by the pair's address", () => {
  const detail = JSON.parse(fs.readFileSync(path.join(withBundle, "search-detail.json"), "utf8"));
  assert.deepEqual(Object.keys(detail.claims).sort(), Object.keys(pages).sort());
  for (const [address, file] of Object.entries(pages)) {
    assert.deepEqual(detail.claims[address].trials.map((trial) => trial.id), file.trials.map((trial) => trial.nct_id));
    assert.equal(detail.claims[address].reports.length, file.row.first_report ? 1 : 0);
  }
  const claimsDetail = JSON.parse(fs.readFileSync(path.join(without, "search-detail.json"), "utf8"));
  for (const address of Object.keys(pages)) assert.equal(claimsDetail.claims[address], undefined);
});

test("each pair built ahead has its cards and embed, and its page names them", () => {
  const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47]);
  const sizes = { "": [1200, 630], "square/": [1080, 1080], "tall/": [1080, 1350] };
  for (const [address, file] of Object.entries(built)) {
    for (const [folder] of Object.entries(sizes)) {
      const image = fs.readFileSync(path.join(withBundle, "og", `${folder}${address}.png`));
      assert.ok(image.subarray(0, 4).equals(PNG), `${folder}${address}`);
    }
    const wide = fs.readFileSync(path.join(withBundle, "og", `${address}.png`));
    assert.deepEqual([wide.readUInt32BE(16), wide.readUInt32BE(20)], sizes[""]);
    const embed = page(withBundle, `embed/${address}`);
    assert.equal(embed.querySelector('meta[name="robots"]').getAttribute("content"), "noindex");
    assert.equal(embed.querySelector("[data-pair-status]").dataset.pairStatus, file.row.status.code);
    assert.match(embed.querySelector("[data-pair-status]").textContent, new RegExp(STATUS_LABELS[file.row.status.code]));
    const oembed = JSON.parse(fs.readFileSync(path.join(withBundle, "oembed", `${address}.json`), "utf8"));
    assert.match(oembed.html, new RegExp(`/embed/${address}"`));
    assert.match(oembed.thumbnail_url, new RegExp(`/og/${address}\\.png$`));
    const document = page(withBundle, address);
    assert.match(document.querySelector('meta[property="og:image"]').getAttribute("content"), new RegExp(`/og/${address}\\.png`));
    assert.match(document.querySelector('meta[property="og:image:alt"]').getAttribute("content"), /Not medical advice/);
    assert.match(document.querySelector('link[type="application/json+oembed"]').getAttribute("href"), new RegExp(`/oembed/${address}\\.json$`));
  }
  for (const address of Object.keys(pages)) {
    assert.ok(!fs.existsSync(path.join(without, "og", `${address}.png`)), address);
    assert.ok(!fs.existsSync(path.join(without, "embed", address)), address);
  }
});

test("a build that reads a bundle writes the validators and types of its page models", () => {
  const code = fs.readFileSync(".bundle-code/validators.mjs", "utf8");
  for (const name of fs.readdirSync("tests/bundle/schemas")) {
    const model = name.slice(0, -".json".length);
    assert.match(code, new RegExp(`validate${model}`), model);
    assert.ok(fs.existsSync(path.join(".bundle-code", "types", `${model}.d.ts`)), model);
  }
});

test("every page of a build that reads a bundle carries the footer notices the build check asks for", () => {
  // The check `pnpm run build` runs after Astro; a pull request's preview stops on it.
  const check = spawnSync(process.execPath, ["scripts/check-dist.mjs"], { env: { ...process.env, DIST_DIR: withBundle }, encoding: "utf8" });
  assert.equal(check.status, 0, check.stdout + check.stderr);
});

test("a trial's papers are linked by their identifiers, and nothing of a paper's text is shown", () => {
  // ambroxol--dementia: trial NCT02914366 and its two papers, from the lab's rehearsal.
  const file = pages["ambroxol--dementia"];
  const trial = file.trials.find((one) => one.paper_ids.length > 0);
  assert.ok(trial, "the bundle holds a trial with papers");
  const document = page(withBundle, "ambroxol--dementia");
  const links = [...document.querySelectorAll(`[data-trial="${trial.nct_id}"] [data-paper]`)];
  assert.deepEqual(links.map((link) => link.dataset.paper), trial.paper_ids);
  for (const link of links) {
    assert.equal(link.getAttribute("href"), `https://doi.org/${link.dataset.paper}`);
    assert.equal(link.textContent, `doi:${link.dataset.paper}`);
  }
  // Its start is given to the month only, and is shown so, with no day made up.
  assert.equal(trial.facts.start.day, "2015-11");
  assert.match(document.querySelector(`[data-trial="${trial.nct_id}"]`).textContent, /Started\s*Nov 2015/);
});

test("no pair page shows a value it could not read", () => {
  for (const address of Object.keys(built)) {
    assert.doesNotMatch(page(withBundle, address).body.textContent, /\bundefined\b|\bnull\b|NaN/, address);
  }
});

test("the bundle holds a trial with posted outcomes and comparisons", () => {
  // curcumin--gastritis-atrophic: trial NCT02782949, from the lab's rehearsal. It is made on
  // request here (one trial, no claim origin); tests/pair-on-request.build-test.mjs builds it
  // ahead too and checks its results on the built page and on the page made on request.
  const curcumin = pages["curcumin--gastritis-atrophic"].trials[0].findings;
  assert.ok(curcumin.outcomes.length > 0 && curcumin.comparisons.length > 0);
});

test("the footer's Data page describes the pairs' files and its link opens the pairs' index", () => {
  // Followed as a reader would: the footer's link, then the page's own download link.
  const footer = page(withBundle, "").querySelector('footer a[href="/data"]');
  assert.ok(footer, "the footer links the Data page");
  const data = page(withBundle, "data");
  assert.doesNotMatch(data.body.textContent, /claims\.json/);
  const link = data.querySelector('a[data-open-data="pairs"]');
  const index = JSON.parse(fs.readFileSync(path.join(withBundle, link.getAttribute("href")), "utf8"));
  assert.equal(index.format, "pairs-index");
  assert.equal(index.entries.length, Object.keys(pages).length);
  assert.equal(Number(data.querySelector("[data-pair-count]").dataset.pairCount), index.entries.length);
  assert.match(data.querySelector("[data-pair-count]").textContent, new RegExp(`${index.entries.length} treatments and conditions`));
  // The example record it names is a file of the build.
  const example = [...data.querySelectorAll("a")].map((a) => a.getAttribute("href")).find((href) => href?.startsWith("/data/pairs/"));
  assert.ok(fs.existsSync(path.join(withBundle, example)), example);
  // Without a bundle the page is the claims' as before.
  assert.ok(page(without, "data").querySelector('a[href="/data/claims.json"]'));
});

test("a pair filed under no topic still has its page, and is reached from every list but a topic's", () => {
  const file = pages[UNFILED];
  assert.equal(file.row.filing, null, "the lab wrote this pair with no topic");
  assert.ok(builtAhead(file), "the unfiled pair is one built ahead, so its page is a file of the build");
  const document = page(withBundle, UNFILED);
  assert.equal(document.querySelector("[data-pair-status]").dataset.pairStatus, file.row.status.code);
  assert.ok(listed(withBundle, `intervention/${file.row.intervention.slug}`).includes(UNFILED));
  assert.ok(listed(withBundle, `condition/${file.row.condition.slug}`).includes(UNFILED));
  // On no topic's page, and not counted on the topics page.
  for (const name of fs.readdirSync(path.join(withBundle, "topic"))) assert.ok(!listed(withBundle, `topic/${name}`).includes(UNFILED), name);
  const counted = [...page(withBundle, "topics").querySelectorAll("[data-topic]")].reduce((sum, item) => sum + Number(item.querySelector(".count").firstChild.textContent), 0);
  assert.equal(counted, Object.values(pages).filter((one) => one.row.filing).length);
  // Search and the lookup file hold it, with no topic.
  const lookup = JSON.parse(fs.readFileSync(path.join(withBundle, "lookup.json"), "utf8"));
  assert.equal(lookup.claims[UNFILED].page, `/${UNFILED}`);
  assert.equal(lookup.claims[UNFILED].topic, null);
  const detail = JSON.parse(fs.readFileSync(path.join(withBundle, "search-detail.json"), "utf8"));
  assert.deepEqual(detail.claims[UNFILED].trials.map((trial) => trial.id), file.trials.map((trial) => trial.nct_id));
  const sitemap = fs.readFileSync(path.join(withBundle, "sitemap.xml"), "utf8");
  assert.match(sitemap, new RegExp(`/${UNFILED}</loc>`));
});

test("a build given no bundle makes no pair page, and keeps the claims' listings", () => {
  for (const address of Object.keys(pages)) assert.ok(!fs.existsSync(path.join(without, address)), address);
  assert.ok(fs.existsSync(path.join(without, "approved-claim", "index.html")));
  assert.ok(!fs.existsSync(path.join(without, "intervention")));
  assert.ok(!fs.existsSync(path.join(without, "condition")));
  assert.match(page(without, "topic/gum-disease").querySelector("h1").textContent, /gum/i);
  assert.equal(page(without, "topic/gum-disease").querySelector("[data-pair-table]"), null);
  assert.equal(page(without, "topics").querySelector("[data-listing]"), null);
  assert.equal(page(without, "clinical").querySelector("[data-listing]"), null);
  const feed = fs.readFileSync(path.join(without, "changes.xml"), "utf8");
  for (const address of Object.keys(pages)) assert.ok(!feed.includes(`/${address}"`), address);
});

// Task 2.4: the bundle carries codes and the site words them. No code reaches a reader as a
// word: not a status, state, phase, event, kind of treatment or registry, nor an
// intervention's key.
test("no page built from the bundle shows one of its codes where its words belong", () => {
  const codes = new Set();
  for (const file of fs.readdirSync("tests/bundle/schemas")) {
    JSON.stringify(JSON.parse(fs.readFileSync(path.join("tests/bundle/schemas", file), "utf8")), (key, value) => {
      // Codes of one word ("drug", "completed") are ordinary words too; those with an
      // underscore are codes only.
      if (key === "enum") for (const code of value) if (typeof code === "string" && code.includes("_")) codes.add(code);
      return value;
    });
  }
  for (const file of Object.values(pages)) codes.add(file.row.intervention.id);
  assert.ok(codes.has("phase_2") && codes.has("results_posted") && codes.has("gene_therapy"));
  const htmlPages = [
    "index.html",
    ...Object.keys(built).flatMap((address) => [`${address}/index.html`, `embed/${address}/index.html`]),
    ...["intervention", "condition", "topic", "clinical"].flatMap((folder) =>
      fs
        .readdirSync(path.join(withBundle, folder), { recursive: true })
        .filter((name) => name.endsWith("index.html"))
        .map((name) => path.join(folder, name)),
    ),
  ];
  assert.ok(htmlPages.length > Object.keys(built).length * 2);
  for (const file of htmlPages) {
    const { document } = parseHTML(fs.readFileSync(path.join(withBundle, file), "utf8"));
    for (const element of document.querySelectorAll("script, style, template")) element.remove();
    const text = document.body.textContent;
    for (const code of codes) assert.ok(!text.includes(code), `${file} shows the code ${code}`);
  }
});

test("a bundle carrying a code with no words stops the build, naming the code", () => {
  const unworded = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-unworded-"));
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-unworded-"));
  try {
    fs.cpSync("tests/bundle", unworded, { recursive: true });
    const file = path.join(unworded, "p12_pair_page", `${TWO_TRIALS}.json`);
    const doctored = JSON.parse(fs.readFileSync(file, "utf8"));
    doctored.checked = [{ registry: "ctis", checked_through: "2026-11-18" }];
    fs.writeFileSync(file, JSON.stringify(doctored));
    const result = build(out, { PAIRS_BUNDLE: unworded });
    assert.notEqual(result.status, 0);
    assert.match(result.stdout + result.stderr, /no words for: registry: ctis/);
  } finally {
    fs.rmSync(unworded, { recursive: true, force: true });
    fs.rmSync(out, { recursive: true, force: true });
  }
});
