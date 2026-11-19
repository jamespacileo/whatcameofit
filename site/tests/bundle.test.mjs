// The lab's bundle of page files, read as the build reads it. tests/bundle is real: the
// pair pages the lab's own pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { cpSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { modelOf, movedAddresses, readBundle, unwordedPairCodes } from "../src/lib/bundle.ts";

const folder = fileURLToPath(new URL("./bundle", import.meta.url));
const address = "apitegromab--muscular-atrophy-spinal";

function copy(change) {
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
  cpSync(folder, dir, { recursive: true });
  const file = join(dir, "p12_pair_page", `${address}.json`);
  const page = JSON.parse(readFileSync(file, "utf8"));
  change(page);
  writeFileSync(file, JSON.stringify(page));
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
