// The home page's lists: the same published claims, put in the orders a reader comes
// back for. Each order is a fact of the record (a date, a count of years); none ranks
// or grades a claim, and none depends on the day the page is read.
import type { ExportedClaim } from "./export";
import { allChanges, type StatusChange } from "./changes.ts";
import { latestPromise } from "./status.ts";

/** Changes from one status to another, newest first. A claim's first status is not a change. */
export function statusMoves(claims: ExportedClaim[]): StatusChange[] {
  return allChanges(claims).filter((change) => change.before !== null);
}

/** Claims with a dated promise, earliest promised date first; on one date, by headline. */
export function promisesByDate(claims: ExportedClaim[]): ExportedClaim[] {
  const due = (claim: ExportedClaim) => latestPromise(claim)!.parsed_date!;
  return claims
    .filter((claim) => latestPromise(claim) !== null)
    .sort((a, b) => due(a).localeCompare(due(b)) || a.headline.localeCompare(b.headline));
}

/** Claims carrying the no-signal overlay, most years first; then the earliest report first. */
export function longestWithoutSignal(claims: ExportedClaim[]): ExportedClaim[] {
  return claims
    .filter((claim) => (claim.status.overlay_years ?? 0) > 0)
    .sort(
      (a, b) =>
        b.status.overlay_years! - a.status.overlay_years! ||
        (a.first_reported_date ?? "").localeCompare(b.first_reported_date ?? "") ||
        a.headline.localeCompare(b.headline),
    );
}
