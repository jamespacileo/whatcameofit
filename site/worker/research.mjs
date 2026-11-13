// Optional public metadata enrichment. A paper search is not a clinical match or
// evidence event. Never send article text/images or ask an AI model from here.
const DAY = 86_400;
const TTL = 7 * DAY;
const VERSION = 1;
const clean = (value, limit = 200) => typeof value === "string" ? value.trim().slice(0, limit) : "";
const distinct = (values) => [...new Map(values.map(v => [v.toLowerCase(), v])).values()];
const finite = (n) => typeof n === "number" && Number.isFinite(n);

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
  const name = clean(org?.names?.find(n => n.types?.includes("ror_display"))?.value, 300);
  if (!id || !name) return null;
  return {
    id, name, url: id,
    country: clean(org.locations?.[0]?.geonames_details?.country_name, 100),
    website: website(org.links?.find(link => link.type === "website")?.value),
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

export function makeResearch({ fetch, apiKey, contact, cache, now = Date.now, timeoutMs = 5000 }) {
  const pauses = new Map();
  let rorAfter = 0;
  const headers = { "User-Agent": `whatcameofit/1 (mailto:${clean(contact)})`, Accept: "application/json" };
  async function get(key) {
    try {
      const entry = await cache?.get(key, "json");
      return entry?.version === VERSION && finite(entry.until) && entry.until > now() ? entry.value : null;
    } catch { return null; }
  }
  async function put(key, value, seconds) {
    try { await cache?.put(key, JSON.stringify({ version: VERSION, until: now() + seconds * 1000, value }), { expirationTtl: Math.max(60, seconds) }); }
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
            redirect: "error", signal: controller.signal,
          });
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
  async function searchPapers(query) {
    const key = `research-v1:openalex:${await digest(query.toLowerCase())}`;
    const cached = await get(key);
    if (Array.isArray(cached)) return { items: cached };
    if (await paused("openalex")) return { error: "limit" };
    const budget = await request("https://api.openalex.org/rate-limit", "openalex");
    if (budget.error) return budget;
    if (!allowance(budget.body?.rate_limit)) { await pause("openalex", untilTomorrow()); return { error: "limit" }; }
    const url = new URL("https://api.openalex.org/works");
    url.search = new URLSearchParams({ search: query, per_page: "10", select: "id,title,doi,publication_year,type,primary_location" });
    const reply = await request(url.href, "openalex");
    if (reply.error) return reply;
    if (!Array.isArray(reply.body?.results)) return { error: "unavailable" };
    const items = reply.body.results.slice(0, 10).map(paper).filter(Boolean);
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
    const items = reply.body.items.slice(0, 20).map(organisation).filter(Boolean).slice(0, 1);
    await put(key, items, TTL);
    return { items };
  }
  return {
    async search({ intervention, indication, searchPhrases = [], organisations = [] } = {}) {
      const result = { papers: [], organisations: [], availability: { openalex: "not_needed", ror: "not_needed" } };
      if (!clean(contact)) return { ...result, availability: { openalex: "not_configured", ror: "not_configured" } };
      const terms = distinct([clean(intervention), ...(Array.isArray(searchPhrases) ? searchPhrases.slice(0, 3).map(v => clean(v)) : [])].filter(Boolean)).slice(0, 2);
      const names = distinct((Array.isArray(organisations) ? organisations.slice(0, 10).map(v => clean(v)) : []).filter(Boolean)).slice(0, 3);
      // Independent providers; a failure of one never removes the other's results.
      await Promise.all([
        (async () => {
          if (!apiKey) { result.availability.openalex = "not_configured"; return; }
          if (!terms.length || !clean(indication)) return;
          result.availability.openalex = "ok";
          for (const term of terms) {
            const found = await searchPapers(`${term} ${clean(indication)}`);
            if (found.error) { result.availability.openalex = found.error; break; }
            result.papers.push(...found.items);
          }
          result.papers = [...new Map(result.papers.map(p => [p.url.toLowerCase(), p])).values()].slice(0, 20);
        })(),
        (async () => {
          if (!names.length) return;
          result.availability.ror = "ok";
          for (const name of names) {
            const found = await findOrganisation(name);
            if (found.error) { result.availability.ror = found.error; break; }
            result.organisations.push(...found.items.map(item => ({ ...item, matchedName: name })));
          }
          result.organisations = [...new Map(result.organisations.map(o => [o.id, o])).values()];
        })(),
      ]);
      return result;
    },
  };
}
