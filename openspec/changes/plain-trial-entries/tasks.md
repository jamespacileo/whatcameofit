# Tasks

## 1. Wording

- [x] 1.1 Show the plain-wording table in design.md (decision 2) and the fold's labels (decision 4) to the operator, record any change there, and verify no wording says how a trial turned out or that it is open to participants
- [x] 1.2 Move `MEASURE_PHRASES`, the change rule, `READING_SHOWN_FROM` and `readingConfidenceLabel` from `site/src/lib/record-brief.ts` into `site/src/lib/readings.ts` with `measureWords(trial, outcomeIndex)`, and build the brief's measure answer from it; verify `site/tests/record-brief.test.mjs` passes unchanged
- [x] 1.3 Add to `site/src/lib/trial-facts.ts` the plain words for allocation, masking and state, `trialHeading(trial, approach)`, `plainFacts(trial, dates)` and `foldLabel(trial)`, with every string in the module-load `assertNeutral` and `assertNoOutcomeVerdict` calls; verify the build fails when a string is given the word "abandoned" or "significant"
- [x] 1.4 Add tests to `site/tests/trial-facts.test.mjs` for "Trial with a named comparison", "Trial whose record names no comparison", "Planned size", "Trial that states no size", "Randomised, quadruple-blind, completed, results posted", "Open-label trial", "Trial under way", "Design the record does not state", "Symptom score followed for four weeks", "Same wording as the record in brief" and "No usable reading"; verify they pass

## 2. The entry

- [x] 2.1 Rework the visible lines of `site/src/components/Trial.astro`: heading, identifier, measure sentence, plain facts, grey notes; pass each trial's completion and results dates from `site/src/pages/[slug].astro`; verify on the built Tourette claim page that the three entries read as on board I and each identifier still opens its record
- [x] 2.2 Rework the fold: its control's label, the plain labels, the registry's title, the design in the registry's terms and the phase; verify "Trial with no phase" and "Claim with one completed Phase 2 trial" on built pages
- [x] 2.3 Draw a one-row-per-group outcome as a table with its caption and the grey lines under it, leaving an outcome posted in several rows as it is; verify "Three groups with a mean change", "Measure that is a change", "Posted comparison", "Outcome posted in several rows" and "Fold with no results"
- [x] 2.4 Style the entry and the table in `site/src/styles/global.css`: every entry at one size, no tint, figures at body size in tabular numerals, three columns on a phone; verify in the browser preview at desktop, 390 and 320 pixels that nothing overflows, controls are 44 pixels tall on a phone and there are no console errors
- [x] 2.5 Rewrite the assertions in `site/tests/site.test.mjs` and `site/tests/trials.test.mjs` that read today's first lines, add "Reader follows a timetable entry" and "Narrow screen" checks for the new markup, and verify the site tests pass

## 3. Record and check

- [x] 3.1 Rewrite the Trial entry in `DESIGN.md` for the new lines, the fold and the results table, and add any new term used in site copy to `GLOSSARY.md`; verify both name the new elements
- [x] 3.2 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests all pass
- [x] 3.3 Open the Tourette claim, a claim with more than five trials and a claim whose trial is under way in the browser preview, with an export that carries readings, and verify each entry's heading, measure sentence and results match its registry record

## Workflow follow-up

- Archive the change after the PR is merged.
