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
import { heldRedirect, preventionClaims, verifiedRedirects } from "../scripts/redirect-scope.mjs";

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
  assert.match(result.stdout, /claims keep their pages \(17 files, 2 in search\), 11 archived stay gone/);
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

// The operator's report of 2026-11-21: /alzheimers-prevention-trontinemab led to
// /trontinemab--alzheimer-disease, whose trials are mostly of people with the disease. A claim
// about preventing a condition keeps its page until a pair of the same scope is verified.
test("a claim about preventing a condition does not lead to a pair about the condition itself", () => {
  const bundle = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-scope-bundle-"));
  fs.cpSync("tests/bundle", bundle, { recursive: true });
  const claim = "alzheimers-prevention-trontinemab";
  assert.ok(retired.pages.includes(claim), "the claim is one the site served");
  // The fixture's dementia pair, made to say it came from the prevention claim.
  const file = path.join(bundle, "p12_pair_page", "ambroxol--dementia.json");
  const page = JSON.parse(fs.readFileSync(file, "utf8"));
  page.row.origin = { ...page.row.origin, claim_slug: claim };
  fs.writeFileSync(file, JSON.stringify(page));
  fs.rmSync(path.join(bundle, "manifest.json"));
  writeManifest(bundle, { madeAt: "2026-11-21T00:00:00Z" });
  const { result, gone, dist } = run(bundle);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const entry = gone.find((one) => one.slug === claim);
  assert.equal(entry?.to, undefined, "no redirect to a pair of another scope");
  assert.equal(entry?.gone, true, "with no kept page in this run, it answers gone rather than lead elsewhere");
  assert.match(result.stdout, /Held: \/alzheimers-prevention-trontinemab does not lead to \/ambroxol--dementia/);
  // Written for the staging smoke check, which holds the claim to its own page.
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dist, "held-redirects.json"), "utf8")), [{ slug: claim, pair: "ambroxol--dementia" }]);
  fs.rmSync(bundle, { recursive: true, force: true });
});

test("a prevention claim leads only to the pair the operator verified for it, never another", () => {
  const prevention = preventionClaims();
  const none = { prevention, verified: new Set() };
  assert.match(heldRedirect("alzheimers-prevention-trontinemab", "trontinemab--alzheimer-disease", none), /preventing a condition/);
  assert.match(heldRedirect("gantenerumab-prevention-of-early-onset-alzheimers-disease", "gantenerumab--alzheimer-disease", none), /preventing a condition/);
  // Approval binds the claim to destination A; destination B, as a later bundle might give, stays held.
  const verified = { prevention, verified: new Set(["alzheimers-prevention-trontinemab trontinemab--alzheimer-disease-prevention"]) };
  assert.equal(heldRedirect("alzheimers-prevention-trontinemab", "trontinemab--alzheimer-disease-prevention", verified), null);
  assert.match(heldRedirect("alzheimers-prevention-trontinemab", "trontinemab--alzheimer-disease", verified), /preventing a condition/);
  // Scope is what production recorded as each claim's indication, not words in its address.
  assert.ok(prevention.has("flu-vaccine-targeting-the-stable-stem-of-hemagglutinin"), "for the prevention of influenza");
  assert.equal(heldRedirect("brain-mri-surveillance-without-prophylactic-cranial", "x--small-cell-lung-carcinoma", none), null);
  assert.equal(heldRedirect("ambroxol-parkinsons-disease-dementia", "ambroxol--dementia", none), null);
  // Every claim listed is one the site served.
  for (const slug of prevention) assert.ok(retired.pages.includes(slug), slug);
});

test("a verified redirect names both its claim and its pair", () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-scope-")), "redirect-scope.json");
  fs.writeFileSync(file, JSON.stringify({ verified: [{ slug: "alzheimers-prevention-trontinemab" }] }));
  assert.throws(() => verifiedRedirects(file), /without both its claim and its pair/);
  fs.writeFileSync(file, JSON.stringify({ verified: [{ slug: "a-claim", pair: "x--y" }] }));
  assert.deepEqual([...verifiedRedirects(file)], ["a-claim x--y"]);
});
