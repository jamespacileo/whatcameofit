# Tasks

## 0. Evidence in the claim brief and timetable (P1)

- [ ] 0.1 <a id="task-f14"></a>Preserve enrollment basis and outcome status in the brief and expanded facts. Render the Impella/NCT05064202 fixture and an actual-enrollment control. [F14](../../../docs/reviews/2026-11-17-code-review.md#finding-f14) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-a-single-trial-has-only-planned-enrollment)

- [x] 1 Mocks: nine sections, 21 variants, three real claims; picks and notes from the operator. `.impeccable/mocks/sections-rebuild/`.
- [x] 2 The record in brief: `said` and `share` on each row (`lib/record-brief.ts`); sentence over a fact sheet. Verify: 1400px, a row opened and its second press; site tests.
- [x] 3 What the report said: groups by who or by kind (`scripts/folds.ts`), firmness mark, bold figures, score behind a press when very sure. Verify: a claim with 12 statements in four reports; site tests.
- [x] 4 Organisations as name chips; other claims as slim rows; "Keep or pass on" as one fact sheet. Verify: 1400px light; the reminders' row is shown by the script; a chip's panel opens.
- [x] 5 Papers under their year, one line each; the dotted ring on a possible record.
- [x] 6 Recorded: milestones over the folded timetable; a link to a record opens every fold it lies in. Verify: a milestone's link opens the fold and lands on its year.
- [x] 7 Trials: the spread by phase, its key, a size bar under each head count, the results ring.
- [x] 8 The whole page: 1400px dark, every section open (7,257px; 9,629px before); 390px light; no console errors; site tests; build.
- [x] 9 Trials' rows as one line: people with a size bar, phase, state with its shape, when results were posted, the trial's number. "Compared with" and "Main measure" are the first facts where the row opens; a trial that has the treatment only as its comparison still says so in sight. Verify: 1400px, a row opened; 390px dark.
- [x] 10 Recorded: a folded year's row is a shape for each of its records, oldest first, and the count, with a key over the timetable; the kinds are said in words to a screen reader. This year and last stay written out. Verify: 1400px light, 390px dark.
- [x] 11 Registry records as entry rows: the title, what the record says and the match on one line; the links, how it was read and what it names where the row opens. A possible record is named as one in words before its title.
- [x] 11a The operator's notes of 2026-11-17 on the built page: only an answer's figures are bold; the brief's sentence a step under the heading; every section's paragraph opens from its heading's info mark (the brief, the statements, possible records, whose heading note says "not counted"); statements distilled (one-line report header, statement first, tag at the line's end); marks coloured by kind; organisations as dotted-underlined names. Verify: 1400px light, two claims; 390px light; the dark values of the mark tokens; site tests.
- [x] 11b "What the report said" after its critique: one list grouped by the order chosen (who, kind, or report where there are several), not report first; tags in aligned columns; the report's title where a row opens. Verify: a claim with 12 statements in eight reports, each order, 1400px; 390px; site tests.
- [x] 11c Section heads after their critique: the heading at 1.5rem, more room over it, the 2px rule directly under every heading, hairlines inside a section. Verify: 1400px light; 390px dark with sections folded; the home page's headings, which share the size.
- [x] 11d Section heads again, the operator finding the 2px rule distracting: no rule under a heading; the heading in the accent blue at weight 650, more room over it, a heading after a folded section closer. Verify: 1400px light and dark; 375px light with sections folded; site tests.
- [x] 11e The fold mark to the left of the heading, in the sheet's margin, as examine.com sets it (looked at on 2026-11-17: hung left on a wide page, at the right on a phone). Verify: 1400px light and dark; 1160px, the narrowest width with side columns; 1000px and 375px, where it stays at the right; a press on the mark folds the section.
- [x] 11f The five fixes of the critique of 2026-11-17 (23 of 36): an opened fact row starts under its label; a paper's title on two lines, whole when opened; the brief's sentence at about 75 characters; the digest counts the trials' states and Phase 4 trials; no approval said by what the site reads; the unconfirmed reading's chip reworded; keys list only the marks drawn, "Stopped early" everywhere. Verify: aducanumab, dupilumab and fenebrutinib at 1400px; dupilumab at 375px; fenebrutinib in the dark theme; site tests.
- [ ] 12 A claim with a dated promise, an approved claim and a claim with one trial looked at in the browser; tablet widths; a print preview.
- [ ] 13 At archive time: fold these additions into the requirements they change ("A claim page answers fixed questions from its records", "Reported statements on the claim page", "Organisations on the claim page", `score-chip`'s "in sight", `review`'s "Lower-band stage reading" where it words the chip).

## 14. Evidence in the claim brief and timetable (P2)

- [ ] 14.1 <a id="task-f15"></a>Derive comparator wording from each trial's codes. Test five sham/zero placebo, placebo-only and mixed fixtures against rendered counts and labels. [F15](../../../docs/reviews/2026-11-17-code-review.md#finding-f15) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-sham-and-placebo-have-distinct-registry-codes)

- [ ] 14.2 <a id="task-f16"></a>Use the dated record types that the timetable includes. Test the SomnoDent dates and preserve the rule for coincident milestones. [F16](../../../docs/reviews/2026-11-17-code-review.md#finding-f16) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-an-article-follows-the-last-registry-event)

- [ ] 14.3 <a id="task-f17"></a>Choose folded-year marks by event kind. Test the August 2021 retraction, an actual trial completion, the legend and accessible wording. [F17](../../../docs/reviews/2026-11-17-code-review.md#finding-f17) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-a-folded-year-contains-a-retraction)
