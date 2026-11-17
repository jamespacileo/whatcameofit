// One claim's full open data record, with the licence, credit and sources repeated so the
// file stands alone. The index at /data/claims.json lists every one.
import type { APIRoute } from "astro";
import { openDataRecord, type OpenClaim } from "../../../lib/open-data";
import { siteOpenData } from "../../../lib/site-open-data";

export function getStaticPaths() {
  return siteOpenData().claims.map((claim) => ({ params: { slug: claim.slug }, props: { claim } }));
}

export const GET: APIRoute = ({ props }) => {
  const { claim } = props as { claim: OpenClaim };
  return new Response(JSON.stringify(openDataRecord(siteOpenData(), claim), null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
