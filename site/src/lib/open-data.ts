// The open data file: the validated export, reduced to what the claim pages already show,
// with its licence, credit line, sources and method address inside. Pure: no files, no
// clock. Outlet icon images, article text and raw registry payloads are never in it.

/** The licence's name as LICENSE-DATA gives it. */
export const DATA_LICENCE = "Creative Commons Attribution 4.0 International (CC BY 4.0)";
export const DATA_LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/";

/** LICENSE-DATA asks for credit, a link to the licence and a note of any change. */
export function dataCredit(siteName: string, siteUrl: string): string {
  return `${siteName} (${siteUrl}), licensed under ${DATA_LICENCE}, ${DATA_LICENCE_URL}. Indicate if changes were made.`;
}
