// The lab's bundle of page files, read as the build reads it. tests/bundle is real: the
// pair pages the lab's own pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { modelOf, movedAddresses, readBundle, unwordedPairCodes } from "../src/lib/bundle.ts";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";
import { pairView } from "../src/lib/pair-view.ts";
import { assertPairWordingNeutral, PAIR_WORDING, UNWORDED_TRIAL_STATES } from "../src/lib/pair-wording.ts";

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

// Task 2.4: the bundle's codes are worded by the site, keyed as the bundle's schema spells them.

test("every code the bundle's schemas allow has words, except the expanded access states", () => {
  const defs = JSON.parse(readFileSync(join(folder, "schemas", "PairPage.json"), "utf8")).$defs;
  const kinds = { ClaimStatusCode: ["status", "status gloss"], TrialPhase: ["phase"], OverallStatus: ["trial state"], TrialEventKind: ["event"], Approach: ["approach"] };
  for (const [def, tables] of Object.entries(kinds)) {
    for (const code of defs[def].enum) {
      if (def === "OverallStatus" && UNWORDED_TRIAL_STATES.includes(code)) continue;
      for (const table of tables) assert.ok(PAIR_WORDING[table][code], `${def} ${code} has no ${table} words`);
    }
  }
  // The states left without words are the schema's own, so none of them is worded by mistake.
  for (const code of UNWORDED_TRIAL_STATES) {
    assert.ok(defs.OverallStatus.enum.includes(code), code);
    assert.equal(PAIR_WORDING["trial state"][code], undefined, code);
  }
});

test("a kind of treatment spelled as the bundle spells it is worded", () => {
  // The claims export spells it "gene-therapy"; the bundle "gene_therapy".
  const dir = copy((page) => { page.approach = { ...page.approach, approach: "gene_therapy" }; });
  try {
    const page = readBundle(dir).pages.PairPage[address];
    assert.equal(pairView(page).approach, "Gene therapy");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a registry the site has no name for stops the read, named, and a known one is shown by name", () => {
  const known = copy((page) => { page.checked = [{ registry: "clinicaltrials.gov", checked_through: "2026-11-18" }]; });
  const unknown = copy((page) => { page.checked = [{ registry: "ctis", checked_through: "2026-11-18" }]; });
  try {
    assert.deepEqual(pairView(readBundle(known).pages.PairPage[address]).registryChecks, [
      { registry: "ClinicalTrials.gov", through: "2026-11-18" },
    ]);
    assert.throws(() => readBundle(unknown), /no words for: registry: ctis/);
  } finally {
    rmSync(known, { recursive: true, force: true });
    rmSync(unknown, { recursive: true, force: true });
  }
});

test("a code named like an object's own property has no words, and stops the read", () => {
  // The registry is free text in the schema; a name every object inherits is not a word of the site's.
  for (const registry of ["toString", "constructor", "__proto__"]) {
    const dir = copy((page) => { page.checked = [{ registry, checked_through: "2026-11-18" }]; });
    try {
      assert.throws(() => readBundle(dir), new RegExp(`no words for: registry: ${registry}`), registry);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }
});

test("the build's reader refuses to load when a table of words holds a verdict", () => {
  // The check runs when the wording module loads, and the build reads bundles through
  // bundle.ts, which imports it. Here a module hook gives the event table a verdict label as it
  // loads, and loading the reader must fail on it: removing the load-time check fails this test.
  const hook = `
    import { registerHooks } from "node:module";
    registerHooks({
      load(url, context, nextLoad) {
        const loaded = nextLoad(url, context);
        if (url.endsWith("/src/lib/pair-wording.ts")) {
          const source = String(loaded.source);
          if (!source.includes('terminated: "Trial terminated"')) throw new Error("the event table has moved: update this test");
          return { ...loaded, source: source.replace('terminated: "Trial terminated"', 'terminated: "Trial abandoned"') };
        }
        return loaded;
      },
    });
    await import(${JSON.stringify(new URL("../src/lib/bundle.ts", import.meta.url).href)});
  `;
  const run = spawnSync(process.execPath, ["--input-type=module", "-e", hook], { encoding: "utf8" });
  assert.notEqual(run.status, 0, "the reader loaded with a verdict in its words");
  assert.match(run.stderr, /Verdict wording "abandoned"/);
  assert.doesNotMatch(run.stderr, /event table has moved/);
});

test("verdict wording in any table of the pair path's words is refused", () => {
  assert.doesNotThrow(() => assertPairWordingNeutral(PAIR_WORDING));
  assert.throws(
    () => assertPairWordingNeutral({ ...PAIR_WORDING, event: { ...PAIR_WORDING.event, terminated: "Trial abandoned" } }),
    /Verdict wording "abandoned"/,
  );
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
