// The open data file: the validated export, reduced to what the claim pages already show,
// with its licence, credit line, sources and method address inside. Pure: no files, no
// clock. Outlet icon images, article text and raw registry payloads are never in it.
import type { ExportedCard } from "./background";
import type { Export, ExportedClaim, ExportedTrialFacts } from "./export";

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
  /** The sources of the background cards in the file, each with the credit it asks for. */
  card_sources: { name: string; title: string; credit: string; licence: string; url: string }[];
  /** Sources whose cards the claim pages show and this file leaves out, and why. */
  left_out: { source: string; licence: string; reason: string }[];
}

/** A background card as the file holds it: never the definition's source text altered. */
export type OpenCard = Omit<ExportedCard, "decided_by">;

export interface OpenData extends OpenDataHeader {
  claims: (Omit<ExportedClaim, "failure_flags" | "background"> & { background: OpenCard[] })[];
}

/** Why a source's cards are not in the file. */
export function leftOutReason(licence: string): string {
  return `Its licence (${licence}) does not allow its material to be offered under this file’s licence.`;
}

// Field by field, so that a fact added to the export reaches the file only when it is
// also added here, beside what the claim page shows.
function trialFacts(facts: ExportedTrialFacts): ExportedTrialFacts {
  return {
    study_kind: facts.study_kind,
    participants: facts.participants && { ...facts.participants },
    allocation: facts.allocation,
    masking: facts.masking,
    comparators: [...facts.comparators],
    healthy_volunteers: facts.healthy_volunteers,
    age_groups: [...facts.age_groups],
    sponsor: facts.sponsor && { name: facts.sponsor.name, kind: facts.sponsor.kind },
    primary_outcomes: facts.primary_outcomes.map(({ measure, time_frame }) => ({
      measure,
      time_frame,
    })),
    primary_outcomes_total: facts.primary_outcomes_total,
    why_stopped: facts.why_stopped,
    results: facts.results && {
      outcomes_total: facts.results.outcomes_total,
      outcomes: facts.results.outcomes.map((outcome) => ({
        title: outcome.title,
        time_frame: outcome.time_frame,
        unit: outcome.unit,
        measure: outcome.measure,
        spread_kind: outcome.spread_kind,
        rows: outcome.rows,
        groups: outcome.groups.map(({ title, analysed, value, spread, lower, upper }) => ({
          title,
          analysed,
          value,
          spread,
          lower,
          upper,
        })),
        comparisons: outcome.comparisons.map(({ groups, p_value, method, test }) => ({
          groups: [...groups],
          p_value,
          method,
          test,
        })),
      })),
    },
  };
}

export function openData(
  data: Export,
  licence: string,
  credit: string,
  method: string,
): OpenData {
  // A card is in the file only when its source's licence allows it to be offered under
  // the file's own. Openspec open-data: "Background cards in the download".
  const cardSources = data.card_sources ?? [];
  const allowed = new Set(
    cardSources.filter((source) => source.in_data_file).map((source) => source.name),
  );
  return {
    licence,
    credit,
    sources: data.sources.map(({ name, url }) => ({ name, url })),
    card_sources: cardSources
      .filter((source) => source.in_data_file)
      .map(({ name, title, credit, licence, url }) => ({ name, title, credit, licence, url })),
    left_out: cardSources
      .filter((source) => !source.in_data_file)
      .map((source) => ({
        source: source.title,
        licence: source.licence,
        reason: leftOutReason(source.licence),
      })),
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
        confidence: event.confidence ?? null,
      })),
      // Each trial with the facts the claim page shows for it and when its registry
      // record was read. Never the record itself. Openspec trial-facts.
      trials: (claim.trials ?? []).map((trial) => ({
        trial_id: trial.trial_id,
        source_name: trial.source_name,
        url: trial.url,
        title: trial.title,
        phases: [...trial.phases],
        state: trial.state,
        facts_as_of: trial.facts_as_of,
        facts: trial.facts === null ? null : trialFacts(trial.facts),
        papers: [...(trial.papers ?? [])],
      })),
      // Each paper the claim page lists, with its roles, the facts the page shows for
      // it and when its index record was read. Never an abstract, an author, an
      // affiliation or the record itself. Openspec paper-facts.
      papers: (claim.papers ?? []).map((paper) => ({
        identifier: paper.identifier,
        url: paper.url,
        record_url: paper.record_url,
        roles: paper.roles.map((role) => ({
          role: role.role,
          trial_id: role.trial_id ?? null,
          listed: role.listed ?? null,
          event_id: role.event_id ?? null,
          score: role.score ?? null,
          reasons: [...(role.reasons ?? [])],
          summary: role.summary ?? null,
        })),
        facts_as_of: paper.facts_as_of,
        facts: paper.facts && {
          title: paper.facts.title,
          journal: paper.facts.journal,
          year: paper.facts.year,
          kinds: [...paper.facts.kinds],
          open_access: paper.facts.open_access,
          retracted: paper.facts.retracted,
          studied_in: [...paper.facts.studied_in],
        },
      })),
      // What the claim page shows of each match: the record, its score and how it was read.
      matches: (claim.matches ?? []).map((match) => ({
        source_name: match.source_name,
        external_id: match.external_id,
        url: match.url,
        score: match.score,
        state: match.state,
        reading: match.reading,
        summary: match.summary,
      })),
      // Each background card the claim page shows, in its source's own words.
      background: (claim.background ?? [])
        .filter((card) => allowed.has(card.source))
        .map((card) => ({
          kind: card.kind,
          fit: card.fit,
          label: card.label,
          definition: card.definition,
          url: card.url,
          source: card.source,
          external_id: card.external_id,
          version: card.version,
          score: card.score,
          reasons: card.reasons.map((reason) => ({ ...reason })),
          read_at: card.read_at,
        })),
      checked_by_person: claim.checked_by_person,
    })),
  };
}
