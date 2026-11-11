# Tasks

## 1. Repository scaffold

- [x] 1.1 Initialise the git repository with the layout in design D1, `.gitignore`, `LICENSE` (MIT) and `LICENSE-DATA` (CC BY 4.0); verify the tree matches D1 and `git status` is clean after the first commit
- [x] 1.2 Create the `pipeline/` uv project on Python 3.12 with the dependencies in design D2 and a `thenwhat` console entry point; verify `uv run thenwhat --help` prints the command list
- [x] 1.3 Create the Astro project in `site/` with a placeholder page; verify `npm run build` writes `site/dist/index.html`
- [x] 1.4 Write `compose.yaml` with the `db`, `pipeline` and `site` services and `.env.example` with every setting named in the design; verify `docker compose up` brings `db` to healthy and `pipeline` connects to it
- [x] 1.5 Add a `check` command (ruff, ty, pytest, site build) and a CI workflow that runs it; verify `check` passes locally and the workflow file runs the same command
- [x] 1.6 Write `CLAUDE.md` (conventions from `SPEC.md` section 9, pointer to `openspec/`), `GLOSSARY.md` (claim, promise, entity, match, evidence event, standing trial, failure flag, overlay) and `README.md`; verify a clean clone reaches a running stack by following the README in under ten commands

## 2. Schema and migrations

- [x] 2.1 Define the models for every table in design D3 and generate the first Alembic migration; verify `upgrade head` then `downgrade base` both succeed on an empty database
- [x] 2.2 Add the constraints (unique slug, unique article URL per claim, one origin paper per claim, unique match per entity and source, unique `dedupe_key` per claim, review-state values); verify a test for each constraint fails the insert it should fail
- [x] 2.3 Have the `pipeline` service apply migrations on start; verify a fresh `docker compose up` ends with all tables present

## 3. Status derivation

- [x] 3.1 Cover every scenario in `specs/status-derivation/spec.md` with one test named after it, written in vertical slices (tests for one rule group, seen failing, then its implementation) at the two agreed seams, `derive` and `refresh_status`; verify the scenario names in the spec and in the tests match one to one
- [x] 3.2 Implement standing trials, the phase mapping and the stage ladder; verify the stage, failed, terminated and preclinical tests pass
- [x] 3.3 Implement the approved and retracted overrides; verify their tests pass
- [x] 3.4 Implement the no-signal overlay with a configurable threshold; verify the overlay tests pass, including the claim with no events
- [x] 3.5 Return the explaining event ids with every result; verify the explanation test passes and the module imports no database, network or clock code
- [x] 3.6 Persist the derived status and change `status_updated_at` only on a real change; verify with a test that re-derives twice

## 4. Claims and manual entry

- [x] 4.1 Implement `claim add` and `article add` with slug and vertical validation; verify tests for duplicate slug, unknown vertical and duplicate article URL
- [x] 4.2 Implement promise records and date parsing (year only, relative, unparseable); verify a test for each scenario in `specs/claims/spec.md`
- [x] 4.3 Keep `first_reported_date` equal to the earliest article date; verify with a test that adds an earlier article later
- [x] 4.4 Implement all-or-nothing `claim import-csv` with row-numbered errors and document the CSV columns in the README; verify tests for a valid file and a file with one bad row
- [x] 4.5 Refuse slug changes once `published_at` is set; verify with a test

## 5. Source clients

- [x] 5.1 Check current terms, authentication and rate limits for ClinicalTrials.gov API v2, Europe PMC, Crossref and the Internet Archive availability lookup, and record them in `docs/sources.md` with the date checked; verify each source has an entry with a link to its terms
- [x] 5.2 Implement the shared base (record contract, Postgres cache, rate limiter, User-Agent with contact address, bounded retry that honours stated delays); verify tests against a fake transport for every scenario in `specs/source-clients/spec.md` that is not source-specific
- [x] 5.3 Add a test-suite guard that fails any test opening a real network connection; verify a deliberately live test fails
- [x] 5.4 Implement the ClinicalTrials.gov client (fetch by identifier, paginated search by intervention term) with recorded fixtures; verify its tests pass offline and the field names in design D5 match the fixtures
- [x] 5.5 Implement the Europe PMC client (paper by DOI, citing papers) with recorded fixtures; verify its tests pass offline
- [x] 5.6 Implement the Crossref client (DOI metadata, retraction and correction notices) with recorded fixtures, including one retracted paper; verify its tests pass offline

## 6. Language model usage and extraction

- [x] 6.1 Implement model configuration from the environment, the usage ledger and the monthly ceiling (design D10); verify tests for missing configuration, ceiling reached, new month, and no credential in error text
- [x] 6.2 Define the extraction schema (including the 500-character summary limit) and the extraction call with bounded retries; verify tests with recorded model responses for a valid draft, an article with no promise, and output that never validates
- [x] 6.3 Implement article retrieval in the order of design D12 (robots.txt, live fetch, archive lookup, pasted text); verify tests for a disallowed URL, a dead link with and without a snapshot, and pasted text
- [x] 6.4 Verify retention: a test that runs extraction to success and to failure and then asserts no table, cache row or log line contains the article text, using a synthetic article
- [x] 6.5 Implement `extract` to store the draft as pending and let the operator edit fields before approval; verify a test that edits the headline and approves

## 7. Decisions and entity resolution

