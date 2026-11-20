// The site's open data, built once per build from the export and shared by the index,
// the per-claim files and the pages that describe them.
import { SITE } from "../../site.config.mjs";
import { builtClaims, data } from "./export";
import { DATA_LICENCE, dataCredit, openData, type OpenData } from "./open-data";

let built: OpenData | null = null;

export function siteOpenData(): OpenData {
  // A claim that leads to its pair has no record of its own in a pairs build; its record's
  // address leads to the pair's (worker/index.mjs).
  built ??= openData({ ...data, claims: builtClaims() }, DATA_LICENCE, dataCredit(SITE.name, SITE.url), SITE.url + "/how-it-works");
  return built;
}
