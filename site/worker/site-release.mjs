import { RELEASE_ROWS, RELEASE_SLUG } from "../src/lib/release-paths.mjs";

// Large releases keep their path-to-file map with the Worker assets. A rollback
// selects the old map as well as the old pages and lookup files.
const MANIFEST = "/_site-release";
const DIGEST = /^[a-f0-9]{64}$/;
const PAGE = new RegExp(`^/((?:(?:embed|topic)/)?${RELEASE_SLUG})(?:/|/index\\.html)?$`);
const GENERATED = new RegExp(
  `^/(?:(?:data/claims|oembed)/${RELEASE_SLUG}\\.json|changes/${RELEASE_SLUG}\\.xml|og/(?:square/|tall/)?${RELEASE_SLUG}\\.png)$`,
);
const PAGEFIND = /^\/pagefind\/(?:[\w.-]+\/)*[\w.-]+$/;
const CONTENT_TYPES = {
  html: "text/html; charset=utf-8",
  json: "application/json; charset=utf-8",
  xml: "application/xml; charset=utf-8",
  png: "image/png",
  js: "text/javascript; charset=utf-8",
  css: "text/css; charset=utf-8",
  wasm: "application/wasm",
  txt: "text/plain; charset=utf-8",
};

function unavailable() {
  return new Response("Site file temporarily unavailable", {
    status: 503,
    headers: { "Cache-Control": "no-store", "Retry-After": "60" },
  });
}

export async function releaseFile(request, here, env) {
  let pathname;
  try { pathname = decodeURI(here.pathname); }
  catch { return null; }
  if (pathname === MANIFEST || pathname.startsWith(`${MANIFEST}/`)) {
    return new Response("Not found", { status: 404, headers: { "Cache-Control": "no-store" } });
  }
  if (!env.SITE_FILES || !["GET", "HEAD"].includes(request.method)) return null;

  const page = PAGE.exec(pathname);
  const rowFile = RELEASE_ROWS.test(pathname.slice(1));
  const generatedFile = GENERATED.test(pathname) || PAGEFIND.test(pathname) || rowFile;
  if (!page && !generatedFile) return null;
  const relative = page ? `${page[1]}/index.html` : pathname.slice(1);
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(relative));
  const shard = new Uint8Array(hash)[0].toString(16).padStart(2, "0");

  try {
    const source = await env.ASSETS.fetch(new Request(new URL(`${MANIFEST}/${shard}.json`, here)));
    if (source.status === 404) return null;
    if (!source.ok) return unavailable();
    const manifest = await source.json();
    if (!manifest?.files || typeof manifest.noindex !== "boolean") return unavailable();
    if (!Object.hasOwn(manifest.files, relative)) return null;
    const [digest, size] = manifest.files[relative];
    if (!DIGEST.test(digest) || !Number.isSafeInteger(size) || size < 0) return unavailable();

    if (page && here.pathname !== `/${page[1]}`) {
      const canonical = new URL(here);
      canonical.pathname = `/${page[1]}`;
      return Response.redirect(canonical, 308);
    }

    const tag = `"${digest}"`;
    const headers = new Headers({
      "Cache-Control": "public, max-age=0, must-revalidate",
      "Content-Type": CONTENT_TYPES[relative.split(".").at(-1)] ?? "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "strict-origin-when-cross-origin",
      "Strict-Transport-Security": "max-age=31536000",
      ETag: tag,
    });
    if (manifest.noindex || rowFile) headers.set("X-Robots-Tag", "noindex");
    const tags = request.headers.get("If-None-Match")?.split(",") ?? [];
    if (tags.some((value) => value.trim() === "*" || value.trim().replace(/^W\//, "") === tag)) {
      return new Response(null, { status: 304, headers });
    }

    const key = `site-files/v1/${digest}`;
    const head = request.method === "HEAD";
    const file = head ? await env.SITE_FILES.head(key) : await env.SITE_FILES.get(key);
    if (!file || file.size !== size) {
      await file?.body?.cancel();
      return unavailable();
    }
    headers.set("Content-Length", String(size));
    return new Response(head ? null : file.body, { headers });
  } catch {
    return unavailable();
  }
}