- [x] 7.1 Implement `decide()` with result validation, the decision log and Backend A (design D9); verify tests for a valid result, a choice outside the options, a failed call being logged, and a backend swap by configuration
- [x] 7.2 Implement entity commands (add, add synonym, set origin paper); verify tests for synonym use and origin paper replacement
- [x] 7.3 Implement `resolve` to search the trial registry by name and every synonym, look up paper DOIs, and store de-duplicated pending candidates; verify tests for every scenario in `specs/entity-resolution/spec.md`
- [x] 7.4 Score each new candidate through the entity match decision step; verify the candidate's score equals the logged probability of "match" and the candidate stays pending
- [x] 7.5 Suggest the evidence stage for a draft claim through the evidence stage decision step; verify the claim's stage stays empty until confirmed

## 8. Evidence events

- [x] 8.1 Implement the trial record to events mapping in design D5 with `date_basis`, phase and state; verify tests for a completed trial with results, an unstarted trial, and a terminated trial without a completion date
- [x] 8.2 Implement the follow-up paper rule; verify the four scenarios in `specs/evidence-events/spec.md`
- [x] 8.3 Implement retraction events for the origin paper and follow-up papers; verify with the retracted-paper fixture
- [x] 8.4 Implement `fetch` for a claim: approved matches only, `dedupe_key` from design D6, initial review state from design D7, templated summaries from design D13; verify tests for a pending match, a second fetch, a previously rejected event, and rule approval
- [x] 8.5 Implement `event add` for manual events, with identifier, phase and state required for trial types; verify tests for a regulatory decision, a trial in another registry, and a trial event without an identifier

## 9. Review

- [x] 9.1 Implement `review list` for all claims or one, by kind, showing assertion, source link and score; verify tests for a mixed queue and an empty queue
- [x] 9.2 Implement approve, reject and change-decision for draft claims, matches and events, recording time and decider; verify tests including reversal of a rule approval
- [x] 9.3 Re-derive status after every decision on an event; verify the test that approves a started event moves the claim from trial registered to Phase 1
- [x] 9.4 Implement the failure flag with its required trial, event and source URL; verify tests for a flag with a source, a flag without one, and results posted with no flag
- [x] 9.5 Write human labels to the decision log on match decisions and on evidence stage confirmation; verify tests for a rejected match and a corrected stage
- [x] 9.6 Document the review workflow and every command in the README; verify each documented command runs as written against the seeded example
  - Run on a clean stack on 2026-11-11. Every command ran as written except `extract new`, `extract article`, `resolve` and `fetch`: with no contact address or model key configured they stopped at their documented refusal. Those four are covered by tests with scripted registries and a scripted model, not by a live run.

## 10. Export and site

- [x] 10.1 Implement `export` with the versioned JSON Schema of design D14, overlay recomputed at export time, and `published_at` set on first export; verify tests that a claim with mixed events exports only approved ones, a draft claim is absent, and the output validates against the schema
- [ ] 10.2 Run an Impeccable design pass for the claim page, topic index and home page, producing `PRODUCT.md` and `DESIGN.md`; verify both files exist and the operator has approved the direction
  - 2026-11-11: both files exist and the pages are built in the direction they describe. The direction was chosen without the operator. Left open until the operator approves it or asks for another.
- [x] 10.3 Build the claim page (status with overlay, promises against actual events, event list with source links, status explanation, source article links) and the not-found page; verify against the seeded example at desktop and phone width
- [x] 10.4 Build the topic index, the home page with Pagefind search and recent status changes, and `/it-happened` with its empty state; verify a search for an entity synonym returns the seeded claim
- [x] 10.5 Render a status card image per claim at build time and set it as the link preview image; verify the seeded claim's card shows headline, first reported date, "promised by" year and status, and no day count
- [x] 10.6 Add the footer notices to the shared layout and a build check that rejects verdict wording in status labels; verify every built page contains the footer and the build fails when a label contains "abandoned"
- [x] 10.7 Validate the export against the schema at build start; verify the site builds in a container with no network and no database

## 11. Integration

- [x] 11.1 Find where the seeded example's trial is registered and record it in `data/seed/`; verify the seed file names the registry and whether fetch or a manual event will supply the trial
- [x] 11.2 Write an end-to-end test for the seeded example using recorded fixtures: article URL, extract, approve draft, resolve, approve matches, fetch, approve events, export, site build; verify the built page shows the expected status and every event links to its source
- [x] 11.3 Load the seeded example on a fresh `docker compose up`; verify a clean checkout shows the claim page at the local preview address with no manual steps
- [x] 11.4 Run `check` on a clean checkout with the network disabled; verify it passes

## 12. Backfill

- [ ] 12.1 Compile dental regeneration claims first reported from 2015 to 2020 into `data/seed/claims.csv` with at least one source article each; verify the file imports cleanly and holds at least 25 claims
  - 2026-11-11: the file holds 23 claims, each with a source article whose page was fetched and whose title and date were read from it. It imports cleanly (tried in a rolled-back transaction). Two short of 25: 41 further leads were dropped as unverifiable or out of scope, listed in `data/seed/claims-notes.md`. Left open until the operator accepts 23 or adds two.
- [ ] 12.2 Run extract and resolve for the first five claims and review them fully; verify their pages build, and record the review time per claim to confirm or adjust the 25 to 40 target
- [ ] 12.3 Run extract, resolve, fetch and review for the remaining claims; verify the review queue is empty and the export holds at least 25 claims
- [ ] 12.4 Check five published claim pages by hand against their sources; verify every status matches what the linked evidence shows and note any rule that gave a misleading result

## Workflow follow-up

- Review the change with `code-review`, giving it this change's path and the git comparison point.
- Archive the change once review is complete, which creates the main specs under `openspec/specs/`.
