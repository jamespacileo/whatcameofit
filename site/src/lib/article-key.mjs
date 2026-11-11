// The form in which two article addresses are compared. The site uses it to build
// lookup.json and the browser extension's build copies this same file, so the two
// always agree. Plain JavaScript on purpose: the extension has no build step for types.

// Parameters that describe how a reader arrived, not which article this is.
const TRACKING = /^(utm_.+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|ref|ref_src|cmpid|ocid|smid|ito|share|at_medium|at_campaign)$/i;

/**
 * @param {string} address
 * @returns {string | null} host and path in comparison form, or null when the
 *   address is not an http or https page.
 */
export function articleKey(address) {
  let url;
  try {
    url = new URL(address);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;

  const host = url.hostname.toLowerCase().replace(/^(www|m|amp)\./, "");
  const path = url.pathname
    .replace(/\/+$/, "")
    .replace(/(\/amp|\.amp)$/i, "");
  const kept = [...url.searchParams.entries()]
    .filter(([name]) => !TRACKING.test(name))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, value]) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`);

  return host + path + (kept.length ? `?${kept.join("&")}` : "");
}
