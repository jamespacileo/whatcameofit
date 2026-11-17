# Tasks

## 1. The approach rule

- [x] 1.1 Add `claims/approach_rule.py` with the registry-type table and the pure `approach_from_registry`, importing `registry_types` from `terms/kinds.py`. Verify with pure tests for: one mapped type, types that do not agree, an unmapped type, no type found, and a configuration test that every table value is a configured approach.
- [x] 1.2 Add `approach_decided_by` and `approach_basis` to the claim model with a new migration (not an edit of an existing one). Verify the migration applies and reverts on a branch-specific test database.
- [x] 1.3 Record who set the approach in `claim add`, `claim edit`, CSV import and the seed loader; clearing an approach clears both columns. Verify with session tests against the test database for each path.
- [x] 1.4 Add the session function that applies the rule to one claim: fills an empty approach, updates or clears one a rule set, leaves any other. Verify with session tests using recorded trial payloads for each scenario of "A rule never overwrites an approach set otherwise".

## 2. Running the approach rule

- [x] 2.1 Call the session function at the end of `fetch_claim`, once the registry records are stored: `thenwhat prepare` and the daily trial refresh both reach a claim's trials through `thenwhat fetch`. Verify with a fetch test that a claim with a drug trial naming its intervention ends with the approach drug and its basis.
- [x] 2.2 Add `thenwhat claim approaches` with `--dry-run` and `--unset`; `--dry-run` also reports agreement with approaches not set by rule. Verify with one success and one refusal CLI test, and a test that `--dry-run` writes nothing.
- [x] 2.3 Export what the registry lists beside the approach (derived through `Records`, whoever set the approach), regenerate `site/export.schema.json` and `site/data/seed-export.json`, add site wording per registry type in `site/src/lib/approach.ts`, and state it beside the approach label. Verify with export tests (Postgres and store give the same) and site tests for a supported approach, an unsupported one, and an unworded type.
- [x] 2.4 Document the command, the table and the "never overwrite" rule in `GLOSSARY.md` (Approach) and the README's command list. Verify the documented commands run as written.

## 3. Clinical categories

- [x] 3.1 Read Europe PMC's and NLM's terms again for republishing a paper's subject headings and record the reading in `docs/sources.md`. Verify the note states what was read, the date, and whether paper headings may be published; if not, drop 3.4 and say so in `design.md`.
- [x] 3.2 Add `clinical/categories.py` with the pure derivation of a claim's categories from trial and paper records, each with its sources. Verify it imports no session, clock or network.
- [x] 3.3 Read a trial record's direct condition terms. Verify with pure tests on recorded payloads for: a direct term is a category, an ancestor is not, two trials giving one category name both.
- [x] 3.4 Add the pure reader of a paper record's major-topic headings in the disease and mental-disorder trees, and include approved papers in the recompute. Verify with pure tests on recorded paper records (abstracts replaced) for: a major disease heading, a check tag, a drug heading, a non-major heading; and a session test for a claim with a paper and no trial.
- [x] 3.5 Gather a claim's approved trial records and its papers' index records through `Records`, as the export does (`claim_clinical_records`). Verify with session tests for: a candidate trial ignored, a category gone once its only record is no longer approved, and a kept claim after a merge holding its own trials' categories (a merge moves no registry match).
- [x] 3.6 Add "Clinical category" to `GLOSSARY.md`. Verify the term is used with that spelling in code, CLI output and site copy by a grep recorded in the task's commit message.

## 4. The MeSH tree

- [x] 4.1 Read `treeNumber` and `broaderDescriptor` in `sources/mesh.py` from the descriptor record, with a recorded fixture, and note the observed fields in `docs/sources.md`. Verify with a source-client test on the fixture, including a descriptor with two tree numbers.
- [x] 4.2 Add the pure tree functions: broader descriptors of a descriptor, and "at or below" by tree-number prefix. Verify with pure tests including a descriptor in two places.
- [x] 4.3 Add `thenwhat clinical tree` to read and store the record of every category in use, each descriptor the mapping names and each broader one, and to list unknown headings and retired descriptors; `thenwhat fetch` does the same for its one claim and keeps its events when NLM does not answer. Verify with one success and one refusal CLI test, that a second run asks the source for nothing, and the two fetch tests.

