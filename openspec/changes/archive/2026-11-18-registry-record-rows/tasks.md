# Tasks

## 1. Pipeline

- [x] 1.1 `facts_of` in `resolve/service.py`, written beside every trial summary (search, rescore, redo, named in article, from papers). Verify: `test_candidate_keeps_what_its_registry_record_says`.
- [x] 1.2 Migration 0027 adds `entity_match.record_facts`. Verify: `test_migrations.py`.
- [x] 1.3 `fill_record_facts` and `thenwhat entity record-facts`. Verify: one success and one refusal in `test_cli_resolve.py`.
- [x] 1.4 `record` on each exported match; regenerate `site/export.schema.json` and `site/data/seed-export.json`. Verify: `test_a_match_carries_its_record_field_by_field_once_it_is_read`, schema and seed tests.

## 2. Site

- [x] 2.1 `lib/registry-records.ts` (grouping, phase and state words) and reading headings in `lib/confidence.ts`. Verify: `site/tests/registry-records.test.mjs`.
- [x] 2.2 `RegistryRecords.astro` on the claim page in place of `MatchList` for registry records; styles; `DESIGN.md` entry. Verify: the two scenarios in `site/tests/site.build-test.mjs`; claim page at 1280px and 375px.

## 3. Revisions after critique (2026-11-16)

- [x] 3.1 "Named in the record", counts on the folded heading, section list and digest, registry in sight with a 24px press area, a title slot for an unread record. Verify: site scenarios.
- [x] 3.2 Possible rows open with their match; trial entries and record rows name the registry in one grammar; one "not counted" note with its rule and guide link; groups fold after three. Verify: site scenarios including "Group of more than three records".

- [x] 3.3 The export carries the score for approval by rule and each record's size; the note names that score; record rows use the trials' size, "View trial details here" and one section name; a muted count; the not-read line on its own; the trial page lists possible claims apart. Verify: `test_export_says_the_score_a_match_needs_to_be_approved_by_rule`, site scenarios, `trials.test.mjs`.

## 4. Release

- [ ] 4.1 On the writer: `alembic upgrade head`, then `thenwhat entity record-facts`, before the next export.
- [x] 4.2 `make check` with a branch-specific `TEST_DATABASE_URL`.
