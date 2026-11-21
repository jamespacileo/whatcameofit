// What the addresses of the claims the site once tracked answer now: the list the Worker
// reads (dist/gone.json) and the renamed topics' redirect file. Runs scripts/redirects.mjs
// on its own against tests/bundle and the frozen list in data/retired-addresses.json.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";

const retired = JSON.parse(fs.readFileSync("data/retired-addresses.json", "utf8"));

function run(bundle = "tests/bundle", kept = "") {
  const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-redirects-"));
  const result = spawnSync("node", ["scripts/redirects.mjs"], {
    env: { ...process.env, PAIRS_BUNDLE: bundle, DIST_DIR: dist, KEPT_CLAIMS_DIR: kept },
    encoding: "utf8",
  });
  const goneFile = path.join(dist, "gone.json");
  const file = path.join(dist, "_redirects");
  const keptFile = path.join(dist, "kept-claims.json");
  return {
    result,
    dist,
    kept: fs.existsSync(keptFile) ? JSON.parse(fs.readFileSync(keptFile, "utf8")) : null,
    gone: fs.existsSync(goneFile) ? JSON.parse(fs.readFileSync(goneFile, "utf8")) : null,
    redirects: fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null,
  };
}

test("a claim one published pair came from leads to that pair, and every other claim address is gone", () => {
  const { result, gone } = run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const by = new Map(gone.map((entry) => [entry.slug, entry]));
  assert.deepEqual(by.get("ambroxol-parkinsons-disease-dementia"), { slug: "ambroxol-parkinsons-disease-dementia", to: "ambroxol--dementia" });
  // Every address the site once served is listed once, and none is left without an answer.
  assert.equal(new Set(gone.map((entry) => entry.slug)).size, gone.length);
  for (const slug of retired.pages) assert.ok(by.has(slug), slug);
  for (const entry of gone) assert.ok(entry.to || entry.on || entry.gone === true, entry.slug);
  // A claim with no pair in this bundle answers gone, with no date to give.
  assert.ok(gone.some((entry) => entry.gone === true));
});

test("a claim the operator archived stays gone, with the day it was taken down", () => {
  const { gone } = run();
  for (const { slug, on } of retired.archived) {
    assert.deepEqual(gone.find((entry) => entry.slug === slug), { slug, on });
  }
});

test("a claim merged into another goes where the claim it became goes", () => {
  const { gone } = run();
  const by = new Map(gone.map((entry) => [entry.slug, entry]));
  for (const { slug, to } of retired.moved) {
    const after = by.get(to);
    assert.deepEqual(by.get(slug), after.to ? { slug, to: after.to } : { slug, gone: true });
  }
});

// The three answers an old claim address has (the operator, 2026-11-21): a claim a published
// pair came from leads to it, one the operator archived stays gone, and every other keeps its
// page and files as production built them (scripts/kept-claims.mjs; tests/kept-claims holds two).
test("with kept claims, a matched claim leads to its pair, an archived one is gone, and an unmatched one keeps its files", () => {
  const KEPT = "10-person-living-donor-kidney-exchange-chain-kidney-failure";
  const { result, gone, kept, dist } = run("tests/bundle", "tests/kept-claims");
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const by = new Map(gone.map((entry) => [entry.slug, entry]));
  // Matched: still a 301 to the pair.
  assert.deepEqual(by.get("ambroxol-parkinsons-disease-dementia"), { slug: "ambroxol-parkinsons-disease-dementia", to: "ambroxol--dementia" });
  // Archived: still gone, with its day.
  for (const { slug, on } of retired.archived) assert.deepEqual(by.get(slug), { slug, on });
  // Unmatched and kept: not in the list the Worker answers from, and its eight files built,
  // byte for byte the frozen ones, with the style they load.
  assert.deepEqual(kept, [KEPT, "exagamglogene-autotemcel-sickle-cell-disease"].sort());
  assert.equal(by.has(KEPT), false);
  const manifest = JSON.parse(fs.readFileSync("tests/kept-claims/manifest.json", "utf8"));
  for (const file of [...manifest.claims[KEPT], ...manifest.shared]) {
    assert.deepEqual(fs.readFileSync(path.join(dist, file)), fs.readFileSync(path.join("tests/kept-claims/files", file)), file);
  }
  // A claim merged into a kept one leads to it.
  assert.deepEqual(by.get("crispr-edited-autologous-bone-marrow-cells-sickle-cell"), {
    slug: "crispr-edited-autologous-bone-marrow-cells-sickle-cell",
    to: "exagamglogene-autotemcel-sickle-cell-disease",
    kept: true,
  });
  // Unmatched and not among the kept (the tests hold two): gone, as before.
  assert.ok(gone.some((entry) => entry.gone === true));
  assert.match(result.stdout, /claims keep their pages \(17 files\), 11 archived stay gone/);
});

test("a kept file that is not the one frozen stops the build", () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-"));
  fs.cpSync("tests/kept-claims", folder, { recursive: true });
  fs.appendFileSync(path.join(folder, "files/data/claims/10-person-living-donor-kidney-exchange-chain-kidney-failure.json"), " ");
  const { result } = run("tests/bundle", folder);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /is not the file frozen/);
});

test("kept claims frozen from another commit stop the build", () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-"));
  fs.cpSync("tests/kept-claims", folder, { recursive: true });
  const file = path.join(folder, "manifest.json");
  fs.writeFileSync(file, JSON.stringify({ ...JSON.parse(fs.readFileSync(file, "utf8")), commit: "f".repeat(40) }));
  const { result } = run("tests/bundle", folder);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /was frozen from f{40}/);
});

test("a topic renamed while claims were tracked keeps its redirect", () => {
  const { redirects } = run();
  assert.match(redirects, /^\/topic\/dental-regeneration \/topic\/mouth-and-teeth 301$/m);
  assert.equal(redirects.trim().split("\n").length, retired.topics.length);
});

test("the build stops when a pair an old address leads to has no data file", () => {
  const bundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-redirects-bundle-"));
  fs.cpSync("tests/bundle", bundle, { recursive: true });
  const folder = fs.readdirSync(bundle).find((name) => name.endsWith("pair_data_file"));
  fs.rmSync(path.join(bundle, folder, "ambroxol--dementia.json"));
  writeManifest(bundle, { madeAt: "2026-11-20T00:00:00Z" });
  const { result, gone } = run(bundle);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ambroxol-parkinsons-disease-dementia leads to the pair ambroxol--dementia, which has no data file/);
  assert.equal(gone, null);
});

test("without a bundle nothing is written", () => {
  const { result, gone } = run("");
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /No bundle/);
  assert.equal(gone, null);
});
