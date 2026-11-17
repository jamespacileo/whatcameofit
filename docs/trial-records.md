# Trial record reader

Claim pages retain their ClinicalTrials.gov links and offer “View trial details here” beside them. The local `/trials/NCTxxxxxxxx` page contains a formatted selection of public registry fields, an official source link, retrieval and update dates, and links back to citing claims. It makes no medical interpretation and does not change a claim's status.

The site builds offline. `trial-index.json` is derived from the published export and limits the reader to cited trials. `trial-reader.astro` builds the shared layout template; the Worker fills it with escaped registry text. The reader is complete HTML, requires no JavaScript or registry cookies, and sends no browser request to ClinicalTrials.gov. The template itself is not a public reader page and is excluded from indexing.

The Worker uses the existing public API v2 client with `CONTACT_EMAIL`. It does not need model credentials and never forwards visitor cookies or authorisation. Each fetch has an eight-second deadline. `TRIAL_RECORD_READS` limits uncached upstream requests to 60 per minute per Cloudflare location; cached responses do not spend lookup/model quotas.

The registry is asked only for the fields the two pages show (`PAGE_FIELDS` in `site/worker/trials.mjs`): its officials, contacts and sites are never received. Whatever comes back then has its people removed by one rule (`site/worker/people.mjs`, the same as the pipeline's) before it is saved or shown. A validated record is saved in the existing `LOOKUP_RESULTS` KV namespace under `trial-record:v1:<id>` with its retrieval time, as copy version 2. Until 2026-11-17 a copy was the registry's whole record, contacts included (version 1); such a copy, and any copy that names a person, is refused and replaced on the next view. A copy is reused for 24 hours and then expires. No older copy is ever shown: when the registry cannot be read, the page says so. Expired, future-dated or mismatched copies are ignored. Missing registry records return 404; temporary failures without a usable copy return 503 with recovery links. Errors use `no-store`. KV outages do not prevent a successful live response.

## Local preview

From `site/`, after installing the existing dependencies:

```sh
EXPORT_FILE=data/published-export.json ASTRO_TELEMETRY_DISABLED=1 pnpm run build
pnpm exec wrangler dev --local --ip 127.0.0.1 --port 8789 --inspector-port 9239 --var CONTACT_EMAIL:corrections@whatcameofit.com
```

This uses local bindings and fetches public registry data. It does not deploy or use model credentials. Plain Astro preview cannot execute the Worker route. Keep the preview on loopback and do not expose a home-network server publicly.

Open `/primary-aldosteronism-baxdrostat` and follow the local links for NCT04605549, NCT07007793 and NCT07800858. For verification, remove only ClinicalTrials.gov cookies in the test browser, then confirm that local pages still work and that their resource requests stay on the local site. Restore the test browser's previous cookies afterwards. Automated tests in `site/tests/trials.test.mjs` use synthetic records and make no network calls.

## Verified upstream failure

On 13 November 2026, removing only `ncbi_sid` in Safari changed ClinicalTrials.gov's internal study request from 200 to 403; restoring it changed the response back to 200. Chrome also failed when cookies were omitted. Public API v2 returned the correct records without cookies. The reason the original session lacked the cookie was not established. This reader avoids that dependency; it does not claim to repair ClinicalTrials.gov's browser interface.

## A listed trial no claim cites

Decided by the operator on 2026-11-17 (change `trial-first-route`): before the store on Cloudflare exists, a trial with no claim may open a plain page, for the listed set only. The listing is one static file the pipeline writes, `thenwhat trials-listing` (set `active-since-2025`: phase 2 or 3, under way or not yet started, record changed by the registry since 1 January 2025). `make publish-data` stages it as `site/data/published-trials-listing.json` beside the export; the site finds it by that name, validates it against `site/trials-listing.schema.json`, and builds two files from it: `/trials-listing.json`, which the search box fetches only when a reader searches, and `/trial-listed.txt`, the registry numbers alone, which is all the Worker reads before it opens a page.

**In parts since 2026-11-17.** The operator made the listed set one rolling set (under way or not yet started now, or ended in the current calendar year; the rule is a named set in `pipeline/src/thenwhat/backfill/trial_sets.py`). By that rule the working database held 102,877 trials that day and the listing is 29,090,078 bytes, more than Cloudflare takes as one file (25 MiB). The pipeline still writes one file. The site's build cuts it, in registry-number order, into parts of about a mebibyte (`site/src/lib/trial-listing-parts.mjs`): 28 parts at that size, the largest 1,049,193 bytes (about 320 KB with gzip, 250 KB with Brotli). `/trials-listing.json` is now a manifest of under 3 KB that names each part and the first and last registry number it holds; the parts are `/trials-listing/00.json` and so on. A search for a registry number fetches the manifest and one part. A search by words needs every part (about 5.8 MB with Brotli), so with more than two parts it is made only when the reader presses "Search 102,877 registered trials for these words"; after that, later searches read nothing more. `/trial-listed.txt` is 1.2 MB and is read by the Worker only. Staging refuses a listing over 64 MiB. The build takes about a second longer.

**Which set is listed** is `TRIALS_SET` in the `Makefile`, since 2026-11-17 `active-or-ended-this-year` (`make deploy TRIALS_SET=<name>` lists another). `thenwhat trials-listing` reads the rule by name from `backfill/trial_sets.py` (`rule_of`) and gives it the calendar year from the clock; the rule is defined nowhere else. The site words a set from its name (`SET_WORDS` in `site/src/lib/trial-page.mjs`); a name it has no words for is described only as studies registered on ClinicalTrials.gov.

**The state is the registry's word.** The plain page states, under the state, the day the registry last changed the record, and a search row shows it beside the state: 7,976 of the trials listed as under way or not yet started on 2026-11-17 had not been changed since before 2025.

**Many pages, one registry.** With about 100,000 uncited trials listed, what keeps requests for their pages from reaching the registry or crowding out readers:

- No page of an uncited trial is in the sitemap or linked from any built page: a search result is the only link to one, made in the reader's browser. Every trial page is `noindex`. `robots.txt` does not disallow `/trials/`: a crawler that is kept from a page never sees its `noindex`.
- A record read within the day is reused from KV, so a page asked for again costs the registry nothing.
- Registry reads for uncited trials' pages have their own allowance, `LISTED_TRIAL_READS`, 30 a minute for each Cloudflare location, inside the 60 a minute of `TRIAL_RECORD_READS` for all trial pages. Past either, the page answers 503 with `Retry-After: 60` and the registry is not asked. So a crawler reading every listed page takes at least 57 hours at one location, the registry sees at most 30 requests a minute from it there, and pages of cited trials keep at least 30 reads a minute.
- Not bounded here: each first read of a page writes one KV entry that lasts a day, so 100,000 pages read in a day is 100,000 KV writes. The limits count for each Cloudflare location, so requests spread over many locations add up.

`/trials/NCTxxxxxxxx` then answers in one of three ways:

- **A published claim cites the trial:** the page above, which now leads with the claims citing it.
- **No claim cites it and the listing holds it:** the plain page. The registry's own record is read on request by the same reader, with the same one-day reuse and the same limit of 60 reads a minute for each location. It states the state, phase, conditions, intervention names, enrolment, lead sponsor (never a person: not one the registry classes "INDIV", and not a sponsor-investigator, on this page or a cited trial's), dates, whether results are posted and when, the reason for stopping in the registry's words, and "No news report is linked to this record yet." It shows no summary, outcome, location, contact or who may take part.
- **Neither:** 404, and the registry is not asked.

Every trial page is marked not to be indexed and none is in the sitemap. A trial's state is worded by the site's fixed phrases in `site/src/lib/trial-page.mjs`, never by the registry's word where that says a trial is recruiting; a build and the tests in `site/tests/trial-pages.test.mjs` fail on a word for how a trial turned out or a word of advice. `LISTED_TRIAL_PAGES=0` at build time, or a build with no listing beside its export, opens no page for an uncited trial and leaves search as it was.
