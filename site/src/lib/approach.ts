// Words for the kind of intervention a claim reports. They name a kind of
// treatment only: never whether it works, or whether anyone can get it.

export const APPROACH_LABELS: Record<string, string> = {
  drug: "Drug",
  vaccine: "Vaccine",
  "gene-therapy": "Gene therapy",
  "cell-therapy": "Cell therapy",
  "tissue-regeneration": "Tissue regeneration",
  transplant: "Transplant",
  device: "Device",
  "surgery-or-procedure": "Surgery or procedure",
  "diet-or-lifestyle": "Diet or lifestyle",
};

/** Approach codes in the export that the site has no words for. */
export function unlabelledApproaches(codes: (string | null)[]): string[] {
  return [...new Set(codes)].filter(
    (code): code is string => code !== null && !(code in APPROACH_LABELS),
  );
}

// How the site names a registry's own type for an intervention, after "as". It says what
// the registry lists and nothing more.
export const REGISTRY_TYPE_PHRASES: Record<string, string> = {
  DRUG: "a drug",
  DEVICE: "a device",
  PROCEDURE: "a procedure",
  GENETIC: "a genetic intervention",
  DIETARY_SUPPLEMENT: "a dietary supplement",
};

/** Registry types in the export that the site has no words for. */
export function unwordedRegistryTypes(types: (string | null | undefined)[]): string[] {
  return [...new Set(types)].filter(
    (type): type is string => typeof type === "string" && !(type in REGISTRY_TYPE_PHRASES),
  );
}

/** What the registry lists the intervention as, in one plain sentence. */
export function approachBasisSentence(basis: { type: string; trials: number }): string {
  const trials = basis.trials === 1 ? "1 trial" : `${basis.trials} trials`;
  return `The registry lists it as ${REGISTRY_TYPE_PHRASES[basis.type]} in ${trials}.`;
}
