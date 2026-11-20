// The site's Worker. Static pages, readable trial records, and /api/lookup, which
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
import { linkSignals, publishedIn } from "./page.mjs";
import { makePapers } from "./papers.mjs";
import { readPost } from "./post.mjs";
import { makeRegistry } from "./registry.mjs";
import { followShort } from "./short.mjs";
import { readBody, sourceUrl, validateImage } from "./visual.mjs";
import { previousResult, storeResult } from "./results.mjs";
import { withCurrentClaims } from "./tracked.mjs";
import { bounded } from "./public-cache.mjs";
import { makeResearch } from "./research.mjs";
import { eventStream, serverTiming, stageTimes } from "./stream.mjs";
import { handleTrial } from "./trials.mjs";
import { releaseFile } from "./site-release.mjs";

const PATH = "/api/lookup";
// What a reader's browser may send with text it read: this many links, each this long.
const MAX_LINKS = 30;
const MAX_LINK_CHARACTERS = 500;
// The most shortened links followed for one post.
const MAX_SHORT_LINKS = 3;
// An independent reading that would let a browser-read result be shared. It is only
// worth this long: past it the reader's own content is searched and nothing is shared.
const PROOF_TIMEOUT_MS = 3_000;
// Reading today's static cards must not hold up a completed saved clinical answer.
const INDEX_TIMEOUT_MS = 500;
const UNREADABLE = { robots: "unreadable_robots", unreadable: "unreadable", address: "address" };

function answer(body, status = 200, timings = null) {
  const timing = serverTiming(timings);
  return Response.json(body, { status, headers: { "Cache-Control": "no-store", ...(timing ? { "Server-Timing": timing } : {}) } });
}
const refuse = (status, error, more = {}) => answer({ error, ...more }, status);
// The same refusal, before it is known whether it is answered as JSON or as an event.
const refusal = (status, error, more = {}) => ({ status, body: { error, ...more } });
// A pre-upgrade caller must never mistake the first item for coverage of a roundup.
const unsupportedClaims = (found, sent) => Array.isArray(found?.claims) && sent?.claimResults !== true;

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
    // Public registry and paper answers are reused briefly; see worker/public-cache.mjs.
    registry: makeRegistry({ fetch, contact: env.CONTACT_EMAIL, cache: env.LOOKUP_RESULTS }),
    papers: makePapers({ fetch, contact: env.CONTACT_EMAIL, cache: env.LOOKUP_RESULTS }),
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
// A claim's own files, by its slug, and where each leads when the claim leads to a pair: the
// pair's embed, oEmbed, cards and open data record, and, for the claim's own feed, the site's
// feed of status changes (a pair has no feed of its own).
const CLAIM_FILES = [
  [/^\/embed\/([a-z0-9-]+)\/?$/, (to) => `/embed/${to}`],
  [/^\/oembed\/([a-z0-9-]+)\.json$/, (to) => `/oembed/${to}.json`],
  [/^\/og\/([a-z0-9-]+)\.png$/, (to) => `/og/${to}.png`],
  [/^\/og\/square\/([a-z0-9-]+)\.png$/, (to) => `/og/square/${to}.png`],
  [/^\/og\/tall\/([a-z0-9-]+)\.png$/, (to) => `/og/tall/${to}.png`],
  [/^\/data\/claims\/([a-z0-9-]+)\.json$/, (to) => `/data/pairs/${to}.json`],
  [/^\/changes\/([a-z0-9-]+)\.xml$/, () => "/changes.xml"],
];

/** Which claim file a path is, by the claim's slug, or null. */
export function claimAsset(pathname) {
  for (const [pattern, at] of CLAIM_FILES) {
    const slug = pattern.exec(pathname)?.[1];
    if (slug) return { slug, at };
  }
  return null;
}

