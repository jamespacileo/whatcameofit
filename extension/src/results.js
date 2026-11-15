// Private to this browser. A previous answer is useful, but never silently current.
// Version 3 also excludes answers from before current-post scoping and corrected
// treatment-report identification. Only completed answers can be reused.
export const RESULT_TTL = 24 * 60 * 60 * 1000;
const VERSION = 3;
const MAX_RESULTS = 10;

/** Whether an answer is whole: not an error, a miss, a partial stream or one that is
 * missing a linked paper. A non-treatment answer counts only in the service's full shape. */
export function completed(found) {
  if (!found || typeof found !== "object" || found.error || found.cacheMiss || found.incomplete) return false;
  if (typeof found.about_a_treatment !== "boolean" || found.papers_unchecked > 0) return false;
  return found.about_a_treatment || (Array.isArray(found.candidates) && found.papers_unchecked === 0);
}
export function reusable(entries, key, fingerprint, now) {
  return (Array.isArray(entries) ? entries : []).find(entry => entry?.version === VERSION && entry.key === key &&
    entry.fingerprint === fingerprint && entry.at <= now && now - entry.at < RESULT_TTL &&
    completed(entry.found)) ?? null;
}
/** Whether a fresh saved answer exists for this page at all, whatever its content. */
export function savedFor(entries, key, now) {
  return (Array.isArray(entries) ? entries : []).some(entry => entry?.version === VERSION && entry.key === key &&
    entry.at <= now && now - entry.at < RESULT_TTL);
}
export function remember(entries, key, fingerprint, found, now) {
  // An answer that is missing a linked paper, or is otherwise unfinished, is not kept:
  // opening the page again asks again.
  if (!fingerprint || !key || !Number.isFinite(now) || !completed(found)) return entries;
  // The model's summary of the page is not needed to show the answer, so it is not kept.
  const { gist, ...kept } = found;
  // `now` is when the answer was checked, which for a shared answer may be earlier.
  const current = Math.max(now, Date.now());
  return [{ version: VERSION, key, fingerprint, found: kept, at: now }, ...(Array.isArray(entries) ? entries : [])
    .filter(entry => entry?.version === VERSION && entry.key !== key && entry.at <= current && current - entry.at < RESULT_TTL)].slice(0, MAX_RESULTS);
}
