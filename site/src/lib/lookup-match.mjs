// Reading an address a reader pastes, and finding tracked claims close to it.
// Plain JavaScript, pure: no network and no page. Shared with the browser extension.
import { articleKey } from "./article-key.mjs";

// Links that only reveal their article when opened.
const SHORTENERS = new Set([
  "t.co", "bit.ly", "tinyurl.com", "ow.ly", "buff.ly", "lnkd.in", "fb.me", "goo.gl", "trib.al",
  "dlvr.it", "ift.tt", "is.gd", "rb.gy", "shorturl.at", "tiny.cc", "cutt.ly", "flip.it",
  "apple.news", "news.google.com", "share.google", "search.app", "redd.it", "youtu.be",
  "bbc.in", "nyti.ms", "wapo.st", "reut.rs", "cnn.it", "dailym.ai", "mol.im", "tgr.ph", "ind.pn",
  "econ.st", "n.pr", "gu.com", "on.ft.com", "fxn.ws", "nyp.st", "thesun.uk", "mirror.co",
]);

// Platforms where an address is a post or a video, not a news article: the name a reader
// knows it by, and its hosts.
const PLATFORMS = [
  ["X", ["x.com", "twitter.com"]],
  ["Facebook", ["facebook.com", "fb.com", "fb.watch"]],
  ["Instagram", ["instagram.com"]],
  ["Threads", ["threads.net", "threads.com"]],
  ["Reddit", ["reddit.com"]],
  ["LinkedIn", ["linkedin.com"]],
  ["TikTok", ["tiktok.com"]],
  ["YouTube", ["youtube.com"]],
  ["Bluesky", ["bsky.app"]],
  ["Telegram", ["t.me"]],
  ["Pinterest", ["pinterest.com"]],
  ["WhatsApp", ["whatsapp.com"]],
  ["Mastodon", ["mastodon.social"]],
  ["Hacker News", ["news.ycombinator.com"]],
];

/**
 * Which post an address is, on the platforms whose posts the lookup service can read:
 * each offers them to software without signing in (docs/sources.md). Null for any other
 * address, including a platform's pages that are not one post.
 * @returns {{ platform: string, how: "bluesky" | "hackernews" | "mastodon", host: string,
 *   actor?: string, id: string } | null}
 */
function readablePost(url, host) {
  if (host === "bsky.app") {
    const post = url.pathname.match(/^\/profile\/([^/]+)\/post\/([a-z0-9]+)\/?$/i);
    return post ? { platform: "Bluesky", how: "bluesky", host, actor: decodeURIComponent(post[1]), id: post[2] } : null;
  }
  if (host === "news.ycombinator.com") {
    const id = url.pathname === "/item" ? url.searchParams.get("id") : null;
    return id && /^\d+$/.test(id) ? { platform: "Hacker News", how: "hackernews", host, id } : null;
  }
  // A post on any Mastodon server has this shape, whatever the server is called.
  const toot = url.pathname.match(/^\/(?:@[^/]+|users\/[^/]+\/statuses)\/(\d{6,})\/?$/);
  return toot ? { platform: "Mastodon", how: "mastodon", host: url.hostname.toLowerCase(), id: toot[1] } : null;
}

// Redirect pages that carry the real address in a parameter: host (and path) to parameter names.
const WRAPPERS = [
  ["l.facebook.com", "", ["u"]],
  ["lm.facebook.com", "", ["u"]],
  ["l.messenger.com", "", ["u"]],
  ["l.instagram.com", "", ["u"]],
  ["out.reddit.com", "", ["url"]],
  ["google.com", "/url", ["url", "q"]],
  ["linkedin.com", "/redir/", ["url"]],
  ["slack-redir.net", "", ["url"]],
  ["youtube.com", "/redirect", ["q"]],
  ["away.vk.com", "", ["to"]],
  ["t.umblr.com", "", ["z"]],
];

const ARCHIVES = /^(web\.archive\.org|archive\.(ph|today|is|md|li|vn|fo)|12ft\.io|removepaywall\.com)$/;

function bare(host) {
  return host.toLowerCase().replace(/^www\./, "");
}

function parse(input) {
  const text = String(input ?? "").trim();
  if (!text || /\s/.test(text)) return null;
  const withScheme = /^https?:\/\//i.test(text)
    ? text
    : /^[a-z0-9-]+(\.[a-z0-9-]+)+(\/\S*)?$/i.test(text)
      ? `https://${text}`
      : null;
  if (!withScheme) return null;
  try {
    return new URL(withScheme);
  } catch {
    return null;
  }
}

