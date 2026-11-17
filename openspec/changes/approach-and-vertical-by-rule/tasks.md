# Tasks

## 1. The approach rule

- [ ] 1.1 Add `claims/approach_rule.py` with the registry-type table and the pure `approach_from_registry`, importing `registry_types` from `terms/kinds.py`. Verify with pure tests for: one mapped type, types that do not agree, an unmapped type, no type found, and a configuration test that every table value is a configured approach.
- [ ] 1.2 Add `approach_decided_by` and `approach_basis` to the claim model with a new migration (not an edit of an existing one). Verify the migration applies and reverts on a branch-specific test database.
- [ ] 1.3 Record who set the approach in `claim add`, `claim edit` (including `--as-assistant`), CSV import and the seed loader; clearing an approach clears both columns. Verify with session tests against the test database for each path.
- [ ] 1.4 Add the session function that applies the rule to one claim: fills an empty approach, updates or clears one a rule set, leaves any other. Verify with session tests using recorded trial payloads for each scenario of "A rule never overwrites an approach set otherwise".

## 2. Running the rule

- [ ] 2.1 Call the session function from `thenwhat prepare` for each claim it handles, after trial matches are decided, and from the daily trial refresh for each claim it changes. Verify with a `prepare` test that a drafted claim with unanimous drug trials ends with the approach drug and its basis.
- [ ] 2.2 Add `thenwhat claim approaches` with `--dry-run` and `--unset`. `--dry-run` also reports, over claims whose approach was not set by rule, how often the rule's answer equals the stored one. Verify with one success and one refusal CLI test, and a test that `--dry-run` writes nothing.
- [ ] 2.3 Document the command, the table and the "never overwrite" rule in `GLOSSARY.md` (Approach) and the README's command list. Verify the documented commands run as written.

## 3. The vertical check

- [ ] 3.1 Add the pure `check_vertical` to `claims/mesh_areas.py`. Verify with pure tests for: a specific vertical in the suggested group, one of two suggested groups, a differing group, no approved trial, no mapped MeSH term.
- [ ] 3.2 Add `thenwhat claim vertical-check` with `--tsv`, listing unarchived disagreeing claims and the three counts. Verify with one success and one refusal CLI test, and that a row carries no article text.
- [ ] 3.3 Add the disagreement line to the `thenwhat prepare` summary. Verify with a `prepare` test where one handled claim disagrees.
- [ ] 3.4 Note in `docs/daily-run.md` where the check appears and how its rows reach the fault tab. Verify the documented command runs as written.

## 4. Export and site

- [ ] 4.1 Add the approach basis to the exported claim, empty unless a rule set the approach. Regenerate `site/export.schema.json` and `site/data/seed-export.json`. Verify the export tests and the schema test pass.
- [ ] 4.2 Add site wording for each registry type in the table to `site/src/lib/approach.ts`, fail the build on a type with no wording, and state the basis beside the approach label on the claim page. Verify with site tests for a rule-set approach, an operator-set approach, and an unworded type.

## 5. Integration

- [ ] 5.1 Run `make check` and verify ruff, ty, pytest and the site build pass.
- [ ] 5.2 On the writer, with the operator's go-ahead: run the migration and `thenwhat claim approaches --dry-run`; record in `design.md` (Decision 7) how many claims the rule would fill and its agreement with hand-set approaches. Verify both numbers are written there before any write run.

## Workflow follow-up

- On the writer, after 5.2 and the operator's go-ahead: run `thenwhat claim approaches`, then `thenwhat claim vertical-check --tsv`, and paste the rows into the fault tab of the failed-address sheet.
- Export and deploy through the usual pull request (`make deploy` after the merge).
- Archive the change once the published site shows rule-set approaches with their basis.
