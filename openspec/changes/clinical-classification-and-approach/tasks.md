# Tasks

## 1. The approach rule

- [ ] 1.1 Add `claims/approach_rule.py` with the registry-type table and the pure `approach_from_registry`, importing `registry_types` from `terms/kinds.py`. Verify with pure tests for: one mapped type, types that do not agree, an unmapped type, no type found, and a configuration test that every table value is a configured approach.
- [ ] 1.2 Add `approach_decided_by` and `approach_basis` to the claim model with a new migration (not an edit of an existing one). Verify the migration applies and reverts on a branch-specific test database.
- [ ] 1.3 Record who set the approach in `claim add`, `claim edit` (including `--as-assistant`), CSV import and the seed loader; clearing an approach clears both columns. Verify with session tests against the test database for each path.
- [ ] 1.4 Add the session function that applies the rule to one claim: fills an empty approach, updates or clears one a rule set, leaves any other. Verify with session tests using recorded trial payloads for each scenario of "A rule never overwrites an approach set otherwise".

## 2. Running the approach rule

- [ ] 2.1 Call the session function from `thenwhat prepare` for each claim it handles, after trial matches are decided, and from the daily trial refresh for each claim it changes. Verify with a `prepare` test that a drafted claim with unanimous drug trials ends with the approach drug and its basis.
- [ ] 2.2 Add `thenwhat claim approaches` with `--dry-run` and `--unset`; `--dry-run` also reports agreement with approaches not set by rule. Verify with one success and one refusal CLI test, and a test that `--dry-run` writes nothing.
- [ ] 2.3 Add the approach basis to the exported claim, regenerate `site/export.schema.json` and `site/data/seed-export.json`, add site wording per registry type in `site/src/lib/approach.ts`, and state the basis beside the approach label. Verify with export tests and site tests for a rule-set approach, an operator-set approach and an unworded type.
- [ ] 2.4 Document the command, the table and the "never overwrite" rule in `GLOSSARY.md` (Approach) and the README's command list. Verify the documented commands run as written.

## 3. Clinical categories

- [ ] 3.1 Read Europe PMC's and NLM's terms again for republishing a paper's subject headings and record the reading in `docs/sources.md`. Verify the note states what was read, the date, and whether paper headings may be published; if not, drop 3.4 and say so in `design.md`.
- [ ] 3.2 Add the `claim_category` table with a new migration. Verify the migration applies and reverts on a branch-specific test database.
- [ ] 3.3 Add the pure reader of a trial record's direct condition terms and the session function that recomputes a claim's categories from approved trials. Verify with pure tests on recorded payloads and session tests for: a direct term stored, an ancestor not stored, a candidate trial ignored, a category removed when its only match is rejected.
- [ ] 3.4 Add the pure reader of a paper record's major-topic headings in the disease and mental-disorder trees, and include approved papers in the recompute. Verify with pure tests on recorded paper records (abstracts replaced) for: a major disease heading, a check tag, a drug heading, a non-major heading; and a session test for a claim with a paper and no trial.
- [ ] 3.5 Call the recompute from `prepare`, the daily trial refresh, claim merge and archive. Verify with a `prepare` test and a merge test that the surviving claim holds both claims' categories with their sources.
- [ ] 3.6 Add "Clinical category" to `GLOSSARY.md`. Verify the term is used with that spelling in code, CLI output and site copy by a grep recorded in the task's commit message.

## 4. The MeSH tree

- [ ] 4.1 Read `treeNumber` and `broaderDescriptor` in `sources/mesh.py` from the descriptor record, with a recorded fixture, and note the observed fields in `docs/sources.md`. Verify with a source-client test on the fixture, including a descriptor with two tree numbers.
- [ ] 4.2 Add the pure tree functions: broader descriptors of a descriptor, and "at or below" by tree-number prefix. Verify with pure tests including a descriptor in two places.
- [ ] 4.3 Add `thenwhat clinical tree` to read and store the record of every category in use and each broader one, and to list missing and retired descriptors. Verify with one success and one refusal CLI test against recorded fixtures, and that a second run asks the source for nothing.

## 5. Topic mapping and comparison

- [ ] 5.1 Add `clinical/topics.py` with the mapping by descriptor identifier, carrying over the 21 headings of `MESH_GROUPS`, and extend the configuration check to refuse a descriptor the stored vocabulary does not hold. Verify with configuration tests for a valid mapping and an unknown descriptor.
- [ ] 5.2 Add the pure `derived_topics`. Verify with pure tests for: one topic covering several categories, one claim under two topics, a category no topic covers.
- [ ] 5.3 Point the advisory suggestion in `claims/mesh_areas.py` at the mapping and delete `MESH_GROUPS`. Verify the existing suggestion tests pass with the reasons now naming the claim's category.
- [ ] 5.4 Add `thenwhat clinical compare` with `--disagreeing`, `--tsv` and `--uncovered`, and the disagreement line in the `prepare` summary. Verify with one success and one refusal CLI test, a test that the counts sum to the number of claims, and that a row carries no article text.
- [ ] 5.5 Add `thenwhat clinical categories` with `--dry-run`, applying the recompute to every unarchived claim and reporting how many are filed by trials, by papers only, and not at all. Verify with a CLI test that `--dry-run` writes nothing.
- [ ] 5.6 Document the three `clinical` commands and where the disagreement rows go in `docs/daily-run.md` and the README. Verify the documented commands run as written.

## 6. Export and site

- [ ] 6.1 Export each claim's clinical categories with their sources, and once per export the tree nodes in use with the MeSH year; refuse the export while a needed record is missing. Regenerate the schema and the seed export. Verify with export tests for a claim with categories, one without, and the refusal.
- [ ] 6.2 Add `site/src/lib/clinical.ts` (parents, children and claims at or below, from tree numbers) and fail the build when the export has categories and no MeSH year. Verify with site tests including a category in two places and a claim counted once.
- [ ] 6.3 Add `/clinical` and `/clinical/[descriptor]` with the NLM credit, the MeSH year and the no-endorsement line. Verify with site tests for: an empty top category not listed, a category page's broader links, claims at and below with statuses, no page for a category without published claims.
- [ ] 6.4 List the clinical categories on the claim page with their source trials and papers. Verify with site tests for a category from a trial and a paper, and a claim with none; and that the site's wording check finds no verdict or advice wording in the new copy.
- [ ] 6.5 Link the clinical index from `/for/clinicians` and the topics page and add the pages to the sitemap. Verify with site tests for both links and the sitemap entries.
- [ ] 6.6 Record the new pages in `DESIGN.md` and report the site build time before and after in the task's commit message. Verify the build passes at phone width with no horizontal scroll on the three new page kinds.

## 7. Integration

- [ ] 7.1 Run `make check` and verify ruff, ty, pytest and the site build pass.
- [ ] 7.2 On the writer, with the operator's go-ahead: run the migrations and the three dry runs of Decision 9, and record the numbers in `design.md` under "Measured". Verify all are written there before any write run.

## Workflow follow-up

- On the writer, after 7.2 and the operator's go-ahead: run `thenwhat claim approaches`, `thenwhat clinical tree`, `thenwhat clinical categories`, then `thenwhat clinical compare --tsv`, and paste the rows into the fault tab of the failed-address sheet.
- Export and deploy through the usual pull request (`make deploy` after the merge).
- Decide the switch-over (deriving the vertical, claims under several friendly topics) from the numbers under "Measured", as its own change.
- Archive this change once the published site shows the clinical browse and rule-set approaches.
