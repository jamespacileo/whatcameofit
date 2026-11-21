// The review site's Worker (openspec change `review-dashboard`). It runs before every file:
// pages, scripts and the API all sit behind one check of the reader's Access token
// (access.mjs), as the proposal `private-content-review` asks for one protected surface.
import { accessSettings, operatorOf } from "./access.mjs";
import { published } from "./published.mjs";
import { overview } from "./reads.mjs";
import { AREAS, MODELS } from "./catalogue.mjs";
import { inventory, pageRecord, rowsOf } from "./inventory.mjs";

/** Sent with every answer: nothing here is cached by a shared cache, indexed or framed. */
const PRIVATE = {
  "Cache-Control": "private, no-store",
  "X-Robots-Tag": "noindex, nofollow",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

function answer(body, status = 200, type = "application/json; charset=utf-8") {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { ...PRIVATE, "Content-Type": type },
  });
}

function marked(response) {
  const copy = new Response(response.body, response);
  for (const [name, value] of Object.entries(PRIVATE)) copy.headers.set(name, value);
  return copy;
}

async function api(url, request, env, email) {
  if (request.method !== "GET") return answer({ error: "read-only" }, 405);
  if (url.pathname === "/api/me") return answer({ email });
  if (url.pathname === "/api/staging/overview") {
    if (!env.STAGING_PAIRS) return answer({ error: "staging store not connected" }, 503);
    const [store, served] = await Promise.all([overview(env.STAGING_PAIRS, "staging"), published(env.STAGING_URL)]);
    return answer({ ...store, published: served });
  }
  if (url.pathname === "/api/models") return answer(await models(env));
  const one = /^\/api\/models\/([^/]+)\/(rows|record)$/.exec(url.pathname);
  if (one) {
    const id = decodeURIComponent(one[1]);
    const store = storeOf(env, url.searchParams.get("env") ?? "staging");
    if (!store) return answer({ error: "this environment's store is not readable yet" }, 409);
    if (one[2] === "rows") {
      const offset = Number(url.searchParams.get("offset") ?? 0);
      if (!Number.isInteger(offset) || offset < 0 || offset > 1_000_000) return answer({ error: "bad offset" }, 400);
      const page = await rowsOf(store, id, offset);
      return page ? answer(page) : answer({ error: "no such model" }, 404);
    }
    const key = url.searchParams.get("key");
    if (!key || key.length > 512) return answer({ error: "bad key" }, 400);
    const record = await pageRecord(store, id, key);
    return record ? answer(record) : answer({ error: "no such record" }, 404);
  }
  return answer({ error: "not found" }, 404);
}

/** Production's store is not read until phase 4 (a D1 Read token); it is listed, never hidden. */
const ENVIRONMENTS = [
  { name: "staging", binding: "STAGING_PAIRS", label: "Staging", store: "thenwhat-store-preview (D1)" },
  { name: "production", binding: null, label: "Production", store: "thenwhat-store (D1)", reason: "Not readable yet: production is read with a D1 Read token, which comes in phase 4." },
];

function storeOf(env, name) {
  const environment = ENVIRONMENTS.find((e) => e.name === name);
  return environment?.binding ? env[environment.binding] ?? null : null;
}

async function models(env) {
  const environments = [];
  const states = {};
  for (const environment of ENVIRONMENTS) {
    const store = environment.binding ? env[environment.binding] : null;
    if (!store) {
      environments.push({ name: environment.name, label: environment.label, store: environment.store, readable: false, reason: environment.reason ?? "This environment's store is not connected." });
      for (const model of MODELS) (states[model.id] ??= {})[environment.name] = { status: "unavailable" };
      continue;
    }
    const seen = await inventory(store);
    environments.push({ name: environment.name, label: environment.label, store: environment.store, readable: true, bundle: seen.bundle, unlisted: seen.unlisted });
    for (const model of MODELS) (states[model.id] ??= {})[environment.name] = seen.states[model.id];
  }
  return { areas: AREAS, environments, models: MODELS.map((model) => ({ ...model, environments: states[model.id] })) };
}

export default {
  /** @param {Request} request */
  async fetch(request, env) {
    const settings = accessSettings(env);
    if (!settings) return answer("The review site is not set up.", 503, "text/plain; charset=utf-8");
    const email = await operatorOf(request, settings);
    if (!email) return answer("Forbidden.", 403, "text/plain; charset=utf-8");
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) return api(url, request, env, email);
    return marked(await env.ASSETS.fetch(request));
  },
};
