// The lookup file the site's lookup box and search, and the lookup Worker, read: version 2,
// keyed by pair address (site/src/pages/lookup/2.json.ts). Version 1, /lookup.json, is kept
// only for the released browser extension.

export const LOOKUP_FILE = "/lookup/2.json";
export const LOOKUP_FORMAT = { format: "lookup", format_version: 2 };

/**
 * The lookup file as the box and the Worker hold it: each pair's entry with its page added,
 * its status's meaning and its unchecked note filled in from the file's own tables,
 * and under `headline` and `indication` too, the names their matching and drawing code was
 * written with. Those two go when that code is renamed; the file itself never carries them.
 * A claim kept at its own address (scripts/kept-claims.mjs) is in the file's `kept`, by its
 * slug, as production's lookup gave it: it joins the pairs with its own page, its own words and
 * `kept` set, so it is found by its words and its articles' addresses as before.
 * A file of another format, or none, reads as no pairs.
 * @param {any} file
 */
export function readLookupFile(file) {
  const ours = file?.format === LOOKUP_FORMAT.format && file?.format_version === LOOKUP_FORMAT.format_version;
  const pairs = {};
  for (const [address, entry] of Object.entries(ours ? file.pairs ?? {} : {})) {
    pairs[address] = {
      ...entry,
      meaning: file.meanings?.[entry.status] ?? "",
      unchecked: entry.unchecked ? file.unchecked_note ?? "" : null,
      page: `/${address}`,
      headline: entry.title,
      indication: entry.condition,
    };
  }
  for (const [slug, entry] of Object.entries(ours ? file.kept ?? {} : {})) {
    if (Object.hasOwn(pairs, slug)) continue;
    pairs[slug] = { ...entry, page: `/${slug}`, title: entry.headline, condition: entry.indication, kept: true };
  }
  return { ...(ours ? file : {}), articles: ours ? file.articles ?? {} : {}, topics: ours ? file.topics ?? {} : {}, pairs };
}

/** A registry record's address, from its identifier: the search detail gives only the
 * identifier, as every trial it lists is a ClinicalTrials.gov record. */
export const TRIAL_REGISTRY = "ClinicalTrials.gov";
export const trialUrl = (id) => `https://clinicaltrials.gov/study/${id}`;

/**
 * The search detail as the box holds it: each trial with its registry and address added. A kept
 * claim's reports and trials (`kept`, by slug) are as production gave them, registry and all.
 * @param {any} file
 */
export function readSearchDetail(file) {
  const pairs = {};
  for (const [address, held] of Object.entries(file?.pairs ?? {})) {
    pairs[address] = { ...held, trials: (held.trials ?? []).map((trial) => ({ ...trial, registry: TRIAL_REGISTRY, url: trialUrl(trial.id) })) };
  }
  for (const [slug, held] of Object.entries(file?.kept ?? {})) if (!Object.hasOwn(pairs, slug)) pairs[slug] = held;
  return { ...file, pairs };
}
