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
- [ ] 3.2 Intervention, condition, topic, topics, clinical index and category pages and the changes feed, from their page models
- [ ] 3.3 Home, search index, sitemap, open-data files, cards, embeds and `lookup.json` on pairs; verify the extension's tests against the new index
- [ ] 3.4 Remove the pages and feeds of `design.md` decision 6 and every claim-only module; verify no source file reads `export.json`
- [ ] 3.5 `DESIGN.md` and `PRODUCT.md` revised for pairs

## 4. On request and old addresses

- [ ] 4.1 The rule that chooses pages built ahead, one function; verify its tests on the small bundle
- [ ] 4.2 The Worker renders a pair page from D1 at the deployment's version, cached a day; verify a test that it equals the built page, and tests for an unknown address and a file that fails its validator
- [ ] 4.3 Redirects from the moved-addresses file, 410 for archived claims kept; verify a test for each and for a slug equal to its address
- [ ] 4.4 `make deploy`: read the current version, export its bundle, check it, build, deploy; `docs/deploy.md` says how to publish and how to roll back; verify a rehearsal in dry-run mode
- [ ] 4.5 A pull request's preview builds the preview database's bundle; verify one preview

## 5. Cutover

- [ ] 5.0 Load the full run's bundle into the preview database, then, with the operator's word, into production; the site in production still reads claims until 5.3
- [ ] 5.1 A preview on the full bundle, read by the operator
- [ ] 5.2 **[operator]** Say the cutover can go ahead
- [ ] 5.3 Deploy; verify 20 old claim addresses redirect, 5 archived ones answer 410, and the sitemap lists pair addresses only
- [ ] 5.4 Freeze `pipeline/`'s publishing and the daily backfill pull requests; a week later remove `site/data/published-export.json`
- [ ] 5.5 Revise `CLAUDE.md` and the README to the new shape; archive this change
