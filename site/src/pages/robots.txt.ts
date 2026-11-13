// Tells crawlers what they may read and where the sitemap is. A preview build asks them
// to read nothing, as its pages ask not to be indexed and it publishes no sitemap.
import type { APIRoute } from "astro";
import { data } from "../lib/export";
import "../lib/public-build";
import { canonicalAddress } from "../lib/structured";

export const GET: APIRoute = () => {
  const lines = data.preview
    ? ["User-agent: *", "Disallow: /"]
    : [
        "User-agent: *",
        // The lookup service answers readers, not crawlers.
        "Disallow: /api/",
        "Allow: /",
        "",
        `Sitemap: ${canonicalAddress("/sitemap.xml")}`,
      ];
  return new Response(`${lines.join("\n")}\n`, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
