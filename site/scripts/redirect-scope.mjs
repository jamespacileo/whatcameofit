// Whether an old claim may lead to the pair it came from (scripts/redirects.mjs). A 301 says the
// claim's page now lives at the pair's: that holds only when the pair is about what the claim was.
// A claim about preventing a condition does not lead to a pair about the condition itself, whose
// trials are mostly of people who have it, until the operator has checked that very pair and
// listed the claim with it in data/redirect-scope.json (the operator, 2026-11-21: "keep the
// legacy claim until its same-scope pair is verified"). Until then the claim keeps its own page
// where one was kept, as a claim no pair came from does.
//
// Which claims are about prevention comes from what production recorded as each claim's
// indication (data/claim-scope.json), not from its address: "flu-vaccine-targeting-the-stable-
// stem-of-hemagglutinin" is for the prevention of influenza, and "brain-mri-surveillance-without-
// prophylactic-cranial" is about people who have small-cell lung cancer. Nor does the registry's
// "primary purpose" decide it: trontinemab's phase 3 trial in cognitively unimpaired people at
// risk (NCT07717411) is filed as treatment.
import fs from "node:fs";
import path from "node:path";

const DATA = path.resolve(import.meta.dirname, "../data");

/** The claims whose recorded indication is the prevention of a condition, by slug. */
export function preventionClaims(file = path.join(DATA, "claim-scope.json")) {
  return new Set(JSON.parse(fs.readFileSync(file, "utf8")).prevention.map((entry) => entry.slug));
}

/** The redirects the operator has verified, each a claim and the one pair checked for it, as
 * "<slug> <pair>": a claim verified for one pair is not thereby verified for another. */
export function verifiedRedirects(file = path.join(DATA, "redirect-scope.json")) {
  const listed = JSON.parse(fs.readFileSync(file, "utf8")).verified ?? [];
  for (const entry of listed) {
    if (!entry.slug || !entry.pair) throw new Error(`${file} lists a verified redirect without both its claim and its pair: ${JSON.stringify(entry)}`);
  }
  return new Set(listed.map((entry) => `${entry.slug} ${entry.pair}`));
}

/**
 * Why `claim` may not lead to the pair at `pair` yet, or null when it may: a claim about
 * prevention leads only to a pair the operator verified for it.
 * @param {{ prevention: Set<string>, verified: Set<string> }} scope
 */
export function heldRedirect(claim, pair, { prevention, verified }) {
  if (!prevention.has(claim)) return null;
  if (verified.has(`${claim} ${pair}`)) return null;
  return "a claim about preventing a condition, leading to a pair not verified as the same scope";
}
