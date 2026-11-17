// The registry numbers of the listed trials, one a line: what the Worker checks before
// it opens a page for a trial no claim cites, without reading the whole listing.
import type { APIRoute } from "astro";
import { listing } from "../lib/trials-listing";

export const GET: APIRoute = () =>
  new Response(listing.trials.map((row) => `${row[0]}\n`).join(""), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
