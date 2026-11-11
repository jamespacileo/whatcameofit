// The form in which two article addresses are compared. The site uses it to build
// lookup.json and the browser extension's build copies this same file, so the two
// always agree. Plain JavaScript on purpose: the extension has no build step for types.

// Parameters that describe how a reader arrived, not which article this is.
const TRACKING =
  /^(utm_.+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|ref|ref_src|ref_url|referrer|cmpid|cmp|ocid|smid|smtyp|ito|share|share_.+|at_.+|ns_.+|amp|amp_.+|outputtype|usqp|mibextid|xtor|guccounter|guce_.+|soc_src|soc_trk|tsrc|ncid|sr_share|taid|unlocked_article_code|emc|partner|rss)$/i;

// Leading host labels that serve the same article as the bare host.
const SAME_SITE_LABELS = /^(www|m|mobile|amp|edition)\./;

// Hosts that serve one site under two names.
const HOST_ALIASES = { "bbc.co.uk": "bbc.com" };

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

  let host = url.hostname.toLowerCase();
  while (SAME_SITE_LABELS.test(host)) host = host.replace(SAME_SITE_LABELS, "");
  host = HOST_ALIASES[host] ?? host;

  let path = url.pathname
    .replace(/\/+$/, "")
    .replace(/\/index\.html?$/i, "")
    .replace(/(\/amp|\.amp)$/i, "")
    .replace(/^\/amp(?=\/)/i, "");
  // CNN's AMP host repeats the site name as the first part of the path.
  if (host === "cnn.com") path = path.replace(/^\/cnn(?=\/)/, "");
  // A Daily Mail article is its number; the words after it vary and are often cut short.
  const mail = host === "dailymail.co.uk" && path.match(/\/article-(\d+)(\/|$)/);
  if (mail) path = `/article-${mail[1]}`;

  const kept = [...url.searchParams.entries()]
    .filter(([name]) => !TRACKING.test(name))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, value]) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`);

  return host + path + (kept.length ? `?${kept.join("&")}` : "");
}
