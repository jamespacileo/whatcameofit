// One pair's open data record (openspec pairs-site, task 3.3): the lab's data file for it as
// written, with the licence, credit and sources. The index at /data/pairs.json lists every one.
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { pairBundle, pairDataRecord } from "../lib/pairs";

export function getStaticPaths() {
  return Object.keys(pairBundle()?.pages.PairDataFile ?? {}).map((address) => ({ params: { address } }));
}

export const GET: APIRoute = ({ params }) =>
  new Response(JSON.stringify(pairDataRecord(params.address!, SITE.name, SITE.url), null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
