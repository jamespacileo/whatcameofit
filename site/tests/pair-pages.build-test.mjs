// The pair page and the pages that list pairs (openspec pairs-site, tasks 3.1 to 3.3), built
// from tests/bundle: real pair pages the lab's own pipeline test writes from its recorded
// slice. The bundle is the build's only input, and a build given none stops. A second build
// drops the ancestor pair the lab will stop making, to show the listings roll pairs up the
// MeSH tree themselves.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";
import { UNCHECKED_BYLINE } from "../src/lib/notices.ts";
import { narrowerPairs, pairView } from "../src/lib/pair-view.ts";
import { renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { embedTitle, renderEmbedArticle, renderEmbedRegistries } from "../src/lib/embed-render.ts";
import { STATUS_LABELS } from "../src/lib/status.ts";
import { SITE } from "../site.config.mjs";
// The released extension's own decision of what its popup shows, run on the built file.
import { stateFor } from "../../extension/src/lookup.js";

const withBundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-"));
const narrowest = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-narrowest-"));
// The bundle as the lab will cut it: a pair only at the most specific MeSH term, so no pair
// for acoziborole and "Infections" itself.
const ANCESTOR = "acoziborole--infections";
const narrowestBundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-narrowest-"));
// A pair filed under no topic, as lab pull request 119 writes one: tulisokibart for hidradenitis
// suppurativa, its page, data file and intervention page and the schemas copied unchanged from
// the lab's own page test on that branch (tests/pipelines/test_pages.py, its recorded slice).
const UNFILED = "tulisokibart--hidradenitis-suppurativa";
fs.cpSync("tests/bundle", narrowestBundle, { recursive: true });
for (const folder of ["p12_pair_page", "p12_pair_data_file"]) fs.rmSync(path.join(narrowestBundle, folder, `${ANCESTOR}.json`));
writeManifest(narrowestBundle, { madeAt: "2026-11-20T00:00:00Z" });
const pages = readBundle("tests/bundle").pages.PairPage;
// No file is built per pair (task 4.6): the Worker makes every pair's page with the shared
// renderer, and tests/pair-on-request.build-test.mjs holds its page to it. These tests read a
// pair's page as that renderer writes it.
const interventionFiles = readBundle("tests/bundle").pages.PairInterventionPage;
function pairDocument(address) {
  const file = pages[address];
  const view = pairView(file);
  const narrower = narrowerPairs(file, interventionFiles[file.row.intervention.slug] ?? null, new Set(Object.keys(pages)));
  return parseHTML(`<!doctype html><html><body>${renderPairBand(view)}${renderPairSheet(view, narrower)}</body></html>`).document;
}
function embedDocument(address) {
  const view = pairView(pages[address]);
  return parseHTML(`<!doctype html><html><body><article>${renderEmbedArticle(view, SITE.name, SITE.url)}<footer><p>${renderEmbedRegistries(view)}</p></footer></article></body></html>`).document;
}
const TWO_TRIALS = "acoziborole--infections";

function build(outDir, env = {}) {
  return spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: { ...process.env, ASTRO_TELEMETRY_DISABLED: "1", ...env },
    encoding: "utf8",
  });
}

function page(dir, address) {
  return parseHTML(fs.readFileSync(path.join(dir, address, "index.html"), "utf8")).document;
}

/** The pairs a lab listing file lists that the bundle has a page for, by address: a slice's
 * file can name pairs it left out, and a listing links only pages that answer. */
const filed = (file) => [...new Set(file.pairs.map((row) => row.pair.address))].filter((address) => address in pages).sort();

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
    [narrowest, { PAIRS_BUNDLE: narrowestBundle }],
  ]) {
    const result = build(dir, env);
    assert.equal(result.status, 0, result.stdout + result.stderr);
  }
});

test("no pair's page, record, card, embed or oEmbed file is built, and each pair's page names its pair", () => {
  for (const address of Object.keys(pages)) {
    for (const file of [address, `data/pairs/${address}.json`, `og/${address}.png`, `og/square/${address}.png`, `og/tall/${address}.png`, `embed/${address}`, `oembed/${address}.json`]) {
      assert.ok(!fs.existsSync(path.join(withBundle, file)), file);
    }
  }
  // The two frames the Worker fills are built.
  assert.ok(fs.existsSync(path.join(withBundle, "pair-shell", "index.html")));
  assert.ok(fs.existsSync(path.join(withBundle, "embed-shell", "index.html")));
  for (const [address, file] of Object.entries(pages)) {
    const document = pairDocument(address);
    assert.match(document.querySelector("h1").textContent, new RegExp(file.row.descriptor.label, "i"), address);
    assert.equal(document.querySelector("[data-pair-status]").dataset.pairStatus, file.row.status.code);
    assert.match(document.querySelector("[data-pair-status]").textContent, new RegExp(STATUS_LABELS[file.row.status.code]));
  }
});

