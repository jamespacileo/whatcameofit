// Only independently public reports enter this shared, expiring results library.
// No page text, screenshots or reader identifiers are persisted. Version 4 also
// excludes answers from before incidental-drug, multi-claim and company-history corrections.
import { articleKey } from "../src/lib/article-key.mjs";
import { bounded } from "./public-cache.mjs";
import { sourceUrl } from "./visual.mjs";
const TTL = 86400;
const VERSION = 8;
// The longest one shared-result read or write is waited on.
const CACHE_TIMEOUT_MS = 500;
async function keyFor(address) {
  const safe = sourceUrl(address);
  if (!safe) return null;
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(articleKey(safe)));
  return `visual-v${VERSION}:` + [...new Uint8Array(hash)].map(n => n.toString(16).padStart(2, "0")).join("");
}
export async function previousResult(store, address, now = Date.now()) {
  if (!store) return null;
  const key = await keyFor(address);
  if (!key) return null;
  const entry = await bounded(() => store.get(key, "json"), CACHE_TIMEOUT_MS);
  if (entry?.version !== VERSION || !entry.publicVerified || typeof entry.found?.about_a_treatment !== "boolean" ||
    typeof entry.at !== "number" || entry.at > now || now - entry.at >= TTL * 1000) return null;
  return { ...entry.found, cache: { checkedAt: entry.at, shared: true } };
}
export async function storeResult(store, address, found, publicVerified, now = Date.now()) {
  if (!store || !publicVerified || typeof found?.about_a_treatment !== "boolean" || found.error || found.article_tracked) return;
  // An answer that is missing a linked paper is not kept: the next lookup asks again.
  if (found.papers_unchecked > 0) return;
  const key = await keyFor(address);
  if (!key) return;
  // Explicit fields only. Never persist an uploaded request, copied text or model gist.
  const { treatment, condition, names, known_names, registry_numbers, paper_numbers, details, tracked, candidates, unscored, post, source, research } = found;
  const kept = found.about_a_treatment
    ? { about_a_treatment: true, treatment, condition, names, known_names, registry_numbers, paper_numbers, papers_unchecked: 0, details, tracked, candidates, unscored, post, source, research }
    // A completed non-treatment identification: what was read, and that nothing was searched.
    : { about_a_treatment: false, treatment: null, condition: null, names: [], known_names: [], registry_numbers: registry_numbers ?? [], paper_numbers: [],
      papers_unchecked: 0, details: { trial_name: null, participants: null, sponsor: null }, tracked: [], candidates: [], unscored: 0, post, source };
  // Lookup still works without caching.
  await bounded(() => store.put(key, JSON.stringify({ version: VERSION, publicVerified: true, at: now, found: kept }), { expirationTtl: TTL }), CACHE_TIMEOUT_MS);
}
