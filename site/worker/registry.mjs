// ClinicalTrials.gov API v2, as the pipeline's client searches it. Terms and limits:
// docs/sources.md. Keep the search rule in step with thenwhat.sources.clinicaltrials.

const API = "https://clinicaltrials.gov/api/v2";
const SEARCH_FIELDS =
  "NCTId,BriefTitle,OfficialTitle,InterventionName,LeadSponsorName,Phase,OverallStatus,Condition";
// A name with more trials than this is a class or a common substance, not one product.
const BROAD_NAME = 100;
// A specific name's trials are read to this many pages of a hundred.
const MAX_PAGES = 2;
const VERSION = "1";
const GENERIC_CONDITION_WORDS = new Set(
  `a an and the of in for with from to or by after during due caused that which disease diseases
  disorder disorders syndrome syndromes condition conditions chronic acute severe mild moderate
  advanced early late stage type high low risk loss pain cancer blood patients patient adults
  adult children people`.split(/\s+/),
);

function tellingWords(condition) {
  const words = (condition.toLowerCase().match(/[a-z0-9][a-z0-9'-]*/g) ?? []).filter(
    (word) => word.length >= 3 && !GENERIC_CONDITION_WORDS.has(word),
  );
  const kept = [...new Set(words)];
  return kept.length ? kept.join(" OR ") : null;
}

export function makeRegistry({ fetch, contact }) {
  const headers = { "User-Agent": `thenwhat-lookup/${VERSION} (mailto:${contact})`, Accept: "application/json" };

  async function get(path, params) {
    const url = new URL(`${API}${path}`);
    for (const [name, value] of Object.entries(params ?? {})) url.searchParams.set(name, value);
    const response = await fetch(url.href, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`registry ${response.status}`);
    return response.json();
  }

  async function page(intervention, condition, pageToken) {
    const params = { "query.intr": intervention, pageSize: "100", fields: SEARCH_FIELDS, countTotal: "true" };
    if (condition) params["query.cond"] = condition;
    if (pageToken) params.pageToken = pageToken;
    const body = await get("/studies", params);
    const studies = body?.studies ?? [];
    return { studies, total: body?.totalCount ?? studies.length, next: body?.nextPageToken ?? null };
  }

  return {
    /** The full record of one trial, or null when the registry has none by that number. */
    async fetch(number) {
      return /^NCT\d{8}$/.test(number) ? get(`/studies/${number}`) : null;
    },

    /**
     * The trials whose interventions match the name. A broad name is searched within the
     * condition: as worded, then by its telling words. A name still broad there, or with
     * no trial there, returns nothing: it does not identify one treatment.
     */
    async search(intervention, condition) {
      const first = await page(intervention, null, null);
      if (condition && first.total > BROAD_NAME) {
        for (const wording of [condition, tellingWords(condition)]) {
          if (!wording) continue;
          const narrowed = await page(intervention, wording, null);
          if (narrowed.total > BROAD_NAME) return [];
          if (narrowed.studies.length) return narrowed.studies;
        }
        return [];
      }
      const studies = [...first.studies];
      let next = first.next;
      for (let read = 1; next && read < MAX_PAGES; read += 1) {
        const more = await page(intervention, null, next);
        studies.push(...more.studies);
        next = more.next;
      }
      return studies;
    },
  };
}