test("a pair with two trials shows both, and lists the events that set its status", () => {
  const file = pages[TWO_TRIALS];
  assert.equal(file.trials.length, 2);
  const document = pairDocument(TWO_TRIALS);
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
  const checked = Object.entries(pages).filter(([, file]) => file.checked_by_person);
  const unchecked = Object.entries(pages).filter(([, file]) => !file.checked_by_person);
  assert.ok(checked.length > 0 && unchecked.length > 0);
  for (const [address] of unchecked) {
    assert.match(pairDocument(address).querySelector("[data-pair-unchecked]").textContent, new RegExp(UNCHECKED_BYLINE[1]));
  }
  for (const [address] of checked) assert.equal(pairDocument(address).querySelector("[data-pair-unchecked]"), null);
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

// A listing page is the lab's file for it, made on request by the Worker (decision 2 as chosen on
// 2026-11-20, task 4.6a); tests/pair-on-request.build-test.mjs holds what each lists.
test("no intervention, category or topic page is built: the Worker makes each", () => {
  const bundle = readBundle("tests/bundle");
  for (const slug of Object.keys(bundle.pages.PairInterventionPage)) assert.ok(!fs.existsSync(path.join(withBundle, "intervention", slug)), slug);
  for (const id of Object.keys(bundle.pages.PairClinicalCategoryPage)) assert.ok(!fs.existsSync(path.join(withBundle, "clinical", id)), id);
  for (const slug of Object.keys(bundle.pages.PairTopicPage)) assert.ok(!fs.existsSync(path.join(withBundle, "topic", slug)), slug);
});

test("with no pair at an ancestor term, no page is made for it or its condition", () => {
  assert.ok(!fs.existsSync(path.join(narrowest, ANCESTOR)));
  assert.ok(!fs.existsSync(path.join(narrowest, "condition", "infections")));
});

test("the topics page counts the pairs each topic's file lists, and the clinical index starts at the top categories", () => {
  const bundle = readBundle("tests/bundle");
  const document = page(withBundle, "topics");
  assert.ok(document.querySelector('[data-listing="topics"]'));
  // The count a topic's page lists: its file's pairs with a page; a topic listing none is left out.
  const counts = new Map(Object.entries(bundle.pages.PairTopicPage).map(([slug, file]) => [slug, filed(file).length]).filter(([, count]) => count > 0));
  const shown = [...document.querySelectorAll("[data-topic]")];
  assert.deepEqual(shown.map((item) => item.dataset.topic).sort(), [...counts.keys()].sort());
  for (const item of shown) {
    assert.equal(item.querySelector(".count").firstChild.textContent.trim(), String(counts.get(item.dataset.topic)));
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
  // The file's keys are a wire format: the released extension reads them under these names,
  // "claims" among them, from when the site tracked claims (extension/src/lookup.js).
  assert.deepEqual(Object.keys(lookup).sort(), ["articles", "claims", "generated_at", "last_checked", "live", "notices", "places", "preview", "schema_version", "topics"]);
  assert.deepEqual(Object.keys(lookup.claims).sort(), Object.keys(pages).sort());
  const entryKeys = ["first_reported", "headline", "indication", "latest_promise", "meaning", "names", "no_signal", "page", "place", "status", "terms", "topic", "unchecked"];
  for (const entry of Object.values(lookup.claims)) assert.deepEqual(Object.keys(entry).sort(), entryKeys);
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
  // The build writes no record: the Worker serves each from D1 (task 4.6), and
  // tests/pair-on-request.build-test.mjs holds each one to the lab's data file with the licence.
  for (const address of Object.keys(files)) assert.ok(!fs.existsSync(path.join(withBundle, "data", "pairs", `${address}.json`)), address);
});

test("the sitemap lists pair addresses and the pages that list pairs", () => {
  const locations = (dir) =>
    [...fs.readFileSync(path.join(dir, "sitemap.xml"), "utf8").matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => new URL(match[1]).pathname);
  const listed = new Set(locations(withBundle));
  for (const address of Object.keys(pages)) assert.ok(listed.has(`/${address}`), address);
  for (const file of Object.values(readBundle("tests/bundle").pages.PairInterventionPage)) {
    assert.ok(listed.has(`/intervention/${file.intervention.slug}`));
  }
});

test("the home page opens with the lookup box, then the latest changes, topics and treatments of pairs", () => {
  const document = page(withBundle, "");
  assert.ok(document.querySelector("#lookup-title"));
  const latest = [...document.querySelectorAll('[data-home="changes"] [data-pair]')].map((item) => item.dataset.pair);
  const changes = Object.values(pages).flatMap((file) => file.history.map((change) => ({ on: change.on, address: file.row.pair.address })));
  assert.equal(latest.length, Math.min(10, changes.length));
  for (const address of latest) assert.ok(pages[address], address);
  const topics = [...document.querySelectorAll('[data-home="topics"] [data-topic]')].map((item) => item.dataset.topic);
  // Each topic whose own file lists a pair with a page, as its page lists them.
  const listing = Object.entries(readBundle("tests/bundle").pages.PairTopicPage).filter(([, file]) => filed(file).length > 0).map(([slug]) => slug);
  assert.deepEqual(topics.sort(), listing.sort());
  const treatments = [...document.querySelectorAll('[data-home="treatments"] [data-intervention]')].map((item) => item.dataset.intervention);
  assert.deepEqual(treatments.sort(), [...new Set(Object.values(pages).map((file) => file.row.intervention.slug))].sort());
});

test("the search detail file gives each pair its trials, by the pair's address", () => {
  const detail = JSON.parse(fs.readFileSync(path.join(withBundle, "search-detail.json"), "utf8"));
  assert.deepEqual(Object.keys(detail.claims).sort(), Object.keys(pages).sort());
  for (const [address, file] of Object.entries(pages)) {
    assert.deepEqual(detail.claims[address].trials.map((trial) => trial.id), file.trials.map((trial) => trial.nct_id));
    assert.equal(detail.claims[address].reports.length, file.row.first_report ? 1 : 0);
  }
});

test("each pair's embed names its status, as the Worker makes it, and no card is drawn per pair", () => {
  for (const [address, file] of Object.entries(pages)) {
    const embed = embedDocument(address);
    assert.equal(embed.querySelector("[data-pair-status]").dataset.pairStatus, file.row.status.code);
    assert.match(embed.querySelector("[data-pair-status]").textContent, new RegExp(STATUS_LABELS[file.row.status.code]));
    assert.match(embed.querySelector("h1").textContent, new RegExp(embedTitle(pairView(file)).slice(0, 20).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  // The embed's frame is noindex and carries the footer notices; the Worker fills the rest.
  const frame = page(withBundle, "embed-shell");
  assert.equal(frame.querySelector('meta[name="robots"]').getAttribute("content"), "noindex");
  assert.ok(frame.body.innerHTML.includes("<!--embed-article-->") && frame.body.innerHTML.includes("<!--embed-registries-->"));
  // No picture is drawn per pair: the build's images are the site's own.
  assert.ok(!fs.existsSync(path.join(withBundle, "og")));
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
  const document = pairDocument("ambroxol--dementia");
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
  for (const address of Object.keys(pages)) {
    assert.doesNotMatch(pairDocument(address).body.textContent, /\bundefined\b|\bnull\b|NaN/, address);
    assert.doesNotMatch(embedDocument(address).body.textContent, /\bundefined\b|\bnull\b|NaN/, address);
  }
});

test("the bundle holds a trial with posted outcomes and comparisons", () => {
  // curcumin--gastritis-atrophic: trial NCT02782949, from the lab's rehearsal.
  // tests/pair-on-request.build-test.mjs checks its results on the page made on request.
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
  // The example record it names is one the index lists; the Worker serves it from D1.
  const example = [...data.querySelectorAll("a")].map((a) => a.getAttribute("href")).find((href) => href?.startsWith("/data/pairs/"));
  assert.ok(index.entries.some((entry) => entry.record === example), example);
});

test("the site has no It happened or Anniversaries page, and links neither", () => {
  // Launch scope (2026-11-20; openspec pairs-site tasks 5.6, 5.7): both listed claims by their
  // reports, which the bundle does not carry. Their addresses answer 404.
  const GONE = ["/it-happened", "/anniversaries", "/anniversaries.xml"];
  for (const file of ["it-happened/index.html", "anniversaries/index.html", "anniversaries.xml"]) {
    assert.ok(!fs.existsSync(path.join(withBundle, file)), file);
  }
  assert.ok(!fs.existsSync(path.join(withBundle, "rows", "on-this-day")));
  // No built page links to them.
  const linked = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith(".html")) {
        const html = fs.readFileSync(full, "utf8");
        for (const address of [...GONE, "/rows/on-this-day/"]) {
          if (html.includes(`href="${address}`)) linked.push(`${path.relative(withBundle, full)} links ${address}`);
        }
      }
    }
  };
  walk(withBundle);
  assert.deepEqual(linked, []);
  // Nor does the guide's entry on approval send a reader to the page by name.
  assert.doesNotMatch(page(withBundle, "guide/approved").body.textContent, /It happened/);
});

test("a pair filed under no topic still has its page, its condition's listing, search and the lookup file", () => {
  const file = pages[UNFILED];
  assert.equal(file.row.filing, null, "the lab wrote this pair with no topic");
  const document = pairDocument(UNFILED);
  assert.equal(document.querySelector("[data-pair-status]").dataset.pairStatus, file.row.status.code);
  assert.ok(listed(withBundle, `condition/${file.row.condition.slug}`).includes(UNFILED));
  // Not counted on the topics page; tests/pair-on-request.build-test.mjs holds that no topic's
  // page lists it.
  const counted = [...page(withBundle, "topics").querySelectorAll("[data-topic]")].reduce((sum, item) => sum + Number(item.querySelector(".count").firstChild.textContent), 0);
  assert.equal(counted, Object.values(readBundle("tests/bundle").pages.PairTopicPage).reduce((sum, file) => sum + filed(file).length, 0));
  assert.ok(Object.values(readBundle("tests/bundle").pages.PairTopicPage).every((file) => !filed(file).includes(UNFILED)));
  // Search and the lookup file hold it, with no topic.
  const lookup = JSON.parse(fs.readFileSync(path.join(withBundle, "lookup.json"), "utf8"));
  assert.equal(lookup.claims[UNFILED].page, `/${UNFILED}`);
  assert.equal(lookup.claims[UNFILED].topic, null);
  const detail = JSON.parse(fs.readFileSync(path.join(withBundle, "search-detail.json"), "utf8"));
  assert.deepEqual(detail.claims[UNFILED].trials.map((trial) => trial.id), file.trials.map((trial) => trial.nct_id));
  const sitemap = fs.readFileSync(path.join(withBundle, "sitemap.xml"), "utf8");
  assert.match(sitemap, new RegExp(`/${UNFILED}</loc>`));
});

test("a build given no bundle stops, saying what it needs", () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-none-"));
  const result = build(out, { PAIRS_BUNDLE: "" });
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /PAIRS_BUNDLE/);
});

test("no page, file or address of the build is a claim's", () => {
  for (const gone of ["data/claims.json", "data/claims", "rows", "year", "source", "outlet-icons"]) {
    assert.ok(!fs.existsSync(path.join(withBundle, gone)), gone);
  }
  assert.doesNotMatch(fs.readFileSync(path.join(withBundle, "sitemap.xml"), "utf8"), /claims/);
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
    // Pairs' pages and embeds, and listings, are the Worker's: checked below as it writes them,
    // and in tests/pair-on-request.build-test.mjs as it serves them.
    ...["condition", "clinical"].flatMap((folder) =>
      fs
        .readdirSync(path.join(withBundle, folder), { recursive: true })
        .filter((name) => name.endsWith("index.html"))
        .map((name) => path.join(folder, name)),
    ),
  ];
  const documents = [
    ...htmlPages.map((file) => [file, parseHTML(fs.readFileSync(path.join(withBundle, file), "utf8")).document]),
    ...Object.keys(pages).flatMap((address) => [[`/${address}`, pairDocument(address)], [`/embed/${address}`, embedDocument(address)]]),
  ];
  for (const [file, document] of documents) {
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
    // Under the small bundle's own manifest the changed file stops the build on the checksum,
    // before any page is written (task 2.3); with a manifest of its own, on the code.
    const stale = build(out, { PAIRS_BUNDLE: unworded });
    assert.notEqual(stale.status, 0);
    assert.match(stale.stdout + stale.stderr, /checksum sha256:[0-9a-f]{64} differs from the manifest's/);
    assert.equal(fs.readdirSync(out, { recursive: true }).some((name) => String(name).endsWith(".html")), false);
    writeManifest(unworded, { madeAt: "2026-11-20T00:00:00Z" });
    const result = build(out, { PAIRS_BUNDLE: unworded });
    assert.notEqual(result.status, 0);
    assert.match(result.stdout + result.stderr, /no words for: registry: ctis/);
  } finally {
    fs.rmSync(unworded, { recursive: true, force: true });
    fs.rmSync(out, { recursive: true, force: true });
  }
});
