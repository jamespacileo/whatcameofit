// One pair's open data record (openspec pairs-site, task 3.3): the lab's data file for it as
// written, with the licence, credit and sources. The index at /data/pairs.json lists every one.
// The build writes the records of the pairs it builds ahead; the Worker serves the rest from
// D1 with the same text (task 1.3).
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { pairBundle, builtAheadRecords } from "../lib/pairs";
import { pairRecordText } from "../lib/pair-record";

export function getStaticPaths() {
  return builtAheadRecords().map((address) => ({ params: { address } }));
}

export const GET: APIRoute = ({ params }) =>
  new Response(pairRecordText(pairBundle()!.pages.PairDataFile[params.address!], SITE.name, SITE.url), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
