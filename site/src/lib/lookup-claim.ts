// A claim as the lookup file words it, which is how the browser extension's popup
// says it. The lookup file and the extension page's drawn popup both read it here, so
// the page can never show an answer the extension would word differently.
import type { ExportedClaim } from "./export";
import { UNCHECKED_NOTE } from "./notices.ts";
import {
  STAGE_PATH,
  STATUS_LABELS,
  STATUS_MEANINGS,
  latestPromise,
  overlayText,
} from "./status.ts";
import { formatDate } from "./timetable.ts";

export function lookupClaim(claim: ExportedClaim) {
  const promise = latestPromise(claim);
  return {
    headline: claim.headline,
    page: `/${claim.slug}`,
    status: STATUS_LABELS[claim.status.code],
    meaning: STATUS_MEANINGS[claim.status.code],
    // The status's place on the path from preclinical to approved, counted from 1, or
    // null for a status that is off the path. A position, never a score.
    place: STAGE_PATH.indexOf(claim.status.code) + 1 || null,
    no_signal: overlayText(claim.status.overlay_years),
    first_reported: claim.first_reported_date ? formatDate(claim.first_reported_date) : null,
    latest_promise: promise
      ? `${promise.description} (by ${promise.parsed_date!.slice(0, 4)})`
      : null,
    unchecked: claim.checked_by_person ? null : UNCHECKED_NOTE,
    // For offering close matches to an address that is not tracked: the treatment's
    // names, then the condition and the titles of the reports.
    names: [claim.intervention.name, ...claim.intervention.synonyms],
    terms: [claim.indication, ...claim.articles.map((article) => article.title)].join(" "),
  };
}

export type LookupClaim = ReturnType<typeof lookupClaim>;
