import assert from "node:assert/strict";
import { test } from "node:test";
import { assertRegistryClaimWording, REGISTRY_CLAIM_WORDING } from "../src/lib/registry-claim-wording.ts";

test("registry wording identifies what the registry lists and whether a report is linked", () => {
  assert.equal(REGISTRY_CLAIM_WORDING.headline("X", "Y"), "Registered trials of X for Y");
  assert.equal(REGISTRY_CLAIM_WORDING.summary("X", "Y"), "Trial registries list studies of X for Y.");
  assert.equal(REGISTRY_CLAIM_WORDING.report, "No news report is linked to this claim yet.");
});

test("registry claim templates reject verdicts and offers of treatment", () => {
  assert.throws(() => assertRegistryClaimWording({ headline: "A promising treatment" }), /promising.*headline/);
  assert.throws(() => assertRegistryClaimWording({ summary: "You can ask for X" }), /ask.*summary/);
  assert.throws(() => assertRegistryClaimWording({ headline: "Get X today" }), /Get.*headline/);
});
