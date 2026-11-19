// The pair page (openspec pairs-site, task 3.1), built from tests/bundle: real pair pages the
// lab's own pipeline test writes from its recorded slice. The claims site is built beside it
// from tests/fixture-export.json, and a build given no bundle makes no pair page.
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

before(() => {
  for (const [dir, env] of [[withBundle, { PAIRS_BUNDLE: "tests/bundle" }], [without, { PAIRS_BUNDLE: "" }]]) {
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

test("a build given no bundle makes no pair page", () => {
  for (const address of Object.keys(pages)) assert.ok(!fs.existsSync(path.join(without, address)), address);
  assert.ok(fs.existsSync(path.join(without, "approved-claim", "index.html")));
});