## 5. Topic mapping and comparison

- [x] 5.1 Add `clinical/topics.py` with the mapping by descriptor identifier, carrying over the 21 headings of `MESH_GROUPS`, and extend the configuration check to refuse a descriptor the stored vocabulary does not hold. Verify with configuration tests for a valid mapping and an unknown descriptor.
- [x] 5.2 Add the pure `derived_topics`. Verify with pure tests for: one topic covering several categories, one claim under two topics, a category no topic covers.
- [x] 5.3 Point the advisory suggestion in `claims/mesh_areas.py` at the mapping and delete `MESH_GROUPS`. Verify the existing suggestion tests pass with the reasons now naming the claim's category.
- [x] 5.4 Add `thenwhat clinical compare` with `--disagreeing`, `--tsv` and `--uncovered`, and the disagreement line in the `prepare` summary. Verify with one success and one refusal CLI test, a test that the counts sum to the number of claims, and that a row carries no article text.
- [x] 5.5 Add `thenwhat clinical categories`, reporting how many unarchived claims have a category from trials, from papers only, and none; with a slug it lists that claim's categories and sources. Verify with one success and one refusal CLI test.
- [x] 5.6 Document the three `clinical` commands and where the disagreement rows go in `docs/daily-run.md` and the README. Verify the documented commands run as written.

## 6. Export and site

- [ ] 6.1 Export each claim's clinical categories with their sources, derived through `Records`, and once per export the tree nodes in use with the MeSH years; a claim whose categories need a MeSH record not yet read is exported as not yet read and counted. Regenerate the schema and the seed export, and report the export time before and after. Verify with export tests for a claim with categories, one without, one not yet read, and that Postgres and the store give the same export.
- [ ] 6.2 Add `site/src/lib/clinical.ts` (parents, children and claims at or below, from tree numbers) and fail the build when the export has categories and no MeSH year. Verify with site tests including a category in two places and a claim counted once.
- [ ] 6.3 Add `/clinical` and `/clinical/[descriptor]` with the NLM credit, the MeSH year and the no-endorsement line. Verify with site tests for: an empty top category not listed, a category page's broader links, claims at and below with statuses, no page for a category without published claims.
- [ ] 6.4 List the clinical categories on the claim page with their source trials and papers. Verify with site tests for a category from a trial and a paper, and a claim with none; and that the site's wording check finds no verdict or advice wording in the new copy.
- [ ] 6.5 Link the clinical index from `/for/clinicians` and the topics page and add the pages to the sitemap. Verify with site tests for both links and the sitemap entries.
- [ ] 6.6 Record the new pages in `DESIGN.md` and report the site build time before and after in the task's commit message. Verify the build passes at phone width with no horizontal scroll on the three new page kinds.

## 7. Integration

- [ ] 7.1 Run `make check` and verify ruff, ty, pytest and the site build pass.
- [ ] 7.2 On the writer, with the operator's go-ahead: run the migration and the three reports of Decision 9, and record the numbers in `design.md` under "Measured". Verify all are written there before any write run.

## Workflow follow-up

- On the writer, after 7.2 and the operator's go-ahead: run `thenwhat claim approaches` and `thenwhat clinical tree`, then `thenwhat clinical compare --tsv`, and paste the rows into the fault tab of the failed-address sheet.
- Export and deploy through the usual pull request (`make deploy` after the merge).
- Decide the switch-over (deriving the vertical, claims under several friendly topics) from the numbers under "Measured", as its own change.
- Archive this change once the published site shows the clinical browse and rule-set approaches.
