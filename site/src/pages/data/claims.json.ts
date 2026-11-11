// The open data file: every published claim, with its licence and sources inside.
import type { APIRoute } from "astro";
import { SITE } from "../../../site.config.mjs";
import { data } from "../../lib/export";
import { DATA_LICENCE, dataCredit, openData } from "../../lib/open-data";

export const GET: APIRoute = () => {
  const body = openData(
    data,
    DATA_LICENCE,
    dataCredit(SITE.name, SITE.url),
    SITE.url + "/how-it-works",
  );
  return new Response(JSON.stringify(body, null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
