## 0. Access (the operator)

- [ ] 0.1 Add the Cloudflare identity provider in Zero Trust, restricted to Palladio account members
- [ ] 0.2 Create the Access application for review.whatcameofit.com: policy Cloudflare Account Member (Palladio) and the operator's email
- [ ] 0.3 Give the AUD tag and team domain for `ACCESS_AUD` and `ACCESS_ISSUER`

## 1. Shell and auth

- [x] 1.1 `review/` from satnaing/shadcn-admin (MIT), trimmed to a read-only shell
- [x] 1.2 Worker: Access token check on every request, operator allowlist, 503 when unset, 403 otherwise
- [x] 1.3 Listed read-only statements; staging overview API and page
- [x] 1.4 Tests on Miniflare with the tests' bundle; `make check-review` in CI
- [x] 1.5a Wrangler config: Worker first for every file, no workers.dev or preview addresses
- [x] 1.5b Overview shows the current D1 bundle apart from the bundle and revision staging was published with
- [ ] 1.5c `make review-deploy`, used only after 0.2

## 2. Model inventory

- [x] 2.1 Catalogue: every table the migrations leave (58, test-held to the migrations, with the migration that made each) and the bundle's 7 page models, with readable names
- [x] 2.2 Per environment: present (rows; current-bundle rows for versioned tables), absent (with the migration or bundle that would hold it), or not readable yet; unlisted tables shown
- [x] 2.3 Records a page at a time; details show the exact table or model, record key, migration or schema, bundle version and the manifest's provenance
- [x] 2.4 Columns never shown (article words, raw payloads, bytes), left out before they reach the browser
- [x] 2.5 Lists and records read one named bundle version (in the address with offset and record key); a version no longer held answers unavailable (410); rows page in primary-key order; each row opens from a focusable link

## 3. Pages and search

- [ ] 3.1 Page list and page view: page file, schema, bundle version, rendered page
- [ ] 3.2 HTTP answers on staging: served, redirected, kept, archived, unknown
- [ ] 3.3 Command menu search by name, alias, condition label, NCT id, address, old claim slug

## 4. Production, read-only

- [ ] 4.1 D1 Read token from the operator; REST reads through the same listed statements
- [ ] 4.2 Staging against production: versions, records, rendering, status codes, search results

## 5. Lab projection

- [ ] 5.1 Read-only export from the lab with run and snapshot ids, after the lab's rerun

## 6. Drafts (needs the operator's approval)

- [ ] 6.1 Drafts in the review site's own store with source, reason, affected pages, base version and the operator's email; through the existing gates only
