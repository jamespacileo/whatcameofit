// Reading one social media post by its address: its text and the links in it. Only on
// platforms that offer posts to software without signing in; terms and limits are in
// docs/sources.md. The text and the links are returned to the caller and kept nowhere,
// and who wrote the post is never read out.
import { allowedByRobots, client, isPublic } from "./article.mjs";

const BLUESKY = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread";
const HACKER_NEWS = "https://hacker-news.firebaseio.com/v0/item";
const MAX_POST_CHARACTERS = 4000;
const ENTITIES = { nbsp: " ", amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };

const unique = (items) => [...new Set(items.filter(Boolean))];

/** The text of a piece of HTML, and the addresses it links to that are not tags or mentions. */
function fromHtml(html) {
  const source = String(html ?? "");
  const links = [...source.matchAll(/<a\b([^>]*)>/gi)]
    .map(([, attributes]) => attributes)
    .filter((attributes) => !/class\s*=\s*["'][^"']*\b(mention|hashtag)\b/i.test(attributes))
    .map((attributes) => attributes.match(/href\s*=\s*["']([^"']+)["']/i)?.[1])
    .filter(Boolean)
    .map(decoded);
  // A paragraph or a line break ends a line; any other tag is only markup around words.
  const text = decoded(source.replace(/<\/?(p|br|div|li)\b[^>]*>/gi, "\n").replace(/<[^>]+>/g, ""));
  return { text, links };
}

function decoded(text) {
  return text
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&([a-z]+);/gi, (whole, name) => ENTITIES[name.toLowerCase()] ?? whole);
}

const tidy = (text) => String(text ?? "").replace(/[ \t]+/g, " ").replace(/\s*\n\s*/g, "\n").trim();

async function bluesky(post, get) {
  const url = new URL(BLUESKY);
  url.searchParams.set("uri", `at://${post.actor}/app.bsky.feed.post/${post.id}`);
  url.searchParams.set("depth", "0");
  url.searchParams.set("parentHeight", "0");
  const answered = await get(url.href);
  const found = answered?.thread?.post;
  if (!found?.record) return null;
  const card = found.embed?.external ?? found.record.embed?.external ?? {};
  const inText = (found.record.facets ?? []).flatMap((facet) => facet.features ?? []).map((feature) => feature.uri);
  // The card a post carries for its link is the linked page's own headline and summary.
  const about = [card.title, card.description].filter(Boolean).join(". ");
  return {
    text: [found.record.text, about && `The page it links to: ${about}`].filter(Boolean).join("\n"),
    links: [card.uri, ...inText],
  };
}

async function hackerNews(post, get) {
  const item = await get(`${HACKER_NEWS}/${post.id}.json`);
  if (!item || item.deleted || item.dead) return null;
  const body = fromHtml(item.text);
  return { text: [item.title, body.text].filter(Boolean).join("\n"), links: [item.url, ...body.links] };
}

async function mastodon(post, get, { fetch, contact }) {
  const url = new URL(`https://${post.host}/api/v1/statuses/${post.id}`);
  // Any server can be a Mastodon server, so this one is asked like any site: only if it
  // is public and its own rules allow it.
  if (!isPublic(url) || !(await allowedByRobots(url, { fetch, contact }))) return null;
  const status = await get(url.href);
  if (!status || status.visibility !== "public" || typeof status.content !== "string") return null;
  const body = fromHtml(status.content);
  const about = [status.card?.title, status.card?.description].filter(Boolean).join(". ");
  return {
    text: [body.text, about && `The page it links to: ${about}`].filter(Boolean).join("\n"),
    links: [status.card?.url, ...body.links],
  };
}

const READERS = { bluesky, hackernews: hackerNews, mastodon };

/**
 * @param {{ how: string, host: string, actor?: string, id: string }} post from readAddress
 * @returns {Promise<{ text: string, links: string[] } | { refused: "post_unreadable" }>}
 *   A post that is private, deleted or not there is refused, as is one whose platform fails.
 */
export async function readPost(post, { fetch, contact }) {
  const get = async (address) => {
    try {
      const response = await fetch(address, { headers: { ...client(contact), Accept: "application/json" } });
      return response.ok ? await response.json() : null;
    } catch {
      return null;
    }
  };
  const read = await READERS[post.how]?.(post, get, { fetch, contact });
  const text = tidy(read?.text).slice(0, MAX_POST_CHARACTERS);
  if (!read || !text) return { refused: "post_unreadable" };
  return { text, links: unique(read.links).filter((link) => /^https?:\/\//i.test(link)) };
}
