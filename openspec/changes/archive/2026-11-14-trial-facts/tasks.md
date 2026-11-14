# Tasks

## 1. Registry record and vocabulary

- [x] 1.1 Record the full registry record of NCT01596231 (posted results, placebo arm, healthy volunteers) as `pipeline/tests/fixtures/clinicaltrials/study_NCT01596231_results.json` with a generic client name, leaving the group description that states a conclusion in place for task 2.6, and with contacts removed and investigators' names replaced (done for all three new fixtures); verify the network guard test still passes
- [x] 1.2 Add a second recorded or hand-reduced fixture of a trial whose posted primary outcome has a comparison (p value and method) and one whose outcome has several rows; verify both load as registry records in a test
- [x] 1.3 Add "Trial facts" to `GLOSSARY.md`, and note in `docs/sources.md` which registry fields are republished and how the terms on showing the processing date and stating modifications are met; verify the entry carries today's check date

## 2. Reading the facts

- [x] 2.1 Add `events/trial_facts.py` with a pure function from a registry record to facts: participants with actual or planned, study kind, allocation, masking, comparators; verify tests on `study_NCT02586935.json` (83 actual, randomised, quadruple masking) and on a record with one arm
- [x] 2.2 Read healthy volunteers, age groups, and lead sponsor with its kind, dropping the name when the registry classes the sponsor as an individual; verify tests for an industry sponsor and an individual sponsor
- [x] 2.3 Read up to three planned primary outcomes with the total, and the stated reason for stopping; verify tests for a record with five outcomes and for a terminated trial with and without a reason
- [x] 2.4 Read posted results for up to three primary outcomes: title, time frame, unit, kind of measure, and per group the title, number analysed, value and spread or interval, all as strings; verify on the NCT01596231 fixture (two groups of ten, means 3.4 and 1.9)
- [x] 2.5 Read posted comparisons (groups, p value as written, method, kind of test) and carry a title and row count with no values for an outcome reported in several rows; verify on the fixtures from 1.2
- [x] 2.6 Reduce the registry's overall status to the seven state codes; verify recruiting, enrolling by invitation and active-not-recruiting all read as under way, and that no test output carries a location, contact, eligibility criteria or any group or outcome description (assert the fixture's "significantly reduced" sentence is absent)
- [x] 2.7 Make every read tolerant of a missing module or field; verify a record holding only an identification module yields a trial with no facts and no error

## 3. Export

- [x] 3.1 Add `trials` to each exported claim: one entry per registry identifier among approved trial events, facts read from the record fetched most recently, `facts_as_of` set from it; verify export tests for a trial with four events, two stored records of different ages, and a trial whose events are all pending
- [x] 3.2 List a manually entered trial with identifier, link, phases and state and no facts; verify on the seed claim's jRCT trial
- [x] 3.3 Export `confidence` on every event, and rewrite the export test that forbids the word so it forbids `raw_payload`, `review_state` and `reviewed_by`; verify the export tests and that a posted result with a high p value leaves status and explaining events unchanged
- [x] 3.4 Regenerate `site/export.schema.json` and `site/data/seed-export.json`; run the export against the real database and record in `docs/lookup.md` how many trials gained facts, how many have posted results, how many records raised no fact, and the export's size before and after; verify `make check`

## 4. Site wording and data

- [x] 4.1 Add the trial types to `site/src/lib/export.ts` and a wording module `site/src/lib/trial-facts.ts` with a label for every fact code and a function naming any code without one; verify a site test fails the build on an unknown masking code and on a label containing "successful"
- [x] 4.2 Carry trials and event confidence into the open data file; verify the open data test finds a trial's participants, design, outcomes, results and record date, and no registry record

## 5. Claim page

- [x] 5.1 Add the "Trials on record" section to `site/src/pages/[slug].astro` to `DESIGN.md`: one entry per trial, furthest phase first, with identifier link, phase, state, participants, design, match score, the date the record was read, and planned outcomes, posted results and match reading in a disclosure; verify in the browser on a claim with one trial and on `knee-osteoarthritis-genicular-artery-embolisation` (33 trials: five shown, the rest on request) at phone and desktop widths
- [x] 5.2 Show posted results as group values and each comparison as "p = …" with its method, with the note that numbers are as posted by the sponsor and that the facts are a selection from the linked record; verify the page for a trial with a posted comparison carries no word on whether the outcome was met
- [x] 5.3 Link each trial event in the timetable to its trial entry and add the fact row counting trials with the largest stated size; verify a claim with no trial shows neither section nor row, and a claim whose trials state no number shows the count alone
- [x] 5.4 Move matched papers under "Matched papers", keep candidates in their own group, and correct the count line so a paper is not counted as a registry record; verify on a claim whose only approved match is a paper
- [x] 5.5 Show an event's confidence when it is below 1; verify a follow-up paper at 0.6 reads "Medium match · 60%" and a trial event shows none
- [x] 5.6 Build the site from an export without `trials`; verify the build succeeds and the page shows the present matched-records section
- [x] 5.7 Describe trial facts on the method page: where they come from, that they are the sponsor's posted numbers, and what the site does not say about them; verify the site build and the verdict-wording test

## 6. Integration

- [x] 6.1 Run `make check`, then review the built pages of three claims with posted results against their registry records, number by number; record any mismatch as a failing test before fixing it

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages.
