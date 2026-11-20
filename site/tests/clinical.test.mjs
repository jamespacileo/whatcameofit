// The clinical credit's wording: pure, no build.
import assert from "node:assert/strict";
import { test } from "node:test";

import { meshEdition } from "../src/lib/clinical.ts";

test("the MeSH edition names every year the records were read from", () => {
  assert.equal(meshEdition(["2026"]), "MeSH 2026");
  assert.equal(meshEdition(["2026", "2027"]), "MeSH 2026 and 2027");
});
