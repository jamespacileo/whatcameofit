# Design

## Context

- `site/src/pages/[slug].astro` (1,225 lines) draws the claim page in this order: reports, digest panel ("Where it stands"), follow offer, facts row, reported statements, timetable (`#timetable`), trials (`#trials`), papers (`#papers`), organisations, background, other claims, pass it on.
- The export already carries what the directly-read answers need. `ExportedTrial`: `state`, `phases`, `facts`. `ExportedTrialFacts`: `participants`, `allocation`, `masking`, `comparators`, `primary_outcomes` (`measure`, `time_frame`), `results`. `ExportedEvent`: `type`, `event_date`, `trial_id`, `regulatory_outcome`. `ExportedClaim`: `evidence_stage`, `approach`.
- `TrialState` is `started`, `completed`, `terminated`, `withdrawn`, `suspended`. `trial-facts` says a recruiting or active trial is "under way" and that nothing may say a trial is open to participants.
- `trial-facts` also says: facts are read by rule and no model is asked; a sponsor's free-text description of a group or an outcome is not carried, because it can state a conclusion.
- `site-publishing` already requires the facts row to count trials and give the largest size ("The claim page counts its trials"), and the trials section to show posted results as the registry's numbers with no word on how a trial turned out.
- `site/src/lib/status.ts` holds `STATUS_MEANINGS` (`trial_registered`: "A clinical trial is registered. No trial with a phase has started.") and `assertNeutral`, run at module load. `site/src/lib/trial-facts.ts` already words allocation, masking and comparators.
- The pipeline has a precedent for a model reading text into fixed fields with rule checks: `pipeline/src/thenwhat/statements/` (`rules.py` is pure and refuses a proposal; `service.py` proposes, checks and stores).
- `DESIGN.md`: say it once; no colour for any status; nothing moves on scroll; everything pressed is 44 pixels tall on a phone; a section with nothing to show has no placeholder; no meters.
- Three critiques shaped this design; the third (27/40, 2026-11-14) found the frame sound and the wording inexact: a group named "What has been recorded since" that was false for a claim whose trials predate its report, a comparison answer that implied more than the records state, and a digest bridge that kept the contradiction.
- The first two critiques (`.impeccable/critique/`, 2026-11-14). The first (21/40) rejected two valenced columns, three overlapping summaries and oversize result figures. The second (27/40), of a ten-row version with a third group "What the records do not cover", found that group was defined by its answers being "None", that result values could not be read without a scale the spec rules out, that the digest contradicted the brief, and that ten rows was too many.

## Goals / Non-Goals

**Goals:**

- A reader who opens nothing learns, in six lines, how the treatment was tested and what has been recorded since.
- Every answer can be traced to a record in one press.
- A model is used only where a rule cannot read, and what it returns can be checked by a rule.
- The same records give the same page.

**Non-Goals:**

- Judging the evidence or the treatment. No answer says a trial was small, weak, promising or enough.
- Result values in the brief. They stay in the trial entries.
- A model writing or choosing wording a reader sees.
- Reading a paper's abstract or a news article's text.
- Changing a status, a match score or a trial fact.

## Decisions

### 1. Six questions, two groups, fixed places

"The record in brief" sits under the follow offer and before the facts row.

| # | Group | Question | Asked when | Answer (values in braces) | Read |
|---|---|---|---|---|---|
| 1 | How it was tested | Tested in people? | always | "In {n} trials. {max} people in the largest" / "In {n} trials" / "None on record" | directly |
| 2 | How it was tested | Compared with a dummy device / a placebo / another treatment? | any trial states a design | "{k} records name {a dummy device}" ("One record names …") / "No record names one" | directly |
| 2′ | How it was tested | What was the first report about? | no trial, `evidence_stage` known | fixed phrase per stage | directly |
| 3 | How it was tested | What did the largest trial measure? | the largest trial has a primary outcome | fixed phrase per measure kind ("How much a symptom score changed" when the title names a change, else "A symptom score") + " over {follow-up}"; else the registry's title in quotation marks | model, else directly |
| 4 | Where the records stand now | Results posted to the registry? | any trial | "By {k} of {n} trials. The latest on {date}" / "By all {n} trials…" / "None on record" | directly |
| 5 | Where the records stand now | A trial under way? | any trial | "{n} under way" / "None on record. The last finished on {date}" | directly |
| 6 | Where the records stand now | Approved by a regulator? | always | "By {regulator} on {date}. An approval is not advice to take a treatment" / "None on record" | directly |

