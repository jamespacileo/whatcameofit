// The site's open data, built once per build from the export and shared by the index,
// the per-claim files and the pages that describe them.
import { SITE } from "../../site.config.mjs";
import { data } from "./export";
import { DATA_LICENCE, dataCredit, openData, type OpenData } from "./open-data";

let built: OpenData | null = null;

export function siteOpenData(): OpenData {
  built ??= openData(data, DATA_LICENCE, dataCredit(SITE.name, SITE.url), SITE.url + "/how-it-works");
  return built;
}
