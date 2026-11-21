## 0. Access (the operator)

- [ ] 0.1 Add the Cloudflare identity provider in Zero Trust, restricted to Palladio account members
- [ ] 0.2 Create the Access application for review.whatcameofit.com: policy Cloudflare Account Member (Palladio) and the operator's email
- [ ] 0.3 Give the AUD tag and team domain for `ACCESS_AUD` and `ACCESS_ISSUER`

## 1. Shell and auth

- [x] 1.1 `review/` from satnaing/shadcn-admin (MIT), trimmed to a read-only shell
- [x] 1.2 Worker: Access token check on every request, operator allowlist, 503 when unset, 403 otherwise
- [x] 1.3 Listed read-only statements; staging overview API and page
- [x] 1.4 Tests on Miniflare with the tests' bundle; `make check-review` in CI
- [ ] 1.5 Wrangler config and `make review-deploy`, used only after 0.2

## 2. Model inventory

- [ ] 2.1 Every pair table, page model and legacy table with rows per version; generic table and record views from the JSON Schemas
- [ ] 2.2 Column deny list (no personal data, no article text), checked by a test

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
