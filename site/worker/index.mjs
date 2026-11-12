// The site's Worker. Every address but one is a file of the built site. /api/lookup
// answers a reader's question about an article the site does not track: which trial
// records is this about? Behaviour: openspec live-lookup.
//
// Nothing a reader sends is stored or logged here: not the address, not the text, not
// the answer. The reader's network address is used once, to count requests per minute.
import { readAddress } from "../src/lib/lookup-match.mjs";
import { MAX_TEXT_CHARACTERS, readArticle } from "./article.mjs";
import { lookUp } from "./lookup.mjs";
import { makeModel } from "./model.mjs";
import { makePapers } from "./papers.mjs";
import { makeRegistry } from "./registry.mjs";

const PATH = "/api/lookup";
const UNREADABLE = { robots: "unreadable_robots", unreadable: "unreadable", address: "address" };

function answer(body, status = 200) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}
const refuse = (status, error) => answer({ error }, status);

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
  };
}

/** @param {{ model: object, registry: object, papers?: object } | undefined} tools stand-ins, for tests */
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

  let article = null;
  let page;
  if (!text) {
    article = readAddress(address);
    if (article.kind === "none") return refuse(400, "address");
    // A shortened link or a post does not say which article it is; the reader pastes the text.
    if (article.kind !== "article") return refuse(422, article.kind);
  }

  const reader = request.headers.get("CF-Connecting-IP") ?? "unknown";
  const limits = await Promise.all([
    env.LOOKUP_PER_READER.limit({ key: reader }),
    env.LOOKUP_IN_ALL.limit({ key: "all" }),
  ]);
  if (limits.some((limit) => !limit.success)) return refuse(429, "busy");

  try {
    if (article) {
      const read = await readArticle(article.address, { fetch, contact: env.CONTACT_EMAIL });
      if (read.refused) return refuse(422, UNREADABLE[read.refused]);
      text = read.text;
      page = read.page;
    }
    const index = await env.ASSETS.fetch(new Request(new URL("/lookup.json", here)))
      .then((response) => (response.ok ? response.json() : { claims: {} }))
      .catch(() => ({ claims: {} }));
    const { model, registry, papers } = tools ?? realTools(env);
    return answer(await lookUp({ text, model, registry, index, page, papers }));
  } catch {
    // What failed may quote what was sent, so it is not written anywhere.
    return refuse(502, "failed");
  }
}

export default { fetch: (request, env) => handle(request, env) };
