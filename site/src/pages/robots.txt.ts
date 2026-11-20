// Tells crawlers what they may read and where the sitemap is.
import type { APIRoute } from "astro";
import "../lib/public-build";
import { canonicalAddress } from "../lib/structured";

export const GET: APIRoute = () => {
  const lines = [
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
