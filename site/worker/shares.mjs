// A pair's embed, oEmbed description and card, made on request (openspec pairs-site task 4.6):
// the build makes none of them, so its file count does not grow with the pairs.
// - /embed/<pair>: the pair's file from D1 at the build's version, checked with its compiled
//   validator, written by lib/embed-render.ts into the frame the build left at /embed-shell.
// - /oembed/<pair>.json: the same file, described for sites that turn pasted links into embeds.
// - /og/<pair>.png, /og/square/<pair>.png, /og/tall/<pair>.png: the site's own card for every
//   pair the version holds. No pair has a picture of its own any more; these addresses answer
//   because pages, feeds and old claim redirects named them (worker/index.mjs).
// Each is cached a day under the bundle version and the frame's digest, as pair pages are.
import { embedTitle, oembedOf, renderEmbedArticle, renderEmbedRegistries } from "../src/lib/embed-render.ts";
import { escape } from "../src/lib/pair-render.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { SITE } from "../site.config.mjs";
import { ABSENT, UNREADABLE, builtVersion, bundleFile, madeHeaders } from "./pairs.mjs";

export const EMBED_SHELL_PATH = "/embed-shell";
const DAY_SECONDS = 86400;
const PAIR = "[a-z0-9]+(?:-[a-z0-9]+)*--[a-z0-9]+(?:-[a-z0-9]+)*";
const EMBED = new RegExp(`^/embed/(${PAIR})$`);
const OEMBED = new RegExp(`^/oembed/(${PAIR})\\.json$`);
const CARD = new RegExp(`^/og/(?:(?:square|tall)/)?(${PAIR})\\.png$`);
// The card a built page names (Base.astro), read from the frame so the address carries the
// build's own revision of the picture.
const OG_IMAGE = /<meta property="og:image" content="([^"]+)"/;

/** Which share a path is, or null: { kind: "embed" | "oembed" | "card", address }. */
export function shareOf(pathname) {
  const embed = EMBED.exec(pathname)?.[1];
  if (embed) return { kind: "embed", address: embed };
  const oembed = OEMBED.exec(pathname)?.[1];
  if (oembed) return { kind: "oembed", address: oembed };
  const card = CARD.exec(pathname)?.[1];
  if (card) return { kind: "card", address: card };
  return null;
}

/**
 * The share a path names, or null when the deployment has no frame or store, the path is no
 * share's, or the version holds no such pair.
 * @param {(file: unknown) => boolean} validate the compiled validator of `PairPage`
 */
export async function shareAnswer(request, env, validate, cache) {
  const url = new URL(request.url);
  const share = shareOf(url.pathname);
  if (!share || !env.PAIRS || typeof validate !== "function") return null;
  const built = await builtVersion(env, url);
  if (!built) return null;
  const card = OG_IMAGE.exec(built.shell)?.[1];
  if (!card) return null;

  const key = new Request(new URL(`/__share/${built.version}/${built.build}${url.pathname}`, url));
  const kept = cache ? await cache.match(key) : undefined;
  if (kept) return kept;

  let answer;
  if (share.kind === "card") {
    // One read by the page table's key: whether the version holds this pair.
    const { results } = await env.PAIRS.prepare("SELECT 1 FROM pair_page WHERE version = ?1 AND model = 'PairPage' AND key = ?2 AND part = 0")
      .bind(built.version, share.address)
      .all();
    if (!results.length) return null;
    const where = new URL(card);
    const image = await env.ASSETS.fetch(new Request(new URL(`${where.pathname}${where.search}`, url)));
    if (!image.ok) return null;
    answer = new Response(image.body, { headers: madeHeaders(built, "image/png", `public, max-age=${DAY_SECONDS}`) });
  } else {
    const file = await bundleFile(env, built.version, "PairPage", share.address);
    if (file === ABSENT) return null;
    if (!validate(file)) {
      const body = share.kind === "oembed" ? JSON.stringify({ error: UNREADABLE }) : `<!doctype html><title>${escape(UNREADABLE)}</title><p>${escape(UNREADABLE)}</p>`;
      return new Response(body, { status: 500, headers: madeHeaders(built, share.kind === "oembed" ? "application/json; charset=utf-8" : "text/html; charset=utf-8", "no-store") });
    }
    const view = pairView(file);
    if (share.kind === "oembed") {
      answer = new Response(JSON.stringify(oembedOf(view, SITE.name, SITE.url, card)), {
        headers: madeHeaders(built, "application/json+oembed; charset=utf-8", `public, max-age=${DAY_SECONDS}`),
      });
    } else {
      const frame = await env.ASSETS.fetch(new Request(new URL(EMBED_SHELL_PATH, url)));
      if (!frame.ok) return null;
      // Each part goes in by a function, so a "$" in a name is shown as written.
      const page = (await frame.text())
        .replaceAll("__EMBED_TITLE__", () => escape(embedTitle(view)))
        .replace("<!--embed-article-->", () => renderEmbedArticle(view, SITE.name, SITE.url))
        .replace("<!--embed-registries-->", () => renderEmbedRegistries(view));
      answer = new Response(page, { headers: madeHeaders(built, "text/html; charset=utf-8", `public, max-age=${DAY_SECONDS}`) });
    }
  }
  if (cache) await cache.put(key, answer.clone());
  return answer;
}
