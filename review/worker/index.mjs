// The review site's Worker (openspec change `review-dashboard`). It runs before every file:
// pages, scripts and the API all sit behind one check of the reader's Access token
// (access.mjs), as the proposal `private-content-review` asks for one protected surface.
import { accessSettings, operatorOf } from "./access.mjs";
import { overview } from "./reads.mjs";

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
    return answer(await overview(env.STAGING_PAIRS, "staging"));
  }
  return answer({ error: "not found" }, 404);
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