- A question's place never depends on its answer. "None on record" is said where the question sits. The scenario "Same questions, opposite answers" holds the design to it.
- Questions 2 to 5 need a trial to ask about. With no trial they are left out and 2′ takes the second place.
- The comparator noun comes from the comparator kind and the claim's `approach` (a device gets "dummy device", a drug "placebo"). "Sham" is used and defined once, in the opened answer.
- "Under way", never "recruiting" or "running".
- No answer begins with "Yes": an answer states the fact, so the list does not read as a tally of yes and none.
- Answer 2 counts records that name a comparator. It does not say the other trials had none; a record can be randomised and blinded and still name no comparator in the fields read. The opened answer gives the design as the registry states it and nothing more.
- Whether a measure is a change is read by rule: the registry's title contains the word "change". The model is not asked.
- Under answer 4, outside the disclosure, a link leads to the trials' posted results on the page.
- Every answer opens to at least its record and the date it was read. Terms a lay reader may not know (sham, placebo, regulator, posted, under way) are defined once, in the opened answer that uses them.
- Dates never break across lines.
- Opened, answer 1 gives the other trials' sizes (up to three, else lowest and highest) and whether the largest size is actual or planned.

Rejected, with the critique that rejected each: two lists "On record / Not on record"; two columns "strengthens / limits"; a third group "What the records do not cover" (questions moved group by answer, and the page ended on a run of "None"); ten rows, including "Papers on record?" (a bare number) and "Who ran the trials?"; a question "Anything measured after {follow-up}?" (a leading question whose only answer is an absence; the follow-up is now stated as a fact in answer 3).

### 2. No result values in the brief

Answer 3 names the measure and how long after the start it was taken, and its opened panel gives the registry's own title and time frame and a link to the trial's entry on the page. Group values, numbers analysed and p values are shown only in the trial entry, as today. Reason: a registry gives a measure's scale only in a description `trial-facts` does not carry, and numbers without a scale cannot be read by the reader this section is for.

### 3. Directly-read answers live in one pure site module

`site/src/lib/record-brief.ts` exports `recordBrief(claim): Group[]`; a row is `{ code, values, source }` where `source` names the record, the field, how it was read and the date. Wording is looked up by code in a table beside the status wording and passed through `assertNeutral`. No clock: "under way" is the exported `state`.

### 4. A reading is a code plus the words it came from

New package `pipeline/src/thenwhat/readings/`, built like `statements/`:

- **Input:** for one trial, the titles and time frames of its planned primary outcomes, as `trial-facts` already carries them. Nothing else from the record, so no sponsor description reaches the model.
- **Output, per outcome:** `follow_up` as a number and a unit from `{days, weeks, months, years}` with the time-frame words it read; `measure` as one code from a fixed list with the title words it read.
- **Measure kinds (accepted by the operator on 2026-11-14):** symptom score, how often something happens, a body measurement or lab value, a scan or image finding, survival or time to an event, side effects, use of the treatment, quality of life, a physical test (walking, grip, balance; added after the first run), other.
- **Checks in `rules.py` (pure):** the words are a substring of the named field; the kind and unit are in the lists; for `follow_up`, the number appears in the words. "Other" is stored and yields no plain phrase.
- **Stored with:** the hash of the input fields, the instructions' version, the provider and model from the environment, the confidence, the decider `model`. A trial is read again only when the hash or the instructions' version changes.
- **On the site:** only the largest trial's first primary outcome is used. With no usable reading (none stored, "other", or below the display threshold used for reported statements) answer 3 falls back to the registry's title, and says so. The question never vanishes.

As built (2026-11-14):

