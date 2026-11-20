// The sitemap: every public page, listed from the bundle. Embed pages are left out so
// they do not compete with their pair pages, and so is the page for an unknown address.
import type { APIRoute } from "astro";
import { AUDIENCES } from "../lib/audiences";
import { categoryPath } from "../lib/clinical";
import { guide } from "../lib/guide-entries";
import "../lib/public-build";
import { canonicalAddress } from "../lib/structured";
import { EXTENSION_OFFERED } from "../../site.config.mjs";
import {
  categoryListings,
  clinicalTops,
  conditionListings,
  interventionListings,
  pairPages,
  topicsIndex,
} from "../lib/pairs";

/** Pair addresses, the pages that list pairs, and the site's own pages. */
function publicPages(): string[] {
  return [
    "/",
    "/topics",
    ...topicsIndex().map((topic) => `/topic/${topic.slug}`),
    ...(clinicalTops().length > 0 ? ["/clinical"] : []),
    ...categoryListings()
      .filter((listing) => listing.pairs.length > 0)
      .map((listing) => categoryPath(listing.descriptorId)),
    ...interventionListings().map((listing) => `/intervention/${listing.slug}`),
    ...conditionListings().map((listing) => `/condition/${listing.slug}`),
    ...Object.keys(pairPages()).sort().map((address) => `/${address}`),
    "/how-it-works",
    "/guide",
    ...guide.map((entry) => `/guide/${entry.slug}`),
    "/about",
    ...AUDIENCES.map((audience) => `/for/${audience}`),
    ...(EXTENSION_OFFERED ? ["/extension"] : []),
    "/privacy",
    "/data",
  ];
}

const escapeXml = (text: string) =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export const GET: APIRoute = () => {
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
