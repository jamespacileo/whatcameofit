// Telling a treatment's name from a description, and splitting a combination.
// The same rules as the pipeline's thenwhat.extract.names; keep the two in step.

const OPENERS = new Set(
  `the a an this that these those new novel experimental investigational one-time daily weekly
  once-daily once-weekly non-surgical under-the-skin`.split(/\s+/),
);
const KINDS = new Set(
  `pill pills drug drugs treatment treatments therapy therapies procedure medicine medication jab
  jabs shot shots injection injections infusion vaccine vaccines implant implants device devices
  tablet tablets capsule spray gel cream surgery operation technique method approach compound
  molecule peptide antibody`.split(/\s+/),
);
const REGISTRY_NUMBER = /^NCT\d{8}$/i;
const COMBINED = /\s+(?:and|plus)\s+|\s*\+\s*/i;

/** Whether the text names a treatment: a brand, a code or a generic name. */
export function isAName(text) {
  const words = String(text ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0 || REGISTRY_NUMBER.test(words.join(" "))) return false;
  if (OPENERS.has(words[0].toLowerCase())) return false;
  const hasCode = words.some((word) => /\d/.test(word));
  const endsInAKind = words.length > 1 && KINDS.has(words.at(-1).toLowerCase());
  return hasCode || !endsInAKind;
}

/** The treatments joined in a name such as "A and B"; none for one treatment. */
export function partsOf(name) {
  const pieces = name.split(COMBINED).map((piece) => piece.trim()).filter(Boolean);
  return pieces.length > 1 ? pieces : [];
}

/** The form in which two names are compared. */
export function nameKey(name) {
  return String(name ?? "").toLowerCase().replace(/\s+/g, " ").trim();
}
