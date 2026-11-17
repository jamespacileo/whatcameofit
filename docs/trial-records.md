# Trial record reader

Claim pages retain their ClinicalTrials.gov links and offer “View trial details here” beside them. The local `/trials/NCTxxxxxxxx` page contains a formatted selection of public registry fields, an official source link, retrieval and update dates, and links back to citing claims. It makes no medical interpretation and does not change a claim's status.

The site builds offline. `trial-index.json` is derived from the published export and limits the reader to cited trials. `trial-reader.astro` builds the shared layout template; the Worker fills it with escaped registry text. The reader is complete HTML, requires no JavaScript or registry cookies, and sends no browser request to ClinicalTrials.gov. The template itself is not a public reader page and is excluded from indexing.

The Worker uses the existing public API v2 client with `CONTACT_EMAIL`. It does not need model credentials and never forwards visitor cookies or authorisation. Each fetch has an eight-second deadline. `TRIAL_RECORD_READS` limits uncached upstream requests to 60 per minute per Cloudflare location; cached responses do not spend lookup/model quotas.

Validated raw records are saved in the existing `LOOKUP_RESULTS` KV namespace under `trial-record:v1:<id>` with their retrieval time. A copy is reused for 24 hours and then expires. No older copy is ever shown: when the registry cannot be read, the page says so. Expired, future-dated or mismatched copies are ignored. Missing registry records return 404; temporary failures without a usable copy return 503 with recovery links. Errors use `no-store`. KV outages do not prevent a successful live response.

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

`/trials/NCTxxxxxxxx` then answers in one of three ways:

- **A published claim cites the trial:** the page above, which now leads with the claims citing it.
- **No claim cites it and the listing holds it:** the plain page. The registry's own record is read on request by the same reader, with the same one-day reuse and the same limit of 60 reads a minute for each location. It states the state, phase, conditions, intervention names, enrolment, lead sponsor (never a person: not one the registry classes "INDIV", and not a sponsor-investigator, on this page or a cited trial's), dates, whether results are posted and when, the reason for stopping in the registry's words, and "No news report is linked to this record yet." It shows no summary, outcome, location, contact or who may take part.
- **Neither:** 404, and the registry is not asked.

Every trial page is marked not to be indexed and none is in the sitemap. A trial's state is worded by the site's fixed phrases in `site/src/lib/trial-page.mjs`, never by the registry's word where that says a trial is recruiting; a build and the tests in `site/tests/trial-pages.test.mjs` fail on a word for how a trial turned out or a word of advice. `LISTED_TRIAL_PAGES=0` at build time, or a build with no listing beside its export, opens no page for an uncited trial and leaves search as it was.
