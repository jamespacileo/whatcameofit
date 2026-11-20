// The lab's bundle of page files, read as the build reads it. tests/bundle is real: the
// pair pages the lab's own pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { cpSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { modelOf, movedAddresses, readBundle, unwordedPairCodes } from "../src/lib/bundle.ts";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";

const folder = fileURLToPath(new URL("./bundle", import.meta.url));
const address = "apitegromab--muscular-atrophy-spinal";

function copy(change) {
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
  cpSync(folder, dir, { recursive: true });
  const file = join(dir, "p12_pair_page", `${address}.json`);
  const page = JSON.parse(readFileSync(file, "utf8"));
  change(page);
  writeFileSync(file, JSON.stringify(page));
  // A changed copy gets its own manifest, so each test below reaches the check it is about.
  writeManifest(dir, { madeAt: "2026-11-20T00:00:00Z" });
  return dir;
}

test("every page file of the bundle fits its schema and is read under its page model", () => {
  const bundle = readBundle(folder);
  assert.deepEqual(bundle.withoutSchema, []);
  for (const name of readdirSync(folder).filter((entry) => entry.startsWith("p12_"))) {
    assert.equal(Object.keys(bundle.pages[modelOf(name)]).length, readdirSync(join(folder, name)).length, name);
  }
  const page = bundle.pages.PairPage[address];
  assert.equal(page.row.pair.address, address);
  assert.equal(page.row.intervention.preferred_name, "APITEGROMAB");
  assert.ok(page.trials.length > 0);
});

test("a file that does not fit its schema stops the read, named", () => {
  const dir = copy((page) => { delete page.row.status; });
  try {
    assert.throws(() => readBundle(dir), new RegExp(`p12_pair_page/${address}\\.json does not fit PairPage`));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a code the site has no words for stops the read, named", () => {
  const pages = Object.values(readBundle(folder).pages.PairPage);
  assert.deepEqual(unwordedPairCodes(pages), []);
  // A state the registry gives only to expanded access records: the schema knows it, the site does not word it.
  const dir = copy((page) => { page.trials[0].facts.overall_status = "withheld"; });
  try {
    assert.throws(() => readBundle(dir), /no words for: trial state: withheld/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a claim's address goes to its pair's only when one pair came from it", () => {
  const pages = Object.values(readBundle(folder).pages.PairPage);
  const moved = movedAddresses(pages);
  const bySlug = Map.groupBy(pages.filter((page) => page.row.origin), (page) => page.row.origin.claim_slug);
  for (const [slug, from] of bySlug) {
    if (from.length === 1 && slug !== from[0].row.pair.address) assert.equal(moved[slug], from[0].row.pair.address);
    else assert.equal(moved[slug], undefined, slug);
  }
  assert.ok(bySlug.size > 0);
});

// The manifest (openspec pairs-site, task 2.3): its counts and checksum are checked before any
// page is read, so a build stops before it writes one.
function copyAsIs(change) {
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
  cpSync(folder, dir, { recursive: true });
  change(dir);
  return dir;
}

test("the bundle's manifest states its version, checksum and counts, and the read gives them", () => {
  const bundle = readBundle(folder);
  assert.equal(bundle.version, "230ee727aab2d32c");
  assert.equal(bundle.manifest.checksum.slice("sha256:".length, "sha256:".length + 16), bundle.version);
  for (const [model, pages] of Object.entries(bundle.pages)) assert.equal(bundle.manifest.counts[model], Object.keys(pages).length, model);
});

test("a file missing from what the manifest counts stops the read, naming the page model and both counts", () => {
  const dir = copyAsIs((at) => rmSync(join(at, "p12_pair_page", `${address}.json`)));
  try {
    assert.throws(() => readBundle(dir), /the manifest counts 12 PairPage files and 11 are present/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a file changed after the manifest was made stops the read on the checksum", () => {
  const dir = copyAsIs((at) => {
    const file = join(at, "p12_pair_page", `${address}.json`);
    const page = JSON.parse(readFileSync(file, "utf8"));
    page.row.intervention.preferred_name = "SOMETHING ELSE";
    writeFileSync(file, JSON.stringify(page));
  });
  try {
    assert.throws(() => readBundle(dir), /checksum sha256:[0-9a-f]{64} differs from the manifest's sha256:230ee727/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a folder with no manifest, or one without an offset on its time, is refused", () => {
  const none = copyAsIs((at) => rmSync(join(at, "manifest.json")));
  const local = copyAsIs((at) => {
    const manifest = JSON.parse(readFileSync(join(at, "manifest.json"), "utf8"));
    writeFileSync(join(at, "manifest.json"), JSON.stringify({ ...manifest, made_at: "2026-11-20T12:00:00" }));
  });
  try {
    assert.throws(() => readBundle(none), /holds no manifest\.json/);
    assert.throws(() => readBundle(local), /no valid made_at/);
  } finally {
    rmSync(none, { recursive: true, force: true });
    rmSync(local, { recursive: true, force: true });
  }
});