export async function handle(request, env, tools) {
  const started = Date.now();
  const here = new URL(request.url);
  if (here.pathname.startsWith("/trials/")) return handleTrial(request, env, tools?.trial);
  // The built reader is a server template, never a public page of placeholders.
  if (/^\/trial-reader(?:\/|\.html|\/index(?:\.html)?)?$/.test(here.pathname)) {
    return new Response("Not found", { status: 404, headers: { "Cache-Control": "no-store" } });
  }
  if (here.pathname !== PATH) {
    // A claim that leads to its pair (`pair: true` in gone.json, written only by a build that
    // reads a bundle, openspec pairs-site 3.4a): the build made none of its files, and each
    // file's address leads to the pair's own. Its page's address is handled below.
    const asset = claimAsset(here.pathname);
    if (asset) {
      const { to, pair } = (await goneList(env.ASSETS, here.origin)).get(asset.slug) ?? {};
      const target = to && pair ? asset.at(to) : null;
      if (target && target !== here.pathname) {
        return new Response(null, {
          status: 301,
          headers: { Location: new URL(`${target}${here.search}`, here.origin).href, "Cache-Control": "public, max-age=300" },
        });
      }
    }
    // A page the operator archived answers 410; everything else is a file of the site.
    const slug = here.pathname.replace(/^\/+|\/+$/g, "");
    if (slug && !slug.includes("/") && !slug.includes(".")) {
      const { on, to } = (await goneList(env.ASSETS, here.origin)).get(slug) ?? {};
      // A claim merged into another, or renamed: its address leads to the page it is at now.
      // A claim whose slug is its pair's address leads nowhere: the pair's page is the file.
      if (to && to !== slug) {
        return new Response(null, {
          status: 301,
          // Kept for five minutes only, so a merge that is undone stops redirecting soon after the next deploy.
          headers: { Location: new URL(`/${to}${here.search}`, here.origin).href, "Cache-Control": "public, max-age=300" },
        });
      }
      if (on) {
        return new Response(gonePage(on, SITE.name), {
          status: 410,
          headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=3600" },
        });
      }
    }
    return await releaseFile(request, here, env) ?? env.ASSETS.fetch(request);
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
    const cached = await currentResult(env, pageUrl, here);
    return unsupportedClaims(cached, sent) ? refuse(409, "multiple_claims") : answer(cached ?? { cacheMiss: true });
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
    const cached = await currentResult(env, cacheUrl, here);
    if (cached) return unsupportedClaims(cached, sent) ? refuse(409, "multiple_claims") : answer(cached);
  }

  // An opted-in caller is answered in stages: the completed clinical answer as soon as
  // it is ready, then the answer with research enrichment. Others get one JSON answer.
  const work = (onCore, timings) => lookUpFor({ sent, read, text, links, platform, image, pageUrl, cacheUrl, here, env, tools, onCore, timings, started });
  if (sent?.stream !== true) {
    const timings = {};
    const { status, body, keep } = await work(null, timings);
    await keep?.();
    return answer(body, status, status === 200 ? timings : null);
  }
  return eventStream(async (send) => {
    const timings = {};
    const { status, body, keep } = await work((core) => send({ type: "core", result: core, timings: stageTimes(timings) }), timings);
    if (status !== 200) send({ type: "error", status, ...body });
    else send({ type: "complete", result: body, timings: stageTimes(timings) });
    // Kept once the reader has the whole answer, whether or not they are still reading.
    await keep?.();
  });
}

async function lookupIndex(env, here) {
  return env.ASSETS.fetch(new Request(new URL("/lookup.json", here)))
    .then(response => response.ok ? response.json() : { claims: {} })
    .catch(() => ({ claims: {} }));
}

async function currentResult(env, address, here) {
  const found = await previousResult(env.LOOKUP_RESULTS, address);
  if (found?.about_a_treatment !== true) return found;
  const index = await bounded(() => lookupIndex(env, here), INDEX_TIMEOUT_MS, { claims: {} });
  return withCurrentClaims(found, index);
}

