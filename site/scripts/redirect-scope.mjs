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
//
// Beside prevention, the lab's scope rule (thenwhat-lab topics.t14_claim_scope) names claims whose
// pair is not of their scope for other reasons: an indication narrower than any condition code
// (HER2-low, KRAS G12C, a stage), trials of another purpose or age, a purpose not coded. Those
// are listed under `held` in data/redirect-scope.json (the release review, 2026-11-21) and keep
// their own pages too, unless verified for the exact pair they would lead to.
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

/** The claims the lab's scope rule holds from their pair, by slug, with its reason. */
export function heldClaims(file = path.join(DATA, "redirect-scope.json")) {
  const listed = JSON.parse(fs.readFileSync(file, "utf8")).held ?? [];
  for (const entry of listed) {
    if (!entry.slug || !entry.reason) throw new Error(`${file} lists a held claim without its slug and reason: ${JSON.stringify(entry)}`);
  }
  return new Map(listed.map((entry) => [entry.slug, entry.reason]));
}

/** What each reason of the lab's scope rule means, for the build log. */
const HELD_REASONS = {
  indication_not_a_mesh_term: "its indication is narrower than any condition code",
  claim_purposes_differ: "its trials and the pair's are of different purposes",
  purpose_not_coded: "its trials' purpose is not coded",
  pair_not_shown: "the pair is not shown yet",
  no_pair_for_the_indication: "no pair is of its indication",
};

/**
 * Why `claim` may not lead to the pair at `pair` yet, or null when it may: a claim about
 * prevention leads only to a pair the operator verified for it.
 * @param {{ prevention: Set<string>, verified: Set<string> }} scope
 */
export function heldRedirect(claim, pair, { prevention, verified, held = new Map() }) {
  if (verified.has(`${claim} ${pair}`)) return null;
  if (held.has(claim)) return `held by the scope rule: ${HELD_REASONS[held.get(claim)] ?? held.get(claim)}`;
  if (!prevention.has(claim)) return null;
  return "a claim about preventing a condition, leading to a pair not verified as the same scope";
}
