# Design

## Context

- The lab's page models are Pydantic models in `thenwhat-lab` `src/lab/models/production/pages.py`. Each names its `route`. On the lab's branch for step S9 the pair path has `PairPage`, `PairDataFile`, `PairInterventionPage`, `PairTopicsPage`, `PairTopicPage`, `PairClinicalCategoryPage`, `PairChangesFeed` and `LookupIndex`, with `ConditionPage` and `HomePage` declared.
- `lab.page_files.write` writes `<folder>/<page>/<key>.json` and `<folder>/schemas/<Model>.json`, and removes the file of a page no longer made.
- A field marked `Private()` in the lab cannot be reached by a page model: the lab's diagram check refuses it. So a bundle holds public records only.
- The site today: Astro static build, one Worker (`site/worker/index.mjs`) in front of the built files, which answers `/api/lookup` and 410 for archived claims. KV `LOOKUP_RESULTS` exists. D1 databases `thenwhat-store` and `thenwhat-store-preview` exist in the EU jurisdiction, with the store's schema applied by `store/ingest/migrations`.
- Not measured yet: how many pair pages a full run makes, and Cloudflare's present limit on files in one deployment. Both are read before decision 2's line is fixed (task 1.3).

## Decisions

1. **The bundle is the contract, and the lab's schemas are its definition.** The site keeps no schema of its own. At build, `site/scripts` reads `schemas/*.json` from the bundle and writes TypeScript types and compiled validators (no runtime `eval`, so they also run in the Worker). Alternative: a hand-kept `export.schema.json` as today. Rejected: two definitions drift, and the lab's models already fail its own checks when a page changes.
2. **Which pair pages are built ahead is a rule over the bundle, in one tested function.** Built ahead: a pair with a claim origin, or with more than one supporting trial. Every other published pair is rendered on request. The rule's second half is provisional until the rehearsal's count is known; if every pair fits a build of a few minutes and the file limit, all are built ahead and the on-request path stays for pairs published between builds. Approved by the operator on 2026-11-19.
3. **On request, the Worker reads the pair's file from D1** (`pair_page`, by version, model and address, its parts joined in order), validates it with the compiled validator, renders it with the same Astro component (the Cloudflare adapter, that route alone not prerendered), and caches the answer a day under a key that holds the bundle version. A new version therefore needs no purge. An address the bundle does not hold answers the not-found page.
4. **One current version, in the store.** `pair_bundle.current` marks it. The build reads it once and writes the version into the built site, so built pages and on-request pages of one deployment read one version. Loading a bundle does not change a deployed site until the next deployment; `make deploy` is still the only way to publish. The load keeps the current version and the one before, so the deployment before can still be served and deployed again.
5. **Addresses.** A pair page is at `/{address}`, where a claim page was, not under `/pairs/`: the lab's `/pairs/...` routes exist only while its claim path stands beside it. The bundle's redirects file maps each claim slug to its pair's address; where the two are equal no redirect is written. The Worker answers a moved slug 301, an archived one 410 as today.
6. **The first version shows no reports.** Approved by the operator on 2026-11-19. The pages and feeds that need a first report are removed, not hidden behind a flag, and return when the lab's milestone C gives the bundle `ReportRow`s.
7. **Scores and reasons stay visible.** A pair's intervention keyed by the lab's chooser, and any trial matched below the sure band, shows its score and that no person checked it, as `docs/adr/0001` and `0004` require. `checked_by_person` is on `PairPage`.
8. **`lookup.json` is a bundle file** (`LookupIndex`), copied to its address by the build. Its `claims` map is keyed by the pair's address. The extension's own tests run against the new file before the cutover.
9. **Tests.** A bundle of about 50 pages is cut from the lab's eval slice by the lab's bundle command and committed under `site/tests/bundle/`: real page files, no article text (the bundle holds none). `*.test.mjs` cover the rule of decision 2, the redirects and the validators; `*.build-test.mjs` build the small bundle. No test reads D1 itself: the store's tests use its local engine.
10. **Cutover and rollback.** The cutover is one deployment. Rollback is `make deploy` of the previous commit, which still reads the committed claims export. `site/data/published-export.json` is removed from the repository one week after the cutover, not with it.

11. **D1 holds the bundle, in the store's own database** (operator, 2026-11-19; R2 was the first proposal). Migration `0011_pairs.sql` adds `pair_bundle`, `pair_page` and the row tables `pair`, `pair_intervention`, `pair_intervention_name`, `pair_condition`, `pair_trial`, `pair_trial_facts`, `pair_status_change`, every row under its bundle's version. The tables are a read model: written only by `store/ingest/scripts/load-pairs.mjs` from the lab's page files, through `wrangler d1 execute --file`, never through the merge path, and never read back by the lab. The row tables are derived from the `PairPage` files alone, so the lab's models stay the one definition. A page file longer than a statement may be (100,000 bytes) is kept in parts. The claims tables of the store stay as they are until the cutover.
12. **The build reads D1 through an export of the current version**, as `store-export-rehearsal` already does with `wrangler d1 execute --remote --json`, written to disk as the bundle folder. So the build itself still needs no network once it has the folder, and tests build the small committed bundle.

## Risks

- **The lab's page models change after S9** (S10 adds reports' places, S12 removes the claim pages). The site builds against the small bundle's schemas, so a change shows as a failed build when the small bundle is cut again, not in production.
- **Search engines see every address move at once.** Redirects are permanent and the sitemap lists only new addresses from the first deployment.
- **A wrong join at volume.** The chooser's held-out precision is 0.90 on 28 cases. Decision 7 shows it; the operator removes a wrong pair with the lab's hold, and the next bundle drops its file.
- **On-request pages cost reads.** Cached a day per version; the existing rate limits cover the path.

## Open Questions

- The line of decision 2, after the rehearsal's count and Cloudflare's file limit are read.
- The 11 seeded claims with no coded pair: the operator's decision at the lab's gate S12.1. Until then their pages are built from the last claims export, unchanged.
- Whether `/data/claims/{slug}.json` redirects to `/data/pairs/{address}.json` or answers 410 for people who mirror the open data.
