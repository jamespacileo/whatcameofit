// The pair page and the pages that list pairs (openspec pairs-site, tasks 3.1 and 3.2), built
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
import { STATUS_LABELS } from "../src/lib/status.ts";

const withBundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-"));
const without = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-off-"));
const narrowest = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-narrowest-"));
// The bundle as the lab will cut it: a pair only at the most specific MeSH term, so no pair
// for acoziborole and "Infections" itself.
const ANCESTOR = "acoziborole--infections";
const narrowestBundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-narrowest-"));
fs.cpSync("tests/bundle", narrowestBundle, { recursive: true });
for (const folder of ["p12_pair_page", "p12_pair_data_file"]) fs.rmSync(path.join(narrowestBundle, folder, `${ANCESTOR}.json`));
const pages = readBundle("tests/bundle").pages.PairPage;
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

test("every pair of the bundle has a page at its address, beside the claims site", () => {
  assert.ok(Object.keys(pages).length > 0);
  for (const [address, file] of Object.entries(pages)) {
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
  const checked = Object.entries(pages).filter(([, file]) => file.checked_by_person);
  const unchecked = Object.entries(pages).filter(([, file]) => !file.checked_by_person);
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
    const expected = Object.values(pages).filter((one) => one.row.filing.vertical === file.vertical.slug);
    assert.deepEqual(listed(withBundle, `topic/${file.vertical.slug}`), addresses(expected));
  }
  for (const file of Object.values(bundle.pages.PairClinicalCategoryPage)) {
    const expected = Object.values(pages).filter((one) => isBeneath(one, file.descriptor.tree_numbers));
    // The lab's own list for the category agrees with the site's roll-up.
    assert.deepEqual(addresses(expected), file.pairs.map((one) => one.pair.address).sort());
    assert.deepEqual(listed(withBundle, `clinical/${file.descriptor.descriptor_id}`), addresses(expected));
  }
});

test("with no pair at an ancestor term, the category and topic still list the pairs beneath it", () => {
  const beneath = ["acoziborole--trypanosomiasis", "acoziborole--trypanosomiasis-african"];
  assert.deepEqual(listed(narrowest, "clinical/D007239"), beneath);
  assert.deepEqual(listed(narrowest, "topic/infections"), beneath);
  assert.ok(!fs.existsSync(path.join(narrowest, ANCESTOR)));
  assert.ok(!fs.existsSync(path.join(narrowest, "condition", "infections")));
});

test("a build given no bundle makes no pair page, and keeps the claims' listings", () => {
  for (const address of Object.keys(pages)) assert.ok(!fs.existsSync(path.join(without, address)), address);
  assert.ok(fs.existsSync(path.join(without, "approved-claim", "index.html")));
  assert.ok(!fs.existsSync(path.join(without, "intervention")));
  assert.ok(!fs.existsSync(path.join(without, "condition")));
  assert.match(page(without, "topic/gum-disease").querySelector("h1").textContent, /gum/i);
  assert.equal(page(without, "topic/gum-disease").querySelector("[data-pair-table]"), null);
});
