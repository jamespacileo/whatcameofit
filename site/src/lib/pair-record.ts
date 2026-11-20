// One pair's open data record (openspec pairs-site, task 3.3): the lab's data file for it as
// written, with the licence, credit and sources, so the file stands alone. Pure, so the build
// and the Worker, which serves the record of a pair the build did not write (task 1.3), give
// the same record for the same file.
import { DATA_LICENCE, dataCredit } from "./open-data.ts";

export const PAIR_RECORD_FORMAT = { format: "pair-record", format_version: 1 } as const;

const PAIR_SOURCES = [
  { name: "ClinicalTrials.gov", url: "https://clinicaltrials.gov/" },
  { name: "Medical Subject Headings (MeSH)", url: "https://www.nlm.nih.gov/mesh/" },
];

/** What every open data file of the pairs carries: its licence, credit and sources. */
export function pairDataHeader(siteName: string, siteUrl: string) {
  return { licence: DATA_LICENCE, credit: dataCredit(siteName, siteUrl), sources: PAIR_SOURCES };
}

/** The record of one pair from its `PairDataFile`. */
export function pairRecordOf(file: { pair: unknown }, siteName: string, siteUrl: string) {
  return { ...PAIR_RECORD_FORMAT, ...pairDataHeader(siteName, siteUrl), pair: file.pair };
}

/** The record as the site serves it, the same bytes built ahead and made on request. */
export const pairRecordText = (file: { pair: unknown }, siteName: string, siteUrl: string) =>
  JSON.stringify(pairRecordOf(file, siteName, siteUrl), null, 2);
