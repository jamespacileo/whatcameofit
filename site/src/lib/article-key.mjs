// The form in which two article addresses are compared. The site uses it to build
// lookup.json and the browser extension's build copies this same file, so the two
// always agree. Plain JavaScript on purpose: the extension has no build step for types.

// Parameters that describe how a reader arrived, not which article this is. The second
// line was added after the pipeline's run of 2026-11-16: each name was seen separating
// two addresses of one article.
const TRACKING = new RegExp(
  "^(utm_.+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|ref|ref_src|ref_url|referrer|cmpid|cmp|ocid|smid|smtyp|ito|share|share_.+|at_.+|ns_.+|amp|amp_.+|outputtype|usqp|mibextid|xtor|guccounter|guce_.+|soc_src|soc_trk|tsrc|ncid|sr_share|taid|unlocked_article_code|emc|partner|rss" +
    "|_r|pgtype|wt\\..+|contentcollection|contentplacement|clicksource|rref|mbid|fsrc|nlid|hpid|hpw|em_pos|nl_art|mtrref|smprod|gwh|gwt|mabreward|__twitter_impression|postshare|trk|trk_.+|__source|srnd|intcid|icid|ribbon-ad-idx|moduledetail|eventname|_ga|_gl|mkt_tok|yclid|twclid|gbraid|wbraid|_hsenc|_hsmi|hsctatracking|sref|leadsource|s_cid|spm|wpisrc|wpmm|wprss|wpmk|referringsource|accesstoken|reflink|cndid|spjobid|spmailingid|spreportid|spuserid|google_editors_picks|lipi|hootpostid|sharetoken|emailtoken|cx_.+)$",
  "i",
);

// Parameters that say how a reader arrived, or which page of one article is shown, on one
// outlet only. Elsewhere a parameter of the same name may name the article.
const OUTLET_TRACKING = {
  "nytimes.com": /^(action|module|region|version|hp|referer|nl|te|src|pagewanted)$/i,
  "wsj.com": /^mod$/i,
  "theatlantic.com": /^single_page$/i,
  "newyorker.com": /^currentpage$/i,
  "washingtonpost.com": /^(tid|noredirect)$/i,
  "economist.com": /^(frsc|cid1)$/i,
  "statnews.com": /^mod$/i,
};

// A parameter copied out of a page's source keeps the "amp;" of its "&amp;".
const ESCAPED_AMPERSAND = /^(amp;)+/i;

// Leading host labels that serve the same article as the bare host.
const SAME_SITE_LABELS = /^(www|m|mobile|amp|edition)\./;

// Hosts that serve one site under two names: an edition, a mobile or text form, a
// renamed site. Each was seen serving one article at one path under both names.
const HOST_ALIASES = {
  "bbc.co.uk": "bbc.com",
  "us.cnn.com": "cnn.com",
  "lite.cnn.com": "cnn.com",
  "www-m.cnn.com": "cnn.com",
  "edition-m.cnn.com": "cnn.com",
  "uk.businessinsider.com": "businessinsider.com",
  "nordic.businessinsider.com": "businessinsider.com",
  "beta.washingtonpost.com": "washingtonpost.com",
  "beta.techcrunch.com": "techcrunch.com",
  "social.techcrunch.com": "techcrunch.com",
  "eu.usatoday.com": "usatoday.com",
  "text.npr.org": "npr.org",
  "motherboard.vice.com": "vice.com",
  "tonic.vice.com": "vice.com",
  "europe.newsweek.com": "newsweek.com",
  "institutions.newscientist.com": "newscientist.com",
  "beta.scmp.com": "scmp.com",
  "beta.latimes.com": "latimes.com",
  "next.ft.com": "ft.com",
  "prime.nautil.us": "nautil.us",
  "x.com": "twitter.com",
  "old.reddit.com": "reddit.com",
  "new.reddit.com": "reddit.com",
  "np.reddit.com": "reddit.com",
};

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

  let host = url.hostname.toLowerCase().replace(/^\.+|\.+$/g, "");
  while (SAME_SITE_LABELS.test(host)) host = host.replace(SAME_SITE_LABELS, "");
  host = Object.hasOwn(HOST_ALIASES, host) ? HOST_ALIASES[host] : host;
  if (!host) return null;

  // An escape is the same character in either letter case, and a doubled slash the same
  // place as a single one.
  let path = url.pathname
    .replace(/%[0-9a-f]{2}/gi, (escape) => escape.toUpperCase())
    .replace(/\/{2,}/g, "/")
    .replace(/\/+$/, "")
    .replace(/\/index\.html?$/i, "")
    .replace(/(\/amp|\.amp)$/i, "")
    .replace(/^\/amp(?=\/)/i, "");
  // CNN's AMP host repeats the site name as the first part of the path.
  if (host === "cnn.com") path = path.replace(/^\/cnn(?=\/)/, "");
  // A Daily Mail article is its number; the words after it vary and are often cut short.
  const mail = host === "dailymail.co.uk" && path.match(/\/article-(\d+)(\/|$)/);
  if (mail) path = `/article-${mail[1]}`;

  const outlet = Object.hasOwn(OUTLET_TRACKING, host) ? OUTLET_TRACKING[host] : null;
  const kept = [...url.searchParams.entries()]
    .map(([name, value]) => [name.replace(ESCAPED_AMPERSAND, ""), value])
    .filter(([name]) => !TRACKING.test(name) && !outlet?.test(name))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, value]) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`);

  return host + path + (kept.length ? `?${kept.join("&")}` : "");
}
