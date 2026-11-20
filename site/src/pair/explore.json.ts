// The explore page's file (src/lib/explore.ts): every published pair with the tree nodes it
// sits at or beneath, built once and filtered in the reader's browser.
import type { APIRoute } from "astro";
import { exploreFile } from "../lib/pairs";

export const GET: APIRoute = () =>
  new Response(JSON.stringify(exploreFile()), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
