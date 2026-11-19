// The sitemap: every public page, listed from the export. Embed pages are left out so
// they do not compete with their claim pages, and so is the page for an unknown
// address. A preview build publishes no sitemap: an empty response writes no file.
import type { APIRoute } from "astro";
import { data, listedTopics } from "../lib/export";
import { AUDIENCES } from "../lib/audiences";
import { buildTree, categoryPath, listedCategories } from "../lib/clinical";
import { guide } from "../lib/guide-entries";
import "../lib/public-build";
import { sourcesOf } from "../lib/sources";
import { canonicalAddress } from "../lib/structured";
import { EXTENSION_OFFERED } from "../../site.config.mjs";
import {
  categoryListings,
  clinicalTops,
  conditionListings,
  interventionListings,
  pairBundleFolder,
  pairPages,
  topicsIndex,
} from "../lib/pairs";

/** The pages of the site's own, which every build makes. */
function sitePages(): string[] {
  return [
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

/** In a build that reads a bundle (openspec pairs-site): pair addresses and the pages that
 * list pairs, and no claim's page. */
function pairSitePages(): string[] {
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
    ...sitePages(),
  ];
}

function publicPages(): string[] {
  const categories = listedCategories(buildTree(data.clinical, data.claims));
  const years = new Set(
    data.claims.flatMap((claim) =>
      claim.first_reported_date ? [claim.first_reported_date.slice(0, 4)] : [],
    ),
  );
  return [
    "/",
    "/topics",
    ...listedTopics.map((topic) => `/topic/${topic.slug}`),
    ...(categories.length > 0 ? ["/clinical"] : []),
    ...categories.map((node) => categoryPath(node.identifier)),
    ...data.claims.map((claim) => `/${claim.slug}`),
    ...sourcesOf(data.claims).map((source) => `/source/${source.slug}`),
    "/it-happened",
    "/how-it-works",
    "/guide",
    ...guide.map((entry) => `/guide/${entry.slug}`),
    "/about",
    ...AUDIENCES.map((audience) => `/for/${audience}`),
    ...(EXTENSION_OFFERED ? ["/extension"] : []),
    "/privacy",
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
  const entries = (pairBundleFolder() ? pairSitePages() : publicPages()).map(
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