/** One lookup after its request is accepted: a status, the body to answer with and, for
 * an answer, how to keep it for the next reader: only once complete, and only when public. */
async function lookUpFor({ sent, read, text, links, platform, image, pageUrl, cacheUrl, here, env, tools, onCore, timings, started }) {
  try {
    const { model, registry, papers, research, fetch: get = fetch, proofTimeoutMs = PROOF_TIMEOUT_MS,
      paperAllowanceMs, paperSpacingMs } = tools ?? realTools(env);
    const index = await lookupIndex(env, here);

    let page;
    let post = null;
    let publicVerified = false;
    if (read?.kind === "article") {
      const article = await readArticle(read.address, { fetch: get, contact: env.CONTACT_EMAIL });
      if (article.refused) return refusal(422, UNREADABLE[article.refused]);
      text = article.text;
      page = article.page;
      publicVerified = true;
    } else if (read?.kind === "post") {
      const both = await readPostAndArticle(read, index, { fetch: get, contact: env.CONTACT_EMAIL });
      if (both.refused) return refusal(422, both.refused, { platform: read.platform });
      post = both.source;
      if (both.tracked) return { status: 200, body: { article_tracked: true, post, tracked: both.tracked, candidates: [] } };
      text = both.text;
      page = both.page;
      publicVerified = true;
    } else if (platform && !image) {
      // A post the reader's browser read: the article it links to is read here, as for
      // a post this service read itself.
      const both = await withLinkedArticle(platform, { text, links }, index, { fetch: get, contact: env.CONTACT_EMAIL });
      post = { ...both.source, read_in_browser: true };
      if (both.tracked) return { status: 200, body: { article_tracked: true, post, tracked: both.tracked, candidates: [] } };
      if (!text && !both.source.article_read) return refusal(422, "post_unreadable", { platform });
      text = both.text;
      page = both.page;
    } else if (links.length || publishedIn(text)) {
      // An article the reader's browser read: its links still say which paper it reports,
      // and its opening lines when it was published.
      page = { ...linkSignals(links, text), published: publishedIn(text) };
    }
    // Browser-supplied content is never proof that a page is public. For a readable
    // source, obtain independent anonymous evidence before making its result shared.
    // Platforms which disallow server reading (including Reddit) stay browser-local.
    if (!publicVerified && !image && cacheUrl && env.LOOKUP_RESULTS) {
      const context = readAddress(cacheUrl);
      if (context.kind === "article") {
        const proof = await readArticle(context.address, { fetch: get, contact: env.CONTACT_EMAIL, timeoutMs: proofTimeoutMs });
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
    // The core and the complete answer carry the same context: where it was read from.
    const placed = (found) => ({ ...found, post,
      ...(image ? { source: { kind: "screenshot", host: pageUrl ? new URL(pageUrl).hostname : null } } : {}) });
    const found = placed(await lookUp({ text, model, registry, index, page, papers, research, image, pageUrl, timings,
      timeBudgetMs: Math.max(0, Math.min(45_000, Number.isFinite(sent?.timeBudgetMs) ? Math.max(0, sent.timeBudgetMs) : 45_000) - (Date.now() - started)),
      ...(paperAllowanceMs ? { paperAllowanceMs } : {}), ...(paperSpacingMs ? { paperSpacingMs } : {}),
      ...(onCore ? { onCore: (core) => { if (!unsupportedClaims(core, sent)) onCore(placed(core)); } } : {}) }));
    if (unsupportedClaims(found, sent)) return refusal(409, "multiple_claims");
    return { status: 200, body: found, keep: () => storeResult(env.LOOKUP_RESULTS, cacheUrl, found, publicVerified) };
  } catch (error) {
    // What failed may quote what was sent, so it is not written anywhere.
    if (error?.code === "budget_exhausted") return refusal(503, "budget_exhausted");
    return refusal(502, "failed");
  }
}

export default { fetch: (request, env) => handle(request, env) };
