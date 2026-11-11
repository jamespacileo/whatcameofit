// The open data file: the validated export, reduced to what the claim pages already show,
// with its licence, credit line, sources and method address inside. Pure: no files, no
// clock. Outlet icon images, article text and raw registry payloads are never in it.
import type { Export, ExportedClaim } from "./export";

/** The licence's name as LICENSE-DATA gives it. */
export const DATA_LICENCE = "Creative Commons Attribution 4.0 International (CC BY 4.0)";
export const DATA_LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/";

/** LICENSE-DATA asks for credit, a link to the licence and a note of any change. */
export function dataCredit(siteName: string, siteUrl: string): string {
  return `${siteName} (${siteUrl}), licensed under ${DATA_LICENCE}, ${DATA_LICENCE_URL}. Indicate if changes were made.`;
}

export interface OpenDataHeader {
  licence: string;
  credit: string;
  sources: { name: string; url: string }[];
  method: string;
  generated_at: string;
  last_checked_at: string | null;
  preview: boolean;
}

export interface OpenData extends OpenDataHeader {
  claims: Omit<ExportedClaim, "failure_flags">[];
}

export function openData(
  data: Export,
  licence: string,
  credit: string,
  method: string,
): OpenData {
  return {
    licence,
    credit,
    sources: data.sources.map(({ name, url }) => ({ name, url })),
    method,
    generated_at: data.generated_at,
    last_checked_at: data.last_checked_at,
    preview: data.preview === true,
    claims: data.claims.map((claim) => ({
      slug: claim.slug,
      headline: claim.headline,
      summary: claim.summary,
      vertical: claim.vertical,
      intervention: { name: claim.intervention.name, synonyms: [...claim.intervention.synonyms] },
      indication: claim.indication,
      first_reported_date: claim.first_reported_date,
      evidence_stage: claim.evidence_stage,
      status: {
        code: claim.status.code,
        overlay_years: claim.status.overlay_years,
        updated_at: claim.status.updated_at,
        explained_by: [...claim.status.explained_by],
      },
      articles: claim.articles.map((article) => ({
        outlet: article.outlet,
        title: article.title,
        published_date: article.published_date,
        url: article.url,
        archive_url: article.archive_url,
      })),
      promises: claim.promises.map((promise) => ({ ...promise })),
      // Every event field is shown on the claim page or needed to match status.explained_by.
      events: claim.events.map((event) => ({
        id: event.id,
        type: event.type,
        event_date: event.event_date,
        date_basis: event.date_basis,
        summary: event.summary,
        source_name: event.source_name,
        source_url: event.source_url,
        trial_id: event.trial_id,
        trial_phases: [...event.trial_phases],
        trial_state: event.trial_state,
        regulatory_outcome: event.regulatory_outcome,
      })),
      checked_by_person: claim.checked_by_person,
    })),
  };
}
