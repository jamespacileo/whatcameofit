// The open data index: the licence, credit and sources, and a short entry per published
// claim with the address of its full record (/data/claims/<slug>.json).
import type { APIRoute } from "astro";
import { openDataIndex } from "../../lib/open-data";
import { siteOpenData } from "../../lib/site-open-data";

export const GET: APIRoute = () =>
  new Response(JSON.stringify(openDataIndex(siteOpenData()), null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
