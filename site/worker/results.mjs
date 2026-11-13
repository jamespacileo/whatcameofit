// Only independently public reports enter this shared, expiring results library.
// No page text, screenshots or reader identifiers are persisted.
import { articleKey } from "../src/lib/article-key.mjs";
import { sourceUrl } from "./visual.mjs";
const TTL = 86400;
async function keyFor(address) {
  const safe = sourceUrl(address);
  if (!safe) return null;
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(articleKey(safe)));
  return "visual-v1:" + [...new Uint8Array(hash)].map(n => n.toString(16).padStart(2, "0")).join("");
}
export async function previousResult(store, address, now = Date.now()) {
  if (!store) return null;
  const key = await keyFor(address);
  if (!key) return null;
  try {
    const entry = await store.get(key, "json");
    if (entry?.version !== 1 || !entry.publicVerified || !entry.found?.about_a_treatment || entry.at > now || now - entry.at >= TTL * 1000) return null;
    return { ...entry.found, cache: { checkedAt: entry.at, shared: true } };
  } catch { return null; }
}
export async function storeResult(store, address, found, publicVerified, now = Date.now()) {
  if (!store || !publicVerified || found.about_a_treatment !== true) return;
  const key = await keyFor(address);
  if (!key) return;
  // Explicit fields only. Never persist an uploaded request, copied text or model gist.
  const { treatment, condition, names, known_names, registry_numbers, paper_numbers, details, tracked, candidates, unscored, post, source } = found;
  const kept = { about_a_treatment: true, treatment, condition, names, known_names, registry_numbers, paper_numbers, details, tracked, candidates, unscored, post, source };
  try { await store.put(key, JSON.stringify({ version: 1, publicVerified: true, at: now, found: kept }), { expirationTtl: TTL }); } catch { /* Lookup still works without caching. */ }
}
