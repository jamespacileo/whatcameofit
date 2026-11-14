# Design

## Context

See proposal.md for the motivation. What the code holds today:

- `ClinicalTrials.fetch_trial` asks for a whole study with no field list, and `events/trial.py` stores that study as the `raw_payload` of every event it drafts. So each approved trial already has its full record in the database, results included when the registry has them.
- A second fetch creates no event for a fact that already has one. A trial's stored records therefore differ in age: the registered event keeps the record as it was when first fetched, a later completed or results event keeps a newer one.
- A manually entered trial event stores the entered details as its payload. It has no `protocolSection`.
- `export/build.py` exports events and matches separately. Nothing joins a trial's events to its match, and `ExportedEvent` drops `confidence`. `tests/test_export.py` asserts that the word "confidence" is absent from the export, a rule written before `docs/adr/0001-publish-by-rule-archive-to-remove.md` made scores public.
- The site owns wording: the export carries codes, `site/src/lib/approach.ts` shows the pattern of a label map plus a build failure on an unknown code, and `site/tests/site.test.mjs` fails the build on verdict wording.
- `EntityMatch.reasons` exists and no step writes to it yet (`related-research` task 4.2).

Observed 2026-11-14 on the public record of NCT01596231 (one request, generic client name):

- Top level: `protocolSection`, `resultsSection`, `derivedSection`, `hasResults`.
- `designModule`: `studyType`, `phases`, `designInfo.allocation`, `designInfo.maskingInfo.masking`, `enrollmentInfo {count: 20, type: "ACTUAL"}`. Arms carry a `type` such as `PLACEBO_COMPARATOR`.
- `resultsSection.outcomeMeasuresModule.outcomeMeasures[]`: `type` (`PRIMARY`), `title`, `reportingStatus`, `paramType`, `dispersionType`, `unitOfMeasure`, `timeFrame`, `groups[] {id, title, description}`, `denoms[].counts[] {groupId, value}`, `classes[].categories[].measurements[] {groupId, value, spread}`, and `analyses[]` when the sponsor posted a comparison. This record posted none.
- A results group's `description` read: the treatment "significantly reduced" the measure. That is the sponsor's conclusion inside a field that looks like a label.
- `sponsorCollaboratorsModule.leadSponsor {name, class}`; `eligibilityModule.healthyVolunteers`, `stdAges`.

## Goals / Non-Goals

**Goals:**

- Every fact comes from a field of the stored record by a rule a reader could repeat by opening the record.
- No new request, model call, table or setting.
- The trial becomes one object in the export, so the page can show it once.

**Non-Goals:**

- A reading of whether an outcome was met. The numbers are shown; the claim's "failed" status keeps its own rule.
- Facts for pending candidates. Their stored record is the short search record, without design or results.
- Adverse events, secondary outcomes, participant flow.
- Fresher records than the events hold.

## Decisions

**Facts are derived at export, not stored.** A pure function takes a registry record and returns the facts; the export calls it on the newest record among a trial's approved events. Alternative considered: a `facts` column on `entity_match`, written at fetch. Rejected for now: it needs a migration and a full fetch run before any page changes, and it stores a second copy of what the payload already says. The cost of deriving is that a fact can be as old as the trial's newest event; see Risks.

**The function lives beside `events/trial.py`** as `events/trial_facts.py`, pure like its neighbour: no database, network or clock. It reads the same record, and its tests sit at the same seam (a pure function over a recorded fixture). Alternative considered: inside `export/`. Rejected: the export would then know the registry's field names.

**The export gains `trials` on each claim, defaulting to an empty list.** One entry per registry identifier among the claim's approved trial events: identifier, source name, link, title, phases, state, `facts_as_of`, and a `facts` object that is null when no registry record is held. Each trial's match is found by identifier in `matches`; the score is not copied. `SCHEMA_VERSION` stays 1 because the field is additive and the site already treats a missing list as none, as it does for `status.history`.

**State is reduced to seven codes.** `not_started`, `under_way`, `completed`, `suspended`, `terminated`, `withdrawn`, `unknown`. The registry's recruiting, enrolling-by-invitation and active-not-recruiting all become `under_way`. Alternative considered: pass the registry's status through. Rejected: "Recruiting" beside a condition a reader has is the nearest this site would come to presenting a trial as an option. For a manual trial the state comes from its newest status-change event, or `not_started` when it has none.

