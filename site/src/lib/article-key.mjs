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

/** A single YouTube video, regardless of share, Shorts, live or watch URL form. */
export function youtubeVideoUrl(value) {
  let url;
  try { url = new URL(value); } catch { return null; }
  if (!/^https?:$/.test(url.protocol) || url.username || url.password || url.port) return null;
  const host = url.hostname;
  let id;
  if (host === "youtu.be") id = url.pathname.match(/^\/([\w-]{11})\/?$/)?.[1];
  else if (["youtube.com", "www.youtube.com", "m.youtube.com"].includes(host)) {
    id = url.pathname === "/watch" && url.searchParams.getAll("v").length === 1
      ? url.searchParams.get("v")
      : url.pathname.match(/^\/(?:shorts|live|embed)\/([\w-]{11})\/?$/)?.[1];
  }
  if (!id || !/^[\w-]{11}$/.test(id)) return null;
  // A path ID and a different query ID are ambiguous, even on a known host.
  if (url.pathname !== "/watch" && url.searchParams.has("v")) return null;
  return `https://www.youtube.com/watch?v=${id}`;
}

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

  const video = youtubeVideoUrl(address);
  if (video) return video.slice("https://www.".length);

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