- Two tables. `trial_read` holds one row per trial (input hash, instructions' version, provider, model, refusals, when read); `reading` holds the readings that passed. With one table, a trial whose readings were all refused would be asked about again on every run.
- A refusal is stored as outcome, kind and reason on `trial_read`, never the model's words. One more reason than planned: `repeated`, for a second reading of one kind for one outcome in one answer.
- `reading.decided_by` is a new `ReadBy.MODEL`. `Decider` is untouched, because adding to it would change the review constraints on other tables.
- The measure-code enum is `MeasureCode`; `MeasureKind` already names the statistic of a posted result.
- The export's `read_on` is the same date and time as the trial's `facts_as_of`. The export carries a trial's readings only when their input hash matches the facts it shows.
- The confidence is the model's own figure from the same structured answer. There is no second check of it, as reported statements have. The site therefore never shows a reading as certain: the percentage stops at 99.
- The rule checks that the number is in the words as digits of its own (4 is in "week 4", not in "week 14"). It does not check that the unit is in the words.
- `thenwhat readings <slug>…` or `--all`; `thenwhat prepare` runs it as each claim's last step. The seed export carries empty readings: the seed loader cannot seed model-read rows.

First run (2026-11-14), on a copy of the local database (`thenwhat_readings`), not the shared one: main had moved to migration 0015, so this change's migration was renumbered 0016 after merging main. Four claims, 17 trials read in 17 calls, 49 readings stored, none refused by rule, a second run read nothing. Seen on the built pages: the largest Tourette trial reads "How much a symptom score changed over 4 weeks", with its quoted words in the record. What the run showed:

- 13 of 49 readings came back with a confidence of 1.0, shown as "very likely · 100%". The figure is the model's own and says more than a reading can.
- A walking test was read as `other`, so its answer fell back to the registry's title. The list has no kind for a test of physical function.
- "Progression-Free Survival" was read as `survival` and worded "How long until an event, such as a relapse". The event in that trial is the illness getting worse or death, so "such as a relapse" is not exact.
- A trial whose time frame gives no number has no follow-up, and its answer names the measure alone.

Repeatability is delivered by storing readings, not by trusting a model to repeat itself. The site never says the same records always give the same answers.

Rejected: the model writing the plain phrase; reading the outcome description; a second model as checker.

### 5. Readings are their own capability

`trial-facts` stays rule-only. Readings are stored and exported beside facts (`ExportedTrial.readings`), never inside them, and never feed status.

### 6. The digest bridges to the brief

When the status is `trial_registered` and the claim has trials, the digest adds after the status's meaning: "{n} trials are on record and all have finished. The registry gives none a phase." ("and {k} have finished" when not all). It carries no link: on a phone it is drawn ahead of the path, and DESIGN.md lets only unpressable text change its drawn order. It is a count from the same trials the page lists. The status, its place on the path and `STATUS_MEANINGS` are unchanged. This answers the second critique's finding that "No trial with a phase has started" read as a contradiction of "Yes, in 3 trials".

### 7. The facts row loses its trial count

The fact "Trials in people: {n} on record, the largest {max}" is removed from the facts row, because answer 1 says it. The requirement "The claim page counts its trials" moves with it. "Records of studies" stays.

### 8. Provenance in plain words

The section's note reads: "Six answers read from the records on this page. Open one to see the record it came from. They describe the records, not the treatment, and are not advice." (the count is the number of answers shown). It is text, not a pill. Whether a person has checked the page is said once, by the page's existing notice under the digest, and is not repeated here. An opened answer says "Read directly from …" or "A model read the plain wording from the two quoted lines, and a rule checked that both lines are in {record}. How sure the reading is: very likely · 92%."

### 9. Markup

A list of rows, each a native disclosure (`details`/`summary`), so it opens without scripting and prints open; one chevron that turns when the row is open. On a wide screen the group's name stands in a column of its own beside its rows, as the topic directory does; under 40rem it is a heading above them and each question is above its answer. Group names are larger than body text. Rows, and each link on a line of its own in an opened answer, are 44 pixels tall on a phone. The section carries `data-pagefind-ignore`.

### 10. An ADR records the model's part

`docs/adr/0002`: a model may read a stored record into a fixed code with the words it read; a rule checks it; the site words it; it never decides a status and never writes a sentence a reader sees.

### 11. `plain-claim-page`

Its requirement "A claim page answers three fixed questions by rule" is removed from that change, with its task group 3 and `STATUS_ANSWERS`. Its title and provenance-line requirements are untouched. If its provenance line ships first, the brief's note drops "not yet checked by a person" and keeps the rest.

## Risks / Trade-offs

- A run of "None on record" can still read as a verdict on a claim that has little on record. Mitigation: fixed places, absence-only wording, the note, and the neutral-wording check. Accepted: it is what the records say.
- A wrong match makes a wrong answer. Mitigation: answers use only the trials the page shows and link to them, each with its match score.
- A wrong reading is published before a person sees it. Mitigation: exact substring check, a number that must be in the words, the confidence shown, the fallback to the registry's title, and archiving under ADR 0001.
- Export shape change: schema and seed must be regenerated, and tests fail until both match.
- The pipeline work serves one answer in six. Accepted by the operator, who asked for model-read interpretation in this change; the readings are also what a later trial-highlights change would use.
- The bridging sentence is a patch on a status that can look out of step with completed, unphased trials. A status-rule change would remove the need for it.
- The operator accepted ADR 0002, the question table and the measure-kind list with their phrases as written, on 2026-11-14.
