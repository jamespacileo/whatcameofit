import { forbiddenWord } from "./trial-page.mjs";

export const REGISTRY_CLAIM_WORDING = {
  headline: (intervention: string, indication: string) =>
    `Registered trials of ${intervention} for ${indication}`,
  summary: (intervention: string, indication: string) =>
    `Trial registries list studies of ${intervention} for ${indication}.`,
  report: "No news report is linked to this claim yet.",
};

const OFFERS_TREATMENT = /\b(?:get|ask|try|take|for you|safe to use)\b/i;

export function assertRegistryClaimWording(phrases: Record<string, string>): void {
  for (const [kind, phrase] of Object.entries(phrases)) {
    const found = forbiddenWord(phrase) ?? phrase.match(OFFERS_TREATMENT)?.[0];
    if (found) throw new Error(`Verdict or advice wording "${found}" in registry claim ${kind}: "${phrase}".`);
  }
}

// Validate the site's own templates before rendering. Registry labels are source data.
assertRegistryClaimWording({
  headline: REGISTRY_CLAIM_WORDING.headline("Example gel", "Example condition"),
  summary: REGISTRY_CLAIM_WORDING.summary("Example gel", "Example condition"),
  report: REGISTRY_CLAIM_WORDING.report,
});
