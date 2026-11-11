// The sitemap: every public page, listed from the export. Embed pages are left out so
// they do not compete with their claim pages, and so is the page for an unknown
// address. A preview build publishes no sitemap: an empty response writes no file.
import type { APIRoute } from "astro";
import { data, listedTopics } from "../lib/export";
import "../lib/public-build";
import { canonicalAddress } from "../lib/structured";

function publicPages(): string[] {
  const years = new Set(
    data.claims.flatMap((claim) =>
      claim.first_reported_date ? [claim.first_reported_date.slice(0, 4)] : [],
    ),
  );
  return [
    "/",
    "/topics",
    ...listedTopics.map((topic) => `/topic/${topic.slug}`),
    ...data.claims.map((claim) => `/${claim.slug}`),
    "/it-happened",
    "/how-it-works",
    "/anniversaries",
    "/data",
    ...[...years].sort().map((year) => `/year/${year}`),
  ];
}

const escapeXml = (text: string) =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export const GET: APIRoute = () => {
  if (data.preview) {
    return new Response(null, { status: 404, statusText: "A preview build has no sitemap" });
  }
  const entries = publicPages().map(
    (page) => `  <url><loc>${escapeXml(canonicalAddress(page))}</loc></url>`,
  );
  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...entries,
    "</urlset>",
    "",
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
};
