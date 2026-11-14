# Tasks

## 1. Decisions on record

- [ ] 1.1 Write `docs/adr/0002` from design decision 8 and show it to the operator; verify it states that a model never decides a status and never writes a sentence a reader sees
- [ ] 1.2 Show the question table and the measure-kind list in design.md to the operator, record any change there, and verify no question or answer judges, predicts, advises or says a trial is open to participants
- [ ] 1.3 In `openspec/changes/plain-claim-page`, remove the requirement "A claim page answers three fixed questions by rule", its design section and task group 3; verify `openspec validate plain-claim-page` passes

## 2. Readings in the pipeline

- [ ] 2.1 Add the reading kinds, measure kinds and units to `pipeline/src/thenwhat/domain.py` and a readings table with a new migration; verify the migration applies to the test database and `ty` passes
- [ ] 2.2 Add `pipeline/src/thenwhat/readings/rules.py` with the pure checks (words in the field, kind and unit in the lists, number in the words) and tests for "Words not in the record", "Number the words do not give" and "Code outside the list"; verify they pass with no database
- [ ] 2.3 Add `pipeline/src/thenwhat/readings/service.py`: build the input from a trial's primary outcomes, ask the configured model for structured output, check, store with the input hash, the instructions' version and the decider `model`, and skip a trial whose hash and version are unchanged; verify against the test database with a recorded model response for "How long the main measure was followed", "What kind of measure", "Model returns a sentence", "Second run with nothing changed" and "Record fetched again with a new time frame"
- [ ] 2.4 Add the CLI command and a step in `thenwhat prepare`, honouring the usage ledger and the spend ceiling; verify one success and one refusal test for the command, and "Spend ceiling reached"
- [ ] 2.5 Export each trial's readings, regenerate `site/export.schema.json` and `site/data/seed-export.json`; verify "Trial with two readings", "Export with no network" and "Claim with and without readings" pass and the schema tests match

## 3. Rule-read rows on the site

- [ ] 3.1 Add `site/src/lib/record-brief.ts` with `recordBrief(claim)` returning the groups and rows of the question table, with each row's source, taking no clock or network; verify it type-checks and that every `TrialState` value is handled
- [ ] 3.2 Add the wording per question and answer code and the fixed phrase per measure kind beside the status wording, reuse the comparator wording of `site/src/lib/trial-facts.ts`, and include every string in the module-load `assertNeutral` call; verify the build fails when a string is given the word "abandoned"
- [ ] 3.3 Add tests to `site/tests/site.test.mjs` for every scenario under "A claim page answers fixed questions from its records" and "Answers are grouped by kind of fact", including "Same question, opposite result"; verify they pass

## 4. The section

- [ ] 4.1 Add `site/src/components/RecordBrief.astro` (a list of native disclosures, the one-line note, the "Automatic · Unreviewed" label, `data-pagefind-ignore`) and render it in `site/src/pages/[slug].astro` after the follow offer and before the facts row; verify on the built Tourette claim page that the three groups appear and each answer opens to its record
- [ ] 4.2 Render the opened answer about what the largest trial measured: body-size rows per group, the statistic and direction in words, the posted comparison in the source line, and no values for an outcome posted in several rows; verify the three scenarios under "Posted results are shown only inside an opened answer"
- [ ] 4.3 Style the section in `site/src/styles/global.css`: the group's name in its own column on a wide screen and above its rows under 40rem, 44-pixel rows on a phone, no status colour, printed open; verify in the browser preview at desktop and phone widths that nothing overflows at 320 pixels, focus is visible, and there are no console errors
- [ ] 4.4 Add tests for "Answer read by rule", "Answer read by a model", "Without scripting" and "Narrow screen"; verify they pass

## 5. Record and check

- [ ] 5.1 Record "The record in brief" under Components in `DESIGN.md`, add "reading" and "under way" to `GLOSSARY.md` if not there, and add the readings step to the README's commands if it lists pipeline steps; verify each file names the new element
- [ ] 5.2 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests all pass
- [ ] 5.3 Run the readings step on the local database, rebuild the export, and open the Tourette claim, one preclinical claim and one approved claim in the browser preview; verify each answer matches the trials and papers listed lower on the page and each model-read answer's quoted words are in the linked registry record

## Workflow follow-up

- Archive the change after the PR is merged.
