// Optional public metadata enrichment. A paper search is not a clinical match or
// evidence event. Never send article text/images or ask an AI model from here.
const DAY = 86_400;
const TTL = 7 * DAY;
const VERSION = 1;
const clean = (value, limit = 200) => typeof value === "string" ? value.trim().slice(0, limit) : "";
const distinct = (values) => [...new Map(values.map(v => [v.toLowerCase(), v])).values()];
const finite = (n) => typeof n === "number" && Number.isFinite(n);
const array = value => Array.isArray(value) ? value : [];
const SELECT = "id,title,doi,publication_year,type,primary_location";
// The most of each the page or the extraction may add to one lookup.
const MAX_CITATIONS = 3;
const MAX_PAPER_QUERIES = 2;
const MAX_RESEARCHERS = 2;
const MAX_PAPERS = 20;

// Bounded literature-search inputs. Anything that is not plainly words is dropped, not
// repaired: it reaches a provider's query language. Search operators, quotes and filter
// separators never pass.
const OPERATOR = /^(?:AND|OR|NOT)$/;
function paperQuery(value) {
  const words = clean(value).split(/\s+/).filter(Boolean);
  if (words.length < 2 || words.length > 6 || words.some(word => OPERATOR.test(word) || !/^[\p{L}\p{N}][\p{L}\p{N}'’-]*$/u.test(word))) return "";
  const query = words.join(" ");
  return query.length <= 120 ? query : "";
}
const TITLE = /^(?:dr|prof|professor|mr|mrs|ms|mx|sir|dame)\.?$/i;
function researcher(value) {
  const parts = clean(value).split(/\s+/).filter(Boolean);
  if (parts.length < 2 || parts.length > 5 || parts.some(part => TITLE.test(part) || !/^\p{L}[\p{L}\p{M}'’.-]*$/u.test(part))) return "";
  const name = parts.join(" ");
  return name.length <= 80 && parts.filter(part => /\p{L}{2}/u.test(part)).length >= 2 ? name : "";
}
// The calendar date of an ISO date or timestamp, when it is a real date.
function isoDate(value) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (raw.length > 40 || !finite(Date.parse(raw))) return "";
  const found = /^(\d{4})-(\d{2})-(\d{2})(?:$|T[\d:.]+(?:Z|[+-]\d{2}:?\d{2})?$)/.exec(raw);
  if (!found) return "";
  const [, year, month, day] = found.map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return year >= 1900 && year < 2200 && date.getUTCMonth() === month - 1 && date.getUTCDate() === day ? found.slice(1).join("-") : "";
}
function doiOf(value) {
  const doi = (typeof value === "string" ? value.trim() : "").replace(/^(?:https:\/\/(?:dx\.)?doi\.org\/|doi:)/i, "").toLowerCase();
  return /^10\.\d{4,9}\/[^\s?#&"'<>\\|,%]+$/.test(doi) && doi.length <= 200 && !/[\u0000-\u001f\u007f]/.test(doi) ? doi : "";
}
function pmidOf(value) {
  const pmid = typeof value === "number" && Number.isInteger(value) ? String(value) : clean(value);
  return /^[1-9]\d{0,8}$/.test(pmid) ? pmid : "";
}
// First occurrence wins: a later record with the same OpenAlex id or the same link is dropped.
function firstOfEach(papers) {
  const ids = new Set(), urls = new Set();
  return papers.filter(item => {
    const id = item.id.toLowerCase(), url = item.url.toLowerCase();
    if (ids.has(id) || urls.has(url)) return false;
    ids.add(id); urls.add(url);
    return true;
  });
}

async function boundedCache(operation) {
  let timer;
  try {
    return await Promise.race([operation(), new Promise(resolve => { timer = setTimeout(() => resolve(null), 200); })]);
  } catch { return null; }
  finally { clearTimeout(timer); }
}

function recordUrl(value, host, pattern) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === host && !url.username && !url.password && !url.port &&
      pattern.test(url.pathname) ? `${url.origin}${url.pathname}` : null;
  } catch { return null; }
}
function website(value) {
  try {
    const u = new URL(value);
    return u.protocol === "https:" && !u.username && !u.password ? u.href : null;
  } catch { return null; }
}
function paper(work) {
  const id = recordUrl(work?.id, "openalex.org", /^\/W\d+$/);
  const title = clean(work?.title, 500);
  if (!id || !title) return null;
  return {
    id, title, source: "openalex",
    year: Number.isInteger(work.publication_year) && work.publication_year > 1400 && work.publication_year < 2200 ? work.publication_year : null,
    kind: clean(work.type, 60), journal: clean(work.primary_location?.source?.display_name, 200),
    url: recordUrl(work.doi, "doi.org", /^\/10\.\d{4,9}\/\S+$/i) ?? id,
  };
}
function organisation(item) {
  if (item?.chosen !== true) return null;
  const org = item.organization;
  const id = recordUrl(org?.id, "ror.org", /^\/0[0-9a-z]{6}\d{2}$/);
  const name = clean(array(org?.names).find(n => array(n?.types).includes("ror_display"))?.value, 300);
  if (!id || !name) return null;
  return {
    id, name, url: id,
    country: clean(array(org.locations)[0]?.geonames_details?.country_name, 100),
    website: website(array(org.links).find(link => link?.type === "website")?.value),
    score: finite(item.score) && item.score >= 0 && item.score <= 1 ? item.score : null,
  };
}
function allowance(body) {
  const cost = body?.endpoint_costs_usd?.search;
  // No paid balance means OpenAlex's own account-wide cap is the final authority,
  // including concurrent requests from different Cloudflare locations. KV is only
  // a cache/cooldown, never claimed to be an atomic global spending counter.
  return finite(body?.daily_budget_usd) && body.daily_budget_usd > 0 && body.daily_budget_usd <= 1 &&
    finite(cost) && cost >= 0.001 && cost <= 0.01 && finite(body.daily_remaining_usd) &&
    body.daily_remaining_usd >= cost + 0.01 && body.prepaid_balance_usd === 0 && body.prepaid_remaining_usd === 0;
}
function retrySeconds(header, now) {
  const seconds = Number(header);
  const delay = header && Number.isFinite(seconds) ? seconds : (Date.parse(header) - now) / 1000;
  return Math.ceil(Math.min(DAY, Math.max(60, Number.isFinite(delay) ? delay : 60)));
}
async function digest(value) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(bytes)].map(n => n.toString(16).padStart(2, "0")).join("");
}

// The literature searches for one lookup. Paper queries from the report are complete
// queries in their own right, about the research itself; the condition is not appended.
// Without them, the treatment's names within the condition, as before.
function plan({ intervention, indication, searchPhrases, paperQueries, researchers, publishedBefore }) {
  const before = isoDate(publishedBefore);
  const queries = distinct(array(paperQueries).slice(0, 10).map(paperQuery).filter(Boolean)).slice(0, MAX_PAPER_QUERIES);
  const authors = distinct(array(researchers).slice(0, 10).map(researcher).filter(Boolean)).slice(0, MAX_RESEARCHERS);
  let searches;
  if (queries.length) {
    searches = [...authors.map(author => ({ query: queries[0], author })), ...queries.map(query => ({ query }))];
  } else {
    const terms = distinct([clean(intervention), ...array(searchPhrases).slice(0, 3).map(v => clean(v))].filter(Boolean)).slice(0, 2);
    searches = clean(indication) ? terms.map(term => ({ query: `${term} ${clean(indication)}` })) : [];
  }
  const planned = new Map(searches.map(s => ({ ...s, before })).map(s => [JSON.stringify([s.query.toLowerCase(), (s.author ?? "").toLowerCase()]), s]));
  return [...planned.values()];
}

export function makeResearch({ fetch, apiKey, contact, cache, now = Date.now, timeoutMs = 5000 }) {
  const pauses = new Map();
  let rorAfter = 0;
  const headers = { "User-Agent": `whatcameofit/1 (mailto:${clean(contact)})`, Accept: "application/json" };
  async function get(key) {
    try {
      const entry = await boundedCache(() => cache?.get(key, "json"));
      return entry?.version === VERSION && finite(entry.until) && entry.until > now() ? entry.value : null;
    } catch { return null; }
  }
  async function put(key, value, seconds) {
    try { await boundedCache(() => cache?.put(key, JSON.stringify({ version: VERSION, until: now() + seconds * 1000, value }), { expirationTtl: Math.max(60, seconds) })); }
    catch { /* A cache outage cannot turn an optional search into a failed lookup. */ }
  }
  async function paused(source) {
    return (pauses.get(source) ?? 0) > now() || await get(`research-v1:pause:${source}`) === true;
  }
  async function pause(source, seconds) {
    pauses.set(source, now() + seconds * 1000);
    await put(`research-v1:pause:${source}`, true, seconds);
  }
  const untilTomorrow = () => Math.max(60, Math.ceil((Math.floor(now() / (DAY * 1000)) * DAY * 1000 + DAY * 1000 - now()) / 1000));
  async function request(url, source) {
    const controller = new AbortController();
    let timer;
    try {
      return await Promise.race([
        (async () => {
          const response = await fetch(url, {
            headers: source === "openalex" ? { ...headers, Authorization: `Bearer ${apiKey}` } : headers,
            // Workers supports manual/follow only. A 3xx is refused below, so the
            // Authorization header can never follow a redirect to another host.
            redirect: "manual", signal: controller.signal,
          });
          if (!response.ok) {
            if ([401, 402, 403, 429].includes(response.status)) {
              await pause(source, response.status === 429 ? retrySeconds(response.headers.get("Retry-After"), now()) : untilTomorrow());
            }
            return { error: [402, 429].includes(response.status) ? "limit" : "unavailable", status: response.status };
          }
          // Hold the timeout through body consumption. Bound an unexpected provider
          // payload, as well as the number of records requested.
          const reader = response.body?.getReader();
          if (!reader) return { error: "unavailable" };
          const chunks = []; let size = 0;
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            size += value.byteLength;
            if (size > 512_000) { await reader.cancel(); return { error: "unavailable" }; }
            chunks.push(value);
          }
          const bytes = new Uint8Array(size); let offset = 0;
          for (const part of chunks) { bytes.set(part, offset); offset += part.length; }
          return { body: JSON.parse(new TextDecoder().decode(bytes)) };
        })(),
        new Promise(resolve => { timer = setTimeout(() => { controller.abort(); resolve({ error: "unavailable" }); }, timeoutMs); }),
      ]);
    } catch { return { error: "unavailable" }; }
    finally { clearTimeout(timer); }
  }
  // One charged search. The cache key holds every constraint, so a search scoped to
  // an author or a date never answers for another.
  async function searchPapers({ query, author = "", before = "" }) {
    const key = author || before
      ? `research-v1:openalex:scoped:${await digest(JSON.stringify([query.toLowerCase(), author.toLowerCase(), before]))}`
      : `research-v1:openalex:${await digest(query.toLowerCase())}`;
    const cached = await get(key);
    if (Array.isArray(cached)) return { items: cached };
    if (await paused("openalex")) return { error: "limit" };
    const budget = await request("https://api.openalex.org/rate-limit", "openalex");
    if (budget.error) return budget;
    if (!allowance(budget.body?.rate_limit)) { await pause("openalex", untilTomorrow()); return { error: "limit" }; }
    const filter = [author && `raw_author_name.search:"${author}"`, before && `to_publication_date:${before}`].filter(Boolean).join(",");
    const url = new URL("https://api.openalex.org/works");
    url.search = new URLSearchParams({ search: query, ...(filter ? { filter } : {}), per_page: "10", select: SELECT });
    const reply = await request(url.href, "openalex");
    if (reply.error) return reply;
    if (!Array.isArray(reply.body?.results)) return { error: "unavailable" };
    const items = reply.body.results.slice(0, 10).map(paper).filter(Boolean);
    await put(key, items, TTL);
    return { items };
  }
  // One cited work by its identifier. A singleton costs nothing, so it needs no allowance
  // check, but it still honours a provider pause. A clean 404 is a cached no-hit; a
  // malformed record or an outage is never cached as empty.
  async function citedWork({ kind, value }) {
    const key = `research-v1:openalex:work:${kind}:${await digest(value)}`;
    const cached = await get(key);
    if (Array.isArray(cached)) return { items: cached };
    if (await paused("openalex")) return { error: "limit" };
    const url = new URL(`https://api.openalex.org/works/${kind}:${kind === "doi" ? encodeURIComponent(value) : value}`);
    url.search = new URLSearchParams({ select: SELECT });
    const reply = await request(url.href, "openalex");
    if (reply.status === 404) { await put(key, [], TTL); return { items: [] }; }
    if (reply.error) return reply;
    const item = paper(reply.body);
    if (!item) return { error: "unavailable" };
    await put(key, [item], TTL);
    return { items: [item] };
  }
  async function findOrganisation(name) {
    const key = `research-v1:ror:${await digest(name.toLowerCase())}`;
    const cached = await get(key);
    if (Array.isArray(cached)) return { items: cached };
    if (await paused("ror")) return { error: "limit" };
    const wait = Math.max(0, rorAfter - now());
    if (wait) await new Promise(resolve => setTimeout(resolve, Math.min(wait, 500)));
    rorAfter = now() + 500;
    const url = new URL("https://api.ror.org/v2/organizations");
    url.search = new URLSearchParams({ affiliation: name });
    const reply = await request(url.href, "ror");
    if (reply.error) return reply;
    if (!Array.isArray(reply.body?.items)) return { error: "unavailable" };
    const candidates = reply.body.items.slice(0, 20);
    if (candidates.some(item => item?.chosen === true && !organisation(item))) return { error: "unavailable" };
    const items = candidates.map(organisation).filter(Boolean).slice(0, 1);
    await put(key, items, TTL);
    return { items };
  }
  return {
    async search({ intervention, indication, searchPhrases = [], organisations = [], paperQueries = [], researchers = [],
      publishedBefore = null, dois = [], pubmedIds = [] } = {}) {
      const result = { papers: [], organisations: [], availability: { openalex: "not_needed", ror: "not_needed" } };
      if (!clean(contact)) return { ...result, availability: { openalex: "not_configured", ror: "not_configured" } };
      const names = distinct(array(organisations).slice(0, 10).map(v => clean(v)).filter(Boolean)).slice(0, 3);
      const citations = [...new Map([
        ...array(dois).slice(0, 10).map(v => ({ kind: "doi", value: doiOf(v) })),
        ...array(pubmedIds).slice(0, 10).map(v => ({ kind: "pmid", value: pmidOf(v) })),
      ].filter(c => c.value).map(c => [`${c.kind}:${c.value}`, c])).values()].slice(0, MAX_CITATIONS);
      const searches = plan({ intervention, indication, searchPhrases, paperQueries, researchers, publishedBefore });
      // Independent providers; a failure of one never removes the other's results.
      await Promise.all([
        (async () => {
          if (!apiKey) { result.availability.openalex = "not_configured"; return; }
          if (!citations.length && !searches.length) return;
          result.availability.openalex = "ok";
          // A paper the page cites comes first and stays whatever happens to discovery.
          const cited = [], found = [];
          let citationError = null;
          try {
            for (const citation of citations) {
              const reply = await citedWork(citation);
              if (reply.error === "limit") { result.availability.openalex = "limit"; return; }
              if (reply.error) citationError = reply.error;
              if (!reply.error) cited.push(...reply.items);
            }
            // Researcher-scoped searches first, then the unscoped fallbacks. Every planned
            // search runs; the result cap applies only after all of them.
            for (const search of searches) {
              const reply = await searchPapers(search);
              if (reply.error) { result.availability.openalex = reply.error; break; }
              found.push(...reply.items);
            }
            if (citationError && result.availability.openalex === "ok") result.availability.openalex = citationError;
          } finally {
            result.papers = firstOfEach([...cited, ...found]).slice(0, MAX_PAPERS);
          }
        })().catch(() => { result.availability.openalex = "unavailable"; }),
        (async () => {
          if (!names.length) return;
          result.availability.ror = "ok";
          for (const name of names) {
            const found = await findOrganisation(name);
            if (found.error) { result.availability.ror = found.error; break; }
            result.organisations.push(...found.items.map(item => ({ ...item, matchedName: name })));
          }
          result.organisations = [...new Map(result.organisations.map(o => [o.id, o])).values()];
        })().catch(() => { result.availability.ror = "unavailable"; }),
      ]);
      return result;
    },
  };
}
