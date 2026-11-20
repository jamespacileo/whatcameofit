// The sitemap, as an index and its files (openspec pairs-site task 4.6f): the site's own pages,
// the pages that list pairs, and the pairs, each kind in files of their own so that no file
// passes the limits search engines read: 50,000 addresses and 50 MB uncompressed a file. The
// files are at the site's root (/sitemap-<name>.xml): a sitemap found through robots.txt may
// list only pages within its own folder.
// https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps
// https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
//
// No file gives a <lastmod>: the date a pair's content last changed is not in the bundle (one
// bundle cannot say when its files last changed), and the date of a load is not that date; a
// sitemap that gives one it does not know misleads. Neither <priority> nor <changefreq>: Google
// ignores both (build-sitemap, above).
import { AUDIENCES } from "./audiences";
import { categoryPath } from "./clinical";
import { guide } from "./guide-entries";
import { canonicalAddress } from "./structured";
import { EXTENSION_OFFERED } from "../../site.config.mjs";
import { categoryListings, clinicalTops, conditionListings, interventionListings, pairPages, topicsIndex } from "./pairs";
import { SITEMAP_BYTES, inFiles, type SitemapFile } from "./sitemap-files";

/** The site's own pages. */
export function sitePages(): string[] {
  return [
    "/",
    "/topics",
    "/explore",
    ...(clinicalTops().length > 0 ? ["/clinical"] : []),
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

/** The pages that list pairs: each topic, clinical category, intervention and condition that
 * lists one. */
export function listingPages(): string[] {
  return [
    ...topicsIndex().map((topic) => `/topic/${topic.slug}`),
    ...categoryListings()
      .filter((listing) => listing.pairs.length > 0)
      .map((listing) => categoryPath(listing.descriptorId)),
    ...interventionListings().map((listing) => `/intervention/${listing.slug}`),
    ...conditionListings().map((listing) => `/condition/${listing.slug}`),
  ];
}

/** Every pair's page. */
export function pairAddresses(): string[] {
  return Object.keys(pairPages()).sort().map((address) => `/${address}`);
}

let files: SitemapFile[] | undefined;

/** Every sitemap file the index names, worked out once a build: the index and the files read
 * the same list. */
export function sitemapFiles(): SitemapFile[] {
  return (files ??= [...inFiles("pages", sitePages()), ...inFiles("listings", listingPages()), ...inFiles("pairs", pairAddresses())]);
}

const escapeXml = (text: string) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** A sitemap file's text. Throws when it would pass the size search engines read. */
export function urlset(pages: string[]): string {
  const text = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...pages.map((page) => `  <url><loc>${escapeXml(canonicalAddress(page))}</loc></url>`),
    "</urlset>",
    "",
  ].join("\n");
  if (new TextEncoder().encode(text).length > SITEMAP_BYTES) throw new Error(`A sitemap file of ${pages.length} addresses passes ${SITEMAP_BYTES} bytes.`);
  return text;
}

/** The sitemap index's text: each file by its address. */
export function sitemapIndex(named: SitemapFile[]): string {
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...named.map((file) => `  <sitemap><loc>${escapeXml(canonicalAddress(`/sitemap-${file.name}.xml`))}</loc></sitemap>`),
    "</sitemapindex>",
    "",
  ].join("\n");
}
