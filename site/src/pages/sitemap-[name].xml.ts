// One sitemap file, at /sitemap-<name>.xml: the site's own pages, the pages that list pairs, or
// the pairs, at most 50,000 addresses a file (lib/sitemap.ts). Embed pages are left out so they do not compete
// with their pair pages, and so is the page for an unknown address.
import type { APIRoute } from "astro";
import "../lib/public-build";
import { sitemapFiles, urlset } from "../lib/sitemap";

export function getStaticPaths() {
  return sitemapFiles().map((file) => ({ params: { name: file.name }, props: { pages: file.pages } }));
}

export const GET: APIRoute = ({ props }) =>
  new Response(urlset(props.pages), { headers: { "Content-Type": "application/xml; charset=utf-8" } });
