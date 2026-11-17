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
