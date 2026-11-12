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
