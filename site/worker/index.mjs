// The site's Worker. Every address but one is a file of the built site. /api/lookup
// answers a reader's question about an article the site does not track, or about a post
// that links to one: which trial records is this about? Behaviour: openspec live-lookup.
//
// Raw requests are never stored or logged. Independently public structured answers
// may be cached briefly under a URL digest. Network addresses only count request rates.
import { PLATFORM_NAMES, readAddress } from "../src/lib/lookup-match.mjs";
import { MAX_TEXT_CHARACTERS, readArticle } from "./article.mjs";
import { lookUp } from "./lookup.mjs";
import { SITE } from "../site.config.mjs";
import { goneList, gonePage } from "./gone.mjs";
import { makeModel } from "./model.mjs";
import { linkSignals } from "./page.mjs";
import { makePapers } from "./papers.mjs";
import { readPost } from "./post.mjs";
import { makeRegistry } from "./registry.mjs";
import { followShort } from "./short.mjs";
import { readBody, sourceUrl, validateImage } from "./visual.mjs";
import { previousResult, storeResult } from "./results.mjs";
import { makeResearch } from "./research.mjs";

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
    research: makeResearch({ fetch, apiKey: env.OPENALEX_API_KEY, contact: env.CONTACT_EMAIL, cache: env.LOOKUP_RESULTS }),
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
  if (here.pathname !== PATH) {
    // A page the operator archived answers 410; everything else is a file of the site.
    const slug = here.pathname.replace(/^\/+|\/+$/g, "");
    if (slug && !slug.includes("/") && !slug.includes(".")) {
      const on = (await goneList(env.ASSETS, here.origin)).get(slug);
      if (on) {
        return new Response(gonePage(on, SITE.name), {
          status: 410,
          headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=3600" },
        });
      }
    }
    return env.ASSETS.fetch(request);
  }
  if (request.method !== "POST") return refuse(405, "method");
  if (!env.OPENAI_API_KEY || !env.LLM_MODEL || !env.CONTACT_EMAIL) return refuse(503, "not_set_up");

  let sent, image;
  try { sent = await readBody(request); image = validateImage(sent?.image); }
  catch (error) { return refuse(error.status ?? 400, error.code ?? "image_invalid"); }
  const pageUrl = sourceUrl(sent?.pageUrl);
  if (sent?.cacheOnly === true) {
    const reader = request.headers.get("CF-Connecting-IP") ?? "unknown";
    const limits = await Promise.all([env.LOOKUP_PER_READER.limit({ key: reader }), env.LOOKUP_IN_ALL.limit({ key: "all" })]);
    if (limits.some(limit => !limit.success)) return refuse(429, "busy");
    return answer(await previousResult(env.LOOKUP_RESULTS, pageUrl) ?? { cacheMiss: true });
  }
  const address = typeof sent?.url === "string" ? sent.url.trim() : "";
  let text = typeof sent?.text === "string" ? sent.text.trim() : "";
  if (text.length > MAX_TEXT_CHARACTERS) return refuse(413, "too_long");
  // Text may come with the links that stood in it, and with the name of the platform it
  // was a post on: what a reader's own browser read from the page they had open. The
  // cleaned page address is optional and identifies an earlier public result.
  const links = (Array.isArray(sent?.links) ? sent.links : [])
    .filter((link) => typeof link === "string" && link.length <= MAX_LINK_CHARACTERS && /^https?:\/\//i.test(link))
    .slice(0, MAX_LINKS);
  const platform = PLATFORM_NAMES.includes(sent?.platform) ? sent.platform : null;
  const linkedBrowserPost = !address && platform !== null && links.length > 0;
  if (!address && !text && !linkedBrowserPost && !image) return refuse(400, "nothing_given");

  let read = null;
  if (!text && !linkedBrowserPost && !image) {
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

  // A caller's context URL must never relabel a different independently fetched URL.
  const cacheUrl = address ? sourceUrl(address) : pageUrl;
  if (!image && sent?.refresh !== true && cacheUrl) {
    const cached = await previousResult(env.LOOKUP_RESULTS, cacheUrl);
    if (cached) return answer(cached);
  }

  try {
    const { model, registry, papers, research, fetch: get = fetch } = tools ?? realTools(env);
    const index = await env.ASSETS.fetch(new Request(new URL("/lookup.json", here)))
      .then((response) => (response.ok ? response.json() : { claims: {} }))
      .catch(() => ({ claims: {} }));

    let page;
    let post = null;
    let publicVerified = false;
    if (read?.kind === "article") {
      const article = await readArticle(read.address, { fetch: get, contact: env.CONTACT_EMAIL });
      if (article.refused) return refuse(422, UNREADABLE[article.refused]);
      text = article.text;
      page = article.page;
      publicVerified = true;
    } else if (read?.kind === "post") {
      const both = await readPostAndArticle(read, index, { fetch: get, contact: env.CONTACT_EMAIL });
      if (both.refused) return refuse(422, both.refused, { platform: read.platform });
      post = both.source;
      if (both.tracked) return answer({ article_tracked: true, post, tracked: both.tracked, candidates: [] });
      text = both.text;
      page = both.page;
      publicVerified = true;
    } else if (platform && !image) {
      // A post the reader's browser read: the article it links to is read here, as for
      // a post this service read itself.
      const both = await withLinkedArticle(platform, { text, links }, index, { fetch: get, contact: env.CONTACT_EMAIL });
      post = { ...both.source, read_in_browser: true };
      if (both.tracked) return answer({ article_tracked: true, post, tracked: both.tracked, candidates: [] });
      if (!text && !both.source.article_read) return refuse(422, "post_unreadable", { platform });
      text = both.text;
      page = both.page;
    } else if (links.length) {
      // An article the reader's browser read: its links still say which paper it reports.
      page = linkSignals(links, text);
    }
    // Browser-supplied content is never proof that a page is public. For a readable
    // source, obtain independent anonymous evidence before making its result shared.
    // Platforms which disallow server reading (including Reddit) stay browser-local.
    if (!publicVerified && !image && cacheUrl && env.LOOKUP_RESULTS) {
      const context = readAddress(cacheUrl);
      if (context.kind === "article") {
        const proof = await readArticle(context.address, { fetch: get, contact: env.CONTACT_EMAIL });
        if (!proof.refused && !image && !platform) {
          // Use the independently public article itself, rather than publishing a
          // client's private/personalised additions under an otherwise public URL.
          text = proof.text;
          page = proof.page;
          publicVerified = true;
        }
      }
      // Visual contents can differ from what an anonymous reader sees. They are not
      // published merely because the surrounding article is accessible.
    }
    const found = { ...(await lookUp({ text, model, registry, index, page, papers, research, image, pageUrl })), post,
      ...(image ? { source: { kind: "screenshot", host: pageUrl ? new URL(pageUrl).hostname : null } } : {}) };
    await storeResult(env.LOOKUP_RESULTS, cacheUrl, found, publicVerified);
    return answer(found);
  } catch (error) {
    // What failed may quote what was sent, so it is not written anywhere.
    if (error?.code === "budget_exhausted") return refuse(503, "budget_exhausted");
    return refuse(502, "failed");
  }
}

export default { fetch: (request, env) => handle(request, env) };
