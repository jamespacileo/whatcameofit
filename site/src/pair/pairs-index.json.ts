// The index of the pairs' open data records (openspec pairs-site, task 3.3).
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { pairDataIndex } from "../lib/pairs";

export const GET: APIRoute = () =>
  new Response(JSON.stringify(pairDataIndex(SITE.name, SITE.url), null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
