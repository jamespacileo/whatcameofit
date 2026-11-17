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
  // Written without indentation: indented, the file passed the 25 MiB a host allows one
  // file at 966 claims. A reader's tool formats it; the content is the same.
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