function tryUrl(text) {
  try {
    const url = new URL(text.replace(/^(https?):\/(?!\/)/i, "$1://"));
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

/** The address inside a redirect, cache or archive link, or null when there is none. */
function unwrap(url) {
  const host = bare(url.hostname);
  for (const [site, pathStart, names] of WRAPPERS) {
    if (host !== site || !url.pathname.startsWith(pathStart)) continue;
    for (const name of names) {
      const inner = url.searchParams.get(name);
      if (inner) return tryUrl(inner);
    }
  }
  // AMP caches: /c/s/host/path, or Google's /amp/s/host/path.
  const amp =
    (host.endsWith(".cdn.ampproject.org") && url.pathname.match(/^\/[a-z]\/(s\/)?(.+)$/)) ||
    (host === "google.com" && url.pathname.match(/^\/amp\/(s\/)?(.+)$/));
  if (amp) return tryUrl(`https://${amp[2]}`);
  // Archives and paywall readers keep the original address in the path.
  if (ARCHIVES.test(host)) {
    const at = url.href.search(/\/https?:\/{1,2}/i);
    if (at > url.origin.length - 1) return tryUrl(url.href.slice(at + 1));
  }
  return null;
}

/**
 * What a pasted piece of text is.
 * @param {string} input
 * @returns {{ kind: "article", key: string, address: string, host: string }
 *   | { kind: "post", host: string, platform: string, readable: boolean, address?: string, post?: object }
 *   | { kind: "short", host: string } | { kind: "none" }}
 *   A post is `readable` when the lookup service can read it by its address; `post` then
 *   says which post it is.
 */
export function readAddress(input) {
  let url = parse(input);
  if (!url) return { kind: "none" };
  for (let depth = 0; depth < 3; depth += 1) {
    const inner = unwrap(url);
    if (!inner) break;
    url = inner;
  }
  const host = bare(url.hostname);
  if (SHORTENERS.has(host) || (ARCHIVES.test(host) && url.pathname.split("/").length <= 2)) {
    return { kind: "short", host };
  }
  const post = readablePost(url, host);
  if (post) return { kind: "post", host, platform: post.platform, readable: true, address: url.href, post };
  const platform = PLATFORMS.find(([, sites]) => sites.some((site) => host === site || host.endsWith(`.${site}`)));
  if (platform) return { kind: "post", host, platform: platform[0], readable: false };
  const key = articleKey(url.href);
  return key === null ? { kind: "none" } : { kind: "article", key, address: url.href, host };
}

// --- closest matches ---------------------------------------------------------

// Words nearly every health story or address has. Sharing one says nothing.
const COMMON = new Set(
  `the and for with from that this these those into over after before about could would should may
  might can will has have had was were are its their your our new news study studies scientists
  scientist researchers research breakthrough health science medical medicine article articles
  story stories world life tech html htm amp index www com org says say said shows show found
  finds find reveal reveals first how why what when who treatment treatments drug drugs cure
  cures patients patient people disease diseases trial trials clinical doctors doctor hope hopes
  year years major huge big experts expert test tests tested results result report reports
  reported latest today week uk usa video watch live update`.split(/\s+/),
);

function words(text) {
  return String(text ?? "")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length >= 3 && !/^\d+$/.test(word) && !COMMON.has(word))
    .map((word) => (word.length > 4 && word.endsWith("s") && !word.endsWith("ss") ? word.slice(0, -1) : word));
}

/**
 * Tracked claims whose names or reports share words with the words in an address.
 * A guess for the reader to check, never a statement that the article is tracked.
 *
 * @param {{ claims: Record<string, { headline: string, names?: string[], terms?: string }> }} index
 * @param {string} address
 * @returns {{ slug: string, claim: object, shared: string[] }[]} closest first
 */
export function closestClaims(index, address, limit = 5) {
  const url = parse(address);
  if (!url) return [];
  const asked = new Set(words(decodeURIComponent(url.pathname)));
  if (asked.size === 0) return [];

  const claims = Object.entries(index.claims).map(([slug, claim]) => ({
    slug,
    claim,
    names: new Set(words((claim.names ?? []).join(" "))),
    all: new Set(words(`${claim.headline} ${(claim.names ?? []).join(" ")} ${claim.terms ?? ""}`)),
  }));
  const spread = new Map();
  for (const entry of claims) for (const word of entry.all) spread.set(word, (spread.get(word) ?? 0) + 1);

  return claims
    .map((entry) => {
      const shared = [...asked].filter((word) => entry.all.has(word));
      // A word found in few claims says more than one found in many.
      const score = shared.reduce((sum, word) => sum + 1 / Math.sqrt(spread.get(word)), 0);
      // One shared word is enough only when it is the treatment's own name or a code name.
      const named = shared.some((word) => entry.names.has(word) || /\d/.test(word));
      return { slug: entry.slug, claim: entry.claim, shared, score, close: shared.length >= 2 || named };
    })
    .filter((entry) => entry.close)
    .sort((a, b) => b.score - a.score || a.slug.localeCompare(b.slug))
    .slice(0, limit)
    .map(({ slug, claim, shared }) => ({ slug, claim, shared }));
}
