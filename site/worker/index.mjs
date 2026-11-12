// The site's Worker. Every address but one is a file of the built site. /api/lookup
// answers a reader's question about an article the site does not track, or about a post
// that links to one: which trial records is this about? Behaviour: openspec live-lookup.
//
// Nothing a reader sends is stored or logged here: not the address, not the text, not
// the answer. The reader's network address is used once, to count requests per minute.
import { PLATFORM_NAMES, readAddress } from "../src/lib/lookup-match.mjs";
import { MAX_TEXT_CHARACTERS, readArticle } from "./article.mjs";
import { lookUp } from "./lookup.mjs";
import { makeModel } from "./model.mjs";
import { linkSignals } from "./page.mjs";
import { makePapers } from "./papers.mjs";
import { readPost } from "./post.mjs";
import { makeRegistry } from "./registry.mjs";
import { followShort } from "./short.mjs";

const PATH = "/api/lookup";
// What a reader's browser may send with text it read: this many links, each this long.
const MAX_LINKS = 30;
const MAX_LINK_CHARACTERS = 500;
// The most shortened links followed for one post.
const MAX_SHORT_LINKS = 3;
const UNREADABLE = { robots: "unreadable_robots", unreadable: "unreadable", address: "address" };

function answer(body, status = 200) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}
const refuse = (status, error, more = {}) => answer({ error, ...more }, status);

function realTools(env) {
  return {
    model: makeModel({
      fetch,
      apiKey: env.OPENAI_API_KEY,
      model: env.LLM_MODEL,
      baseUrl: env.LLM_BASE_URL || undefined,
      // The same setting as the pipeline's: which backend scores the records.
      decisions: env.DECISION_BACKEND === "openai-decisions",
      decisionsModel: env.DECISIONS_MODEL || undefined,
    }),
    registry: makeRegistry({ fetch, contact: env.CONTACT_EMAIL }),
    papers: makePapers({ fetch, contact: env.CONTACT_EMAIL }),
    fetch,
  };
}

/** The claims that cite this article, as the site lists them. */
function trackedBy(index, articleKey) {
  return (index.articles?.[articleKey] ?? [])
    .filter((slug) => index.claims?.[slug])
    .map((slug) => ({ slug, headline: index.claims[slug].headline, page: index.claims[slug].page }));
}

/**
 * A post and the article it links to, read together. The first link in the post that is
 * an article's address is followed; a link to another post or a shortened link is not.
 * @returns the text to look up, what the article's page says of itself, and where it all
 *   came from; or `refused` when the post itself cannot be read.
 */
async function readPostAndArticle(read, index, { fetch, contact }) {
  const post = await readPost(read.post, { fetch, contact });
  if (post.refused) return { refused: post.refused };
  return withLinkedArticle(read.platform, post, index, { fetch, contact });
}

/**
 * A post's text and links, however they were read, and the article the post links to.
 * @param {{ text: string, links: string[] }} post
 */
async function withLinkedArticle(platform, post, index, { fetch, contact }) {
  // A shortened link is followed to where it leads, where its shortener allows.
  let followed = 0;
  const read = [];
  for (const link of post.links) {
    let one = readAddress(link);
    if (one.kind === "short" && followed < MAX_SHORT_LINKS) {
      followed += 1;
      const leadsTo = await followShort(link, { fetch, contact });
      if (leadsTo) one = readAddress(leadsTo);
    }
    read.push(one);
    if (one.kind === "article") break;
  }
  const linked = read.find((one) => one.kind === "article");
  const source = {
    platform,
    article: linked?.address ?? null,
    article_host: linked?.host ?? null,
    article_read: false,
  };
  // What is left is a shortened link whose shortener does not let software follow it.
  if (!linked && read.some((one) => one.kind === "short")) source.only_short_links = true;
  const said = `A post on ${platform} says:\n${post.text}`;
  if (!linked) return { text: said, source };
  // An article the site tracks has a reviewed page: that is the answer. The article is
  // not fetched and no automatic search is made in its place.
  const tracked = trackedBy(index, linked.key);
  if (tracked.length) return { tracked, source };
  const article = await readArticle(linked.address, { fetch, contact });
  if (article.refused) return { text: said, source };
  return {
    text: `${said}\n\nThe article it links to:\n${article.text}`.slice(0, MAX_TEXT_CHARACTERS),
    page: article.page,
    source: { ...source, article_read: true },
  };
}

