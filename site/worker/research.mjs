// Optional public metadata enrichment. A paper search is not a clinical match or
// evidence event. Never send article text/images or ask an AI model from here.
const DAY = 86_400;
const TTL = 7 * DAY;
const VERSION = 1;
const clean = (value, limit = 200) => typeof value === "string" ? value.trim().slice(0, limit) : "";
const distinct = (values) => [...new Map(values.map(v => [v.toLowerCase(), v])).values()];
const finite = (n) => typeof n === "number" && Number.isFinite(n);
const array = value => Array.isArray(value) ? value : [];

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
/** Fetching one work by its identifier is free on the free plan. Anything else is refused. */
function freeLookup(body) {
  return body?.endpoint_costs_usd?.singleton === 0 && body.prepaid_balance_usd === 0 && body.prepaid_remaining_usd === 0;
}
/** A paper the page links to, as OpenAlex addresses it: by DOI or by PubMed number. */
function linkedId(ref) {
  const doi = clean(ref?.doi).toLowerCase();
  if (/^10\.\d{4,9}\/[^\s?#]+$/.test(doi)) return `doi:${doi}`;
  const pubmedId = clean(ref?.pubmedId);
  return /^\d{4,9}$/.test(pubmedId) ? `pmid:${pubmedId}` : null;
}
/** Two years before a report to a month after it, as publication-date filters. Nothing for no date. */
function around(published) {
  const at = Date.parse(clean(published, 40));
  if (!Number.isFinite(at)) return [];
  const day = offset => new Date(at + offset * DAY * 1000).toISOString().slice(0, 10);
  return [`from_publication_date:${day(-730)}`, `to_publication_date:${day(31)}`];
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
          // No such record. Only a lookup by identifier treats this as an answer.
          if (response.status === 404) return { missing: true };
          if (!response.ok) {
            if ([401, 402, 403, 429].includes(response.status)) {
              await pause(source, response.status === 429 ? retrySeconds(response.headers.get("Retry-After"), now()) : untilTomorrow());
            }
            return { error: [402, 429].includes(response.status) ? "limit" : "unavailable" };
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
  async function searchPapers(query, filter = "") {
    const key = `research-v1:openalex:${await digest(`${query}${filter && `\n${filter}`}`.toLowerCase())}`;
    const cached = await get(key);
    if (Array.isArray(cached)) return { items: cached };
    if (await paused("openalex")) return { error: "limit" };
    const budget = await request("https://api.openalex.org/rate-limit", "openalex");
    if (budget.error) return budget;
    if (!allowance(budget.body?.rate_limit)) { await pause("openalex", untilTomorrow()); return { error: "limit" }; }
    const url = new URL("https://api.openalex.org/works");
    url.search = new URLSearchParams({ search: query, ...(filter ? { filter } : {}), per_page: "10", select: "id,title,doi,publication_year,type,primary_location" });
    const reply = await request(url.href, "openalex");
    if (reply.error) return reply;
    if (!Array.isArray(reply.body?.results)) return { error: "unavailable" };
    const items = reply.body.results.slice(0, 10).map(paper).filter(Boolean);
    await put(key, items, TTL);
    return { items };
  }
  /** The record of one paper the page links to. Not a search: the identifier is the page's own. */
  async function linkedPaper(id) {
    const key = `research-v1:openalex-work:${await digest(id)}`;
    const cached = await get(key);
    if (Array.isArray(cached)) return { items: cached };
    if (await paused("openalex")) return { error: "limit" };
    const budget = await request("https://api.openalex.org/rate-limit", "openalex");
    if (budget.error || budget.missing) return { error: budget.error ?? "unavailable" };
    if (!freeLookup(budget.body?.rate_limit)) return { error: "limit" };
    const url = new URL(`https://api.openalex.org/works/${id}`);
    url.search = new URLSearchParams({ select: "id,title,doi,publication_year,type,primary_location" });
    const reply = await request(url.href, "openalex");
    if (reply.error) return reply;
    const found = reply.missing ? null : paper(reply.body);
    const items = found ? [{ ...found, linked: true }] : [];
    await put(key, items, TTL);
    return { items };
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
    async search({ intervention, indication, searchPhrases = [], organisations = [], linked = [], published } = {}) {
      const result = { papers: [], organisations: [], availability: { openalex: "not_needed", ror: "not_needed" } };
      if (!clean(contact)) return { ...result, availability: { openalex: "not_configured", ror: "not_configured" } };
      const terms = distinct([clean(intervention), ...(Array.isArray(searchPhrases) ? searchPhrases.slice(0, 3).map(v => clean(v)) : [])].filter(Boolean)).slice(0, 2);
      const ids = distinct((Array.isArray(linked) ? linked.slice(0, 3).map(linkedId) : []).filter(Boolean));
      const names = distinct((Array.isArray(organisations) ? organisations.slice(0, 10).map(v => clean(v)) : []).filter(Boolean)).slice(0, 3);
      // A failure of one provider never removes the other's results.
      const identified = (async () => {
        if (!names.length) return;
        result.availability.ror = "ok";
        for (const name of names) {
          const found = await findOrganisation(name);
          if (found.error) { result.availability.ror = found.error; break; }
          result.organisations.push(...found.items.map(item => ({ ...item, matchedName: name })));
        }
        result.organisations = [...new Map(result.organisations.map(o => [o.id, o])).values()];
      })().catch(() => { result.availability.ror = "unavailable"; });
      await Promise.all([
        (async () => {
          if (!apiKey) { result.availability.openalex = "not_configured"; return; }
          const queries = terms.length && clean(indication) ? terms.map(term => `${term} ${clean(indication)}`) : [];
          if (!ids.length && !queries.length) return;
          result.availability.openalex = "ok";
          const found = [];
          const ask = async (search, mark = {}) => {
            const reply = await search();
            if (reply.error) { result.availability.openalex = reply.error; return false; }
            found.push(...reply.items.map(item => ({ ...item, ...mark })));
            return true;
          };
          // The papers the page links to come first: a press release words a finding
          // differently from its paper's title, so a search by keyword can miss it.
          for (const id of ids) if (!await ask(() => linkedPaper(id))) return;
          for (const query of queries) if (!await ask(() => searchPapers(query))) return;
          // A report names where the work was done. Papers on the treatment whose authors
          // are at a named organisation, published around the report, are searched for too:
          // this finds the paper when its title shares few words with the report.
          await identified;
          const anyTerm = terms.map(term => `(${term.replace(/[()"]/g, " ")})`).join(" OR ");
          for (const org of terms.length ? result.organisations : []) {
            const filter = [`authorships.institutions.ror:${org.id}`, ...around(published)].join(",");
            if (!await ask(() => searchPapers(anyTerm, filter), { institutions: [org.name] })) break;
          }
          // One record per paper: marked as linked if any finding was, with every named
          // organisation it was found under. Linked first, then the most organisations.
          const papers = new Map();
          for (const { institutions = [], ...one } of found) {
            const kept = papers.get(one.url.toLowerCase()) ?? papers.set(one.url.toLowerCase(), { ...one, institutions: [] }).get(one.url.toLowerCase());
            if (one.linked) kept.linked = true;
            kept.institutions = distinct([...kept.institutions, ...institutions]);
          }
          const weight = p => (p.linked ? 10 : 0) + p.institutions.length;
          result.papers = [...papers.values()].sort((a, b) => weight(b) - weight(a)).slice(0, 20)
            .map(({ institutions, ...one }) => institutions.length ? { ...one, institutions } : one);
        })().catch(() => { result.availability.openalex = "unavailable"; }),
        identified,
      ]);
      return result;
    },
  };
}
