// ClinicalTrials.gov API v2, as the pipeline's client searches it. Terms and limits:
// docs/sources.md. Keep the search rule in step with thenwhat.sources.clinicaltrials.
// A public registry answer may be reused for a day; a failure is never kept.

import { withDeadline } from "./deadline.mjs";
import { SOURCE_TTL_SECONDS, makeShared, makeSourceCache } from "./public-cache.mjs";

const API = "https://clinicaltrials.gov/api/v2";
// One request, its body included.
const TIMEOUT_MS = 10_000;
// The acronym, the enrolment and the collaborators let a lookup tell which of a
// treatment's trials an article reports.
const SEARCH_FIELDS =
  "NCTId,BriefTitle,OfficialTitle,InterventionName,LeadSponsorName,Phase,OverallStatus,Condition" +
  ",Acronym,EnrollmentCount,CollaboratorName,StudyType" +
  ",InterventionDescription,InterventionArmGroupLabel,ArmGroupLabel,ArmGroupType,ArmGroupDescription,ArmGroupInterventionName";
// A trial's name that this many trials carry does not identify one.
const MAX_NAMED_TRIALS = 20;
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

export function makeRegistry({ fetch, contact, timeoutMs = TIMEOUT_MS, cache, cacheTimeoutMs }) {
  const headers = { "User-Agent": `thenwhat-lookup/${VERSION} (mailto:${contact})`, Accept: "application/json" };
  const reuse = makeSourceCache(cache, { kind: "registry", timeoutMs: cacheTimeoutMs });
  const shared = makeShared();

  /** Aborting `parent` ends the wait: the lookup no longer needs the answer. */
  async function get(path, params, parent) {
    const url = new URL(`${API}${path}`);
    for (const [name, value] of Object.entries(params ?? {})) url.searchParams.set(name, value);
    return shared(url.href, async (signal) => {
      const key = await reuse.key(url.href);
      const saved = await reuse.get(key);
      if (saved && typeof saved === "object") return saved;
      // A registry that does not answer in time is an error, never an empty search.
      const body = await withDeadline(timeoutMs, async (deadline) => {
        const response = await fetch(url.href, { headers, signal: deadline });
        if (response.status === 404) return null;
        if (!response.ok) throw new Error(`registry ${response.status}`);
        return response.json();
      }, { label: "registry", parent: signal });
      // Only a public answer is kept; a missing record is asked about again.
      if (body && typeof body === "object") await reuse.put(key, body, SOURCE_TTL_SECONDS);
      return body;
    }, parent);
  }

  async function page(intervention, condition, pageToken, signal) {
    const params = { "query.intr": intervention, pageSize: "100", fields: SEARCH_FIELDS, countTotal: "true" };
    if (condition) params["query.cond"] = condition;
    if (pageToken) params.pageToken = pageToken;
    const body = await get("/studies", params, signal);
    const studies = body?.studies ?? [];
    return { studies, total: body?.totalCount ?? studies.length, next: body?.nextPageToken ?? null };
  }

  return {
    /** The full record of one trial, or null when the registry has none by that number. */
    async fetch(number, { signal } = {}) {
      return /^NCT\d{8}$/.test(number) ? get(`/studies/${number}`, null, signal) : null;
    },

    /**
     * The trials that carry this name in their acronym or title, such as SURMOUNT-5.
     * None when so many do that the name does not identify a trial.
     */
    async named(name, { signal, condition } = {}) {
      const phrase = String(name ?? "").replaceAll('"', " ").trim();
      if (!phrase) return [];
      const params = {
        "query.titles": `"${phrase}"`,
        pageSize: String(MAX_NAMED_TRIALS),
        fields: SEARCH_FIELDS,
        countTotal: "true",
      };
      // Common acronyms can identify one study within the stated condition.
      // Narrow at most once; never paginate a broad or still ambiguous name.
      for (const within of condition ? [null, condition] : [null]) {
        const body = await get("/studies", { ...params, ...(within ? { "query.cond": within } : {}) }, signal);
        const studies = body?.studies ?? [];
        if ((body?.totalCount ?? studies.length) <= MAX_NAMED_TRIALS) return studies;
      }
      return [];
    },

    /**
     * The trials whose interventions match the name. A broad name is searched within the
     * condition: as worded, then by its telling words. A name still broad there, or with
     * no trial there, returns nothing: it does not identify one treatment.
     */
    async search(intervention, condition, { signal } = {}) {
      const first = await page(intervention, null, null, signal);
      if (condition && first.total > BROAD_NAME) {
        for (const wording of [condition, tellingWords(condition)]) {
          if (!wording) continue;
          const narrowed = await page(intervention, wording, null, signal);
          if (narrowed.total > BROAD_NAME) return [];
          if (narrowed.studies.length) return narrowed.studies;
        }
        return [];
      }
      const studies = [...first.studies];
      let next = first.next;
      for (let read = 1; next && read < MAX_PAGES; read += 1) {
        const more = await page(intervention, null, next, signal);
        studies.push(...more.studies);
        next = more.next;
      }
      return studies;
    },
  };
}
