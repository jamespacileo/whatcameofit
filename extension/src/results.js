// Private to this browser. A previous answer is useful, but never silently current.
export const RESULT_TTL = 24 * 60 * 60 * 1000;
export function reusable(entries, key, fingerprint, now) {
  return (Array.isArray(entries) ? entries : []).find(entry => entry.version === 1 && entry.key === key &&
    entry.fingerprint === fingerprint && entry.at <= now && now - entry.at < RESULT_TTL &&
    entry.found?.about_a_treatment === true) ?? null;
}
export function remember(entries, key, fingerprint, found, now) {
  if (!fingerprint || found?.about_a_treatment !== true) return entries;
  return [{ version: 1, key, fingerprint, found, at: now }, ...(Array.isArray(entries) ? entries : [])
    .filter(entry => entry.key !== key && entry.at <= now && now - entry.at < RESULT_TTL)].slice(0, 10);
}