/** @param {{ model: object, registry: object, papers?: object, fetch?: Function } | undefined} tools stand-ins, for tests */
export async function handle(request, env, tools) {
  const here = new URL(request.url);
  if (here.pathname !== PATH) return env.ASSETS.fetch(request);
  if (request.method !== "POST") return refuse(405, "method");
  if (!env.OPENAI_API_KEY || !env.LLM_MODEL || !env.CONTACT_EMAIL) return refuse(503, "not_set_up");

  const sent = await request.json().catch(() => null);
  const address = typeof sent?.url === "string" ? sent.url.trim() : "";
  let text = typeof sent?.text === "string" ? sent.text.trim() : "";
  if (!address && !text) return refuse(400, "nothing_given");
  if (text.length > MAX_TEXT_CHARACTERS) return refuse(413, "too_long");
  // Text may come with the links that stood in it, and with the name of the platform it
  // was a post on: what a reader's own browser read from the page they had open. The
  // page's address is not asked for and is not sent.
  const links = (Array.isArray(sent?.links) ? sent.links : [])
    .filter((link) => typeof link === "string" && link.length <= MAX_LINK_CHARACTERS && /^https?:\/\//i.test(link))
    .slice(0, MAX_LINKS);
  const platform = PLATFORM_NAMES.includes(sent?.platform) ? sent.platform : null;

  let read = null;
  if (!text) {
    read = readAddress(address);
    if (read.kind === "none") return refuse(400, "address");
    // A shortened link does not say which article it is; the reader opens it first.
    if (read.kind === "short") return refuse(422, "short");
    // A post on a platform that does not offer posts to software: the reader pastes its text.
    if (read.kind === "post" && !read.readable) return refuse(422, "post", { platform: read.platform });
  }

  const reader = request.headers.get("CF-Connecting-IP") ?? "unknown";
  const limits = await Promise.all([
    env.LOOKUP_PER_READER.limit({ key: reader }),
    env.LOOKUP_IN_ALL.limit({ key: "all" }),
  ]);
  if (limits.some((limit) => !limit.success)) return refuse(429, "busy");

  try {
    const { model, registry, papers, fetch: get = fetch } = tools ?? realTools(env);
    const index = await env.ASSETS.fetch(new Request(new URL("/lookup.json", here)))
      .then((response) => (response.ok ? response.json() : { claims: {} }))
      .catch(() => ({ claims: {} }));

    let page;
    let post = null;
    if (read?.kind === "article") {
      const article = await readArticle(read.address, { fetch: get, contact: env.CONTACT_EMAIL });
      if (article.refused) return refuse(422, UNREADABLE[article.refused]);
      text = article.text;
      page = article.page;
    } else if (read?.kind === "post") {
      const both = await readPostAndArticle(read, index, { fetch: get, contact: env.CONTACT_EMAIL });
      if (both.refused) return refuse(422, both.refused, { platform: read.platform });
      post = both.source;
      if (both.tracked) return answer({ article_tracked: true, post, tracked: both.tracked, candidates: [] });
      text = both.text;
      page = both.page;
    } else if (platform) {
      // A post the reader's browser read: the article it links to is read here, as for
      // a post this service read itself.
      const both = await withLinkedArticle(platform, { text, links }, index, { fetch: get, contact: env.CONTACT_EMAIL });
      post = { ...both.source, read_in_browser: true };
      if (both.tracked) return answer({ article_tracked: true, post, tracked: both.tracked, candidates: [] });
      text = both.text;
      page = both.page;
    } else if (links.length) {
      // An article the reader's browser read: its links still say which paper it reports.
      page = linkSignals(links, text);
    }
    return answer({ ...(await lookUp({ text, model, registry, index, page, papers })), post });
  } catch {
    // What failed may quote what was sent, so it is not written anywhere.
    return refuse(502, "failed");
  }
}

export default { fetch: (request, env) => handle(request, env) };
