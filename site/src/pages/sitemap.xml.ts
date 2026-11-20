// The sitemap index: each sitemap file of the site by its address (lib/sitemap.ts says why the
// files are split, and why none gives a <lastmod>). Robots.txt names this one.
import type { APIRoute } from "astro";
import "../lib/public-build";
import { sitemapFiles, sitemapIndex } from "../lib/sitemap";

export const GET: APIRoute = () =>
  new Response(sitemapIndex(sitemapFiles()), { headers: { "Content-Type": "application/xml; charset=utf-8" } });
