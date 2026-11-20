// How the sitemap's addresses are split into files (lib/sitemap.ts): pure, so the build and its
// tests split them the same way. At most 50,000 addresses and 50 MB uncompressed a file.
// https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps

/** Addresses a sitemap file holds at most. */
export const SITEMAP_LIMIT = 50_000;
/** Bytes a sitemap file holds at most, uncompressed. */
export const SITEMAP_BYTES = 50 * 1024 * 1024;

export interface SitemapFile {
  /** The file's name under /sitemaps/, with no extension. */
  name: string;
  pages: string[];
}

/** One kind's pages in files of at most `limit` addresses: "<kind>" alone when one file holds
 * them, else "<kind>-1", "<kind>-2" and on. */
export function inFiles(kind: string, pages: string[], limit = SITEMAP_LIMIT): SitemapFile[] {
  if (pages.length <= limit) return [{ name: kind, pages }];
  const files: SitemapFile[] = [];
  for (let start = 0; start < pages.length; start += limit) files.push({ name: `${kind}-${files.length + 1}`, pages: pages.slice(start, start + limit) });
  return files;
}
