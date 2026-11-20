# Tasks

Sections 1 and 2 need only the lab's step S9 and its bundle command. Section 5 waits for the lab's full run and the cleared holds.

## 1. Before any build

- [x] 1.1 The operator's decisions of 2026-11-19 recorded in `design.md` (bundle as the only input, on-request tail, registry-first, the store migration superseded)
- [ ] 1.2 Write the deltas that revise or remove the claim-keyed requirements of `claims`, `open-data`, `anniversaries`, `source-pages`, `sharing`, `landing-pages`, `health-areas`, `clinical-classification` and `deployment`, against the pair page models as merged at the lab's S9; verify `openspec validate pairs-site --strict`
- [ ] 1.3 Read Cloudflare's current limits and prices for files in a deployment, and note them, dated, in `docs/sources.md`; with the rehearsal's count of pair pages, fix the line of `design.md` decision 2
- [ ] 1.4 Write the ADR for the bundle and on-request pages, and name the `CLAUDE.md` lines it supersedes
- [x] 1.5 Done 2026-11-19 at the operator's word: `registry-drafted-claims`, `file-based-backfill`, `claim-identity-records` and `same-story-candidates` moved to `openspec/changes/archive/2026-11-19-*`, each with a `SUPERSEDED.md` and without folding its deltas; sections 0, 5 and 6 of `cloudflare-source-of-truth` marked superseded
- [ ] 1.6 Add pair, bundle and address to `GLOSSARY.md` and retire claim's entry to history; verify the terms match the specs

## 2. The bundle in the build

- [x] 2.1 Done 2026-11-19: the pair pages and schemas the lab's own pipeline test writes from its recorded slice (branch `track-pairs-s9`, 12 pairs), committed under `site/tests/bundle/`. To be cut again when S9 merges. Was: The small bundle from the lab, committed under `site/tests/bundle/`; verify it holds no article text and each file fits its schema
- [x] 2.1a Done 2026-11-19: migration `0011_pairs.sql` and `store/ingest/scripts/load-pairs.mjs`; `tests/pairs-load.test.mjs` loads the small bundle on D1's local engine, reads a page back as written, and shows a load stopped early changes nothing a reader sees
- [x] 2.1b Done 2026-11-19 on the operator's machine, preview only: restore bookmark `0000000d-00000000-00005128-6f9a9d6e93f7b1c2397ae4982c34b693` noted first; migrations 0008 to 0011 applied in 1.8 s (0008 rebuilds `work_entry`, which held no row); `load-pairs.mjs --remote` loaded bundle `555633f514ca6c04` in 2.4 s with the local counts (12 pairs, 60 page parts). Production was not touched
- [ ] 2.1c Export the current version from D1 to a bundle folder for the build; verify it equals the folder that was loaded
- [ ] 2.2 Types and compiled validators generated from the bundle's schemas; verify a test that a file with a missing field is refused by name
- [ ] 2.3 The build reads a bundle folder: manifest, checksum, counts; verify tests for a missing file and a wrong checksum
- [ ] 2.4 Status and event wording keyed by the bundle's codes; verify the build stops on a code with no wording and on verdict wording

- [x] 2.2a Done 2026-11-19: `site/src/lib/bundle.ts` reads a bundle folder, checks each file against its schema and each code against the site's wording, and gives a claim's address its pair's; `tests/bundle.test.mjs` on the small bundle. Compiled validators for the Worker and generated types are still 2.2
- [ ] 2.5 **[lab]** `PairOrigin.created_at` is written with no offset, which its schema calls a date-time; the site reads both spellings until the lab writes one. Remove the allowance in `bundle.ts` then

## 3. Pages

