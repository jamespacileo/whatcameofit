// The comparison form of an article address, against the cases the pipeline's own
// address key is tested on (pipeline/tests/test_address_key.py). Both read one file,
// so the site and the pipeline cannot come to disagree about which addresses are one
// article. No build and no network.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { articleKey } from "../src/lib/article-key.mjs";

const cases = JSON.parse(
  readFileSync(new URL("./fixtures/article-key-cases.json", import.meta.url), "utf8"),
);

test("every shared form of one article gives its key", () => {
  for (const { key, addresses } of cases.same) {
    for (const address of addresses) assert.equal(articleKey(address), key, address);
  }
});

test("an address that is not a web page has no key", () => {
  for (const address of cases.none) assert.equal(articleKey(address), null, address);
});