**Registry text passes through whole; counts are capped.** Outcome measures, time frames, group titles and the reason for stopping are the registry's words and are not clipped or rephrased, so a reader who opens the record finds the same sentence. At most three planned and three posted primary outcomes are carried, each list with its total.

**Numbers stay strings.** Values, spreads, interval limits and p values are carried as the registry wrote them ("<0.001", "3.4"). Parsing them would invite rounding and comparison, and neither is wanted.

**Only single-row outcomes carry values.** An outcome with one class and one category has one value per group and fits a line. Anything else (time points, subgroups, categories) is carried as a title and a row count, and the page links to the record. Alternative considered: carry every row. Rejected: a table of twelve rows per outcome per trial is the registry's page, not a digest of it.

**Free-text descriptions are never read.** Group descriptions, outcome descriptions and population descriptions are skipped by the function, not filtered afterwards, so the export cannot carry a sponsor's conclusion by accident. A test asserts the fixture's "significantly reduced" sentence is absent from the export.

**An individual sponsor's name is dropped.** The registry class `INDIV` means the lead sponsor is a person. The site holds no personal data beyond subscriber emails, so the kind is exported and the name is not.

**Event confidence is exported as a number on every event.** The site shows it only below 1. The test that forbids the word "confidence" in the export is rewritten to forbid `raw_payload`, `review_state` and `reviewed_by` only; the reason is recorded in the test's name.

**Site wording is one new module**, `site/src/lib/trial-facts.ts`, holding the label for each code (allocation, masking, comparator, study kind, sponsor kind, age group, measure kind, test kind, state) and one function that names any code in the export without a label. The build fails on such a code and on verdict wording in any label, through the existing checks in `site/tests/site.test.mjs`.

**The page section follows `DESIGN.md`.** "Trials on record" replaces the approved trial rows of "Matched registry records": one entry per trial with a summary line (phase, state, participants, design in a few words) and the planned outcomes, results and match reading inside a disclosure, as match readings are today. Candidates keep their own group. Papers get the heading "Matched papers". Layout and type are settled against `DESIGN.md` at implementation; nothing here adds a token.

**The registry's terms are met in the section's own text.** The terms ask that the processing date be shown and that modifications be stated. Each entry shows `facts_as_of`, and the section says the facts are a selection, unaltered, from the linked record.

## Risks / Trade-offs

- [A fact changes in the registry with no new event, such as a planned enrolment revised] → the entry shows the date its record was read. If measurement shows many stale entries, the stored-column alternative above is a contained follow-up: the function and the export shape do not change.
- [A reader takes a p value below 0.05 as proof] → the page states the numbers are as posted by the sponsor, adds no label, and links the record. The method page explains what a posted result is and is not.
- [A registry title or outcome measure itself carries promotional wording] → it is the registry's text, attributed and linked; the site's own labels are the ones checked for verdicts.
- [Thirty-three trials make the page long] → five shown, the rest in one disclosure, ordered furthest phase first.
- [The export grows] → an estimate, not a measurement: about one kilobyte per trial, so 221 approved trials would add about a quarter of a megabyte to a 949-kilobyte file. Measured in task 3.4.
- [Registry fields are missing or oddly shaped on old records] → every read is tolerant: a missing module yields an absent fact, never an error, and the function is run over every stored record in task 3.4 before release.

## Migration Plan

1. Pipeline first: the function, its fixture and tests, then the export fields and regenerated `site/export.schema.json` and `site/data/seed-export.json`.
2. Site second, in the same deploy: an export without `trials` still builds, and the page falls back to the present section.
3. No database change. Rollback is a revert of the deploy; no data is written by this change.

## Open Questions

- Whether serious adverse event counts per group belong on the page. Deferred: it needs its own wording decision under the no-medical-advice rule.
- "Failed" needs a human-set failure flag, and publishing by rule has no human step, so no claim can reach it today. Posted results would make a rule possible. That is a change to `status-derivation` for the operator to decide, and nothing here depends on it.
