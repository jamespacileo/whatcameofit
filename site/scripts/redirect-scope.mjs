// Whether an old claim may lead to the pair it came from (scripts/redirects.mjs). A 301 says the
// claim's page now lives at the pair's: that holds only when the pair is about what the claim was.
// A claim scoped to preventing a condition does not lead to a pair about the condition itself,
// whose trials are mostly of people who have it, until the operator has checked that pair is of
// the same scope and listed the claim in data/redirect-scope.json (the operator, 2026-11-21:
// "keep the legacy claim until its same-scope pair is verified"). Until then the claim keeps its
// own page where one was kept, as a claim no pair came from does.
//
// The registry's own "primary purpose" cannot decide it: trontinemab's phase 3 trial in
// cognitively unimpaired people at risk is filed as treatment. The claim's own address names its
// scope, so the address decides.
import fs from "node:fs";
import path from "node:path";

/** A claim or pair address that names prevention as its scope. */
export const PREVENTION = /(?:^|-)(?:prevent|prevents|prevention|preventing|preventive|prophylaxis|prophylactic)(?:-|$)/;

/** The claims whose same-scope pair the operator has checked, by slug. */
export function verifiedRedirects(file = path.resolve(import.meta.dirname, "../data/redirect-scope.json")) {
  const listed = JSON.parse(fs.readFileSync(file, "utf8")).verified ?? [];
  return new Set(listed.map((entry) => entry.slug));
}

/**
 * Why `claim` may not lead to the pair at `pair` yet, or null when it may: a claim scoped to
 * prevention leads only to a pair whose address names the same scope, or one the operator verified.
 */
export function heldRedirect(claim, pair, verified = new Set()) {
  if (verified.has(claim)) return null;
  if (PREVENTION.test(claim) && !PREVENTION.test(pair)) return "a claim about preventing a condition, leading to a pair about the condition";
  return null;
}
