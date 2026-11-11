// What the status card says, in one place: the image and its text alternative agree.
import type { ExportedClaim } from "./export";

export interface CardFact {
  label: string;
  value: string;
}

export function cardFacts(
  claim: ExportedClaim,
  statusLabel: string,
  latestPromiseDate: string | null,
): CardFact[] {
  const facts: CardFact[] = [];
  if (claim.first_reported_date) {
    facts.push({ label: "First reported", value: claim.first_reported_date.slice(0, 4) });
  }
  // A promise is shown as the year it names, never as a count of days: a count would
  // be wrong the day after the image was made.
  if (latestPromiseDate) facts.push({ label: "Promised by", value: latestPromiseDate.slice(0, 4) });
  facts.push({ label: "Status now", value: statusLabel });
  return facts;
}

export function cardAlt(claim: ExportedClaim, facts: CardFact[]): string {
  return `${claim.headline}. ${facts.map((fact) => `${fact.label} ${fact.value}`).join(". ")}.`;
}