- [ ] 3.1 The pair page at `/{address}`, from `PairPage`; verify a build test for a pair with two trials and one with a model-keyed intervention
- [x] 3.1a Done 2026-11-19: `site/src/pair/PairRoute.astro` and `site/src/lib/pairs.ts`: the pair page at `/{address}` with its status, the events that set it, each trial (state, phases, people, dates, arms, results posted, papers, its events), the history of the status, other names and the registries searched; "not yet checked by a person" where `checked_by_person` is false. Built only when `PAIRS_BUNDLE` names a bundle folder, so the claims site is unchanged and a merge to main publishes no pair page until the cutover. `tests/pair-pages.build-test.mjs` builds the small bundle beside the claims fixture, and a build with no bundle. Still open in 3.1: the model-keyed intervention, because the small bundle has none (every intervention is keyed by substance) and `PairPage` carries no score (3.1b)
- [ ] 3.1b **[lab]** Give `PairPage` the chooser's score and reasons for an intervention it keyed, and for a trial matched below the sure band, so the page can show them as decision 7 and `docs/adr/0001` and `0004` require; cut the small bundle with one such pair
- [x] 3.2 Intervention, condition, topic, topics, clinical index and category pages and the changes feed, from their page models. Done 2026-11-19 in 3.2a and 3.2b
- [x] 3.2a Done 2026-11-19: the intervention page (`/intervention/{slug}`), the condition page (`/condition/{slug}`, new), the topic page and the clinical category page list pairs (`site/src/pair/*Route.astro`, `site/src/components/PairTable.astro`). Each list is worked out from the pair pages, not taken from a listing file: a condition or category lists the pairs whose condition is at or beneath it by MeSH tree number, a topic the pairs the lab filed under it, so nothing depends on a pair at every ancestor term (the lab will keep only the most specific). In a build that reads a bundle the claim versions of `/topic/{slug}` and `/clinical/{id}` make no page; without one they are unchanged. `tests/pair-pages.build-test.mjs` checks each list on the small bundle, that the site's roll-up equals the lab's own category lists, and a bundle with the ancestor pair removed. Still open in 3.2: the topics page, the clinical index and the changes feed
- [x] 3.2b Done 2026-11-19: in a build that reads a bundle, `/topics` lists each topic with a pair filed under it, by the bundle's groups, with its count; `/clinical` starts at the categories with no broader one in the bundle; `/changes.xml` has an entry for each change in each pair's history. Without a bundle the three are the claims' as before. The per-topic and per-claim feeds under `/changes/` stay claim-only until 3.4
- [x] 3.3 Home, search index, sitemap, open-data files, cards, embeds and `lookup.json` on pairs; verify the extension's tests against the new index. Done 2026-11-19 in 3.3a, 3.3b and 3.3d
- [x] 3.3a Done 2026-11-19, in a build that reads a bundle: `/lookup.json` lists every pair by its address with the keys the released extension reads, worded by the site as `lookupClaim` words a claim; `/data/pairs/{address}.json` is the lab's `PairDataFile` as written, with the licence, credit and sources, and `/data/pairs.json` indexes them; the sitemap lists pair addresses and the pages that list pairs, and no claim's page. `tests/pair-pages.build-test.mjs` runs the extension's own `stateFor` on the built lookup file for every pair. Without a bundle all three are the claims' as before. Still open in 3.3: home, search index, cards and embeds
- [x] 3.3b Done 2026-11-19, in a build that reads a bundle: the home page is the lookup box, the latest status changes, the topics and the treatments followed (`site/src/pair/PairHome.astro`; the claims home moved unchanged to `site/src/components/ClaimHome.astro`, so each page carries only its own scripts); `/search-detail.json` gives each pair its trials and its first report where the lab holds one; the header links the pairs' topics. The footer's "last checked" and "built" dates still come from the claims export until the bundle has a manifest (2.3). Still open in 3.3: cards and embeds
- [x] 3.3d Done 2026-11-19, in a build that reads a bundle: each pair has its status card in the three shapes (`/og/{address}.png`, `/og/square/`, `/og/tall/`), saying its status, how many trials and the month the status was worked out, and quoting no report; an embed at `/embed/{address}` and its oEmbed description; the pair page names its card, the card's text and its oEmbed
- [x] 3.3c Done 2026-11-19, the assistant's decision recorded as decision 8 in `design.md`: the site builds `lookup.json`. Was: **[operator]** Decision 8 says `lookup.json` is the lab's `LookupIndex` file copied as written. The small bundle holds no `LookupIndex`, so the site builds the file from the pair pages in its own wording (the rule that the site owns all wording). Confirm this replaces decision 8, or have the lab add `LookupIndex` to the bundle
- [ ] 3.4 Remove the pages and feeds of `design.md` decision 6 and every claim-only module; verify no source file reads `export.json`
- [ ] 3.5 `DESIGN.md` and `PRODUCT.md` revised for pairs

## 4. On request and old addresses

- [ ] 4.1 The rule that chooses pages built ahead, one function; verify its tests on the small bundle
- [ ] 4.2 The Worker renders a pair page from D1 at the deployment's version, cached a day; verify a test that it equals the built page, and tests for an unknown address and a file that fails its validator
- [ ] 4.3 Redirects from the moved-addresses file, 410 for archived claims kept; verify a test for each and for a slug equal to its address
- [ ] 4.4 `make deploy`: read the current version, export its bundle, check it, build, deploy; `docs/deploy.md` says how to publish and how to roll back; verify a rehearsal in dry-run mode
- [ ] 4.5 A pull request's preview builds the preview database's bundle; verify one preview
  - The preview database is migrated through 0011 and holds bundle `555633f514ca6c04` as its current version (2.1b, 2026-11-19), ready for 2.1c's export and this preview

## 5. Cutover

- [ ] 5.0 Load the full run's bundle into the preview database, then, with the operator's word, into production; the site in production still reads claims until 5.3
- [ ] 5.1 A preview on the full bundle, read by the operator
- [ ] 5.2 **[operator]** Say the cutover can go ahead
- [ ] 5.3 Deploy; verify 20 old claim addresses redirect, 5 archived ones answer 410, and the sitemap lists pair addresses only
- [ ] 5.4 Freeze `pipeline/`'s publishing and the daily backfill pull requests; a week later remove `site/data/published-export.json`
- [ ] 5.5 Revise `CLAUDE.md` and the README to the new shape; archive this change
