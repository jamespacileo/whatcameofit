# Design

## Context

- `site/src/pages/[slug].astro` (1,225 lines) draws the claim page in this order: reports, digest panel ("Where it stands"), follow offer, facts row, reported statements, timetable (`#timetable`), trials (`#trials`), papers (`#papers`), organisations, background, other claims, pass it on.
- The export already carries what the rule-read answers need. `ExportedTrial`: `state`, `phases`, `facts`. `ExportedTrialFacts`: `participants`, `allocation`, `masking`, `comparators`, `sponsor`, `primary_outcomes` (`measure`, `time_frame`), `results` (`outcomes` with `groups`, `comparisons`, `rows`). `ExportedPaper.facts.year`. `ExportedEvent`: `type`, `event_date`, `trial_id`, `regulatory_outcome`. `ExportedClaim.evidence_stage`.
- `TrialState` is `started`, `completed`, `terminated`, `withdrawn`, `suspended`. `trial-facts` says a recruiting or active trial is "under way" and that nothing may say a trial is open to participants.
- `trial-facts` also says: facts are read by rule and no model is asked; a sponsor's free-text description of a group or an outcome is not carried, because it can state a conclusion; an outcome posted in several rows carries no values.
- `site/src/lib/trial-facts.ts` already words allocation, masking and comparators. `site/src/lib/status.ts` holds `assertNeutral`, run at module load.
- The pipeline has a precedent for a model reading text into fixed fields with rule checks: `pipeline/src/thenwhat/statements/` (`rules.py` is pure and refuses a proposal; `service.py` proposes, checks and stores). Reported statements are exported with `kind`, `basis`, `confidence` and `read_on`.
- `DESIGN.md`: say it once; no colour for any status; nothing moves on scroll; everything pressed is 44 pixels tall on a phone; a section with nothing to show has no placeholder; no meters; a trial entry shows "no colour and no word" for how a trial turned out.
- ADR 0001: items are published by rule, with scores shown; the operator archives what is wrong.

## Goals / Non-Goals

**Goals:**

- A reader who stops after the first screen and a half knows how the treatment was tested, what was posted and what the records do not cover.
- Every answer can be traced to a record in one press.
- A model is used only where a rule cannot read, and what it returns can be checked by a rule.
- The same records give the same page.

**Non-Goals:**

- Judging the evidence or the treatment. No answer says a trial was small, weak, promising or enough.
- A model writing or choosing wording a reader sees.
- Reading a paper's abstract or a news article's text.
- The scale a measure runs on.
- Changing a status, a match score or a trial fact.

## Decisions

### 1. One section, three groups by kind of fact

"The record in brief" sits under the follow offer and before the facts row. The groups are "How it was tested", "What was posted" and "What the records do not cover". The test for a group is the kind of fact, and the scenario "Same question, opposite result" holds the design to it: reversing a result must not move, add or remove a row.

Rejected: two lists "On record / Not on record" (the first draft of this change: the second list held records, and "small" is a judgement); two columns "strengthens / limits" (grades the treatment; the critique's P0).

### 2. The questions

Rows appear in this order. A row whose rule does not apply is absent.

| Group | Question | Applies when | Answer (values in braces) | Read by |
|---|---|---|---|---|
| Tested | Tested in people? | always | "Yes, in {n} trials" / "None on record" | rule |
| Tested | What was the first report about? | no trial, `evidence_stage` known | fixed phrase per stage | rule |
| Tested | How many people? | any trial states `participants` | "{max} in the largest trial; {a} and {b} in the others" (3 or fewer others), else "between {min} and {max} in the others" | rule |
| Tested | Compared with a dummy device / a placebo / another treatment? | any trial states a design | "Yes, in {k} of {n} trials" | rule |
| Tested | Who ran the trials? | any trial states a sponsor | "{n} organisations" + kind clause from the sponsor's kind | rule |
| Tested | A trial under way? | any trial `started` | "Yes, {n} under way" | rule |
| Posted | Results posted to the registry? | any trial | "Yes, by {k} of {n} trials" / "All {n}" | rule |
| Posted | What did the largest trial measure? | largest trial has a primary outcome | fixed phrase per measure kind + ", {follow-up} after starting" when read; else the registry's title as written | model, else rule |
| Posted | Papers on record? | any paper | "{n}" | rule |
| Posted | Approved by a regulator? | an approval event | "Yes, on {date}" | rule |
| Not covered | Anything measured after {follow-up}? | every trial with a primary outcome has a follow-up reading | "None on record" | model |
| Not covered | A trial under way? | trials, none `started` | "None on record. The last completed {date}" | rule |
| Not covered | Results posted to the registry? | trials, none with results | "None on record" | rule |
| Not covered | A registered trial in people? | no trial | "None on record" | rule |
| Not covered | Approved by a regulator? | no approval event | "None on record" | rule |

Notes:

- The comparator question's noun comes from the comparator kind and the claim's `approach` (a device gets "dummy device"; a drug gets "placebo"). "Sham" is used and defined once, in the opened answer.
- "Under way", never "recruiting" or "running": `trial-facts` forbids saying a trial is open to participants. Mockup board H's "recruiting" is wrong on this point.
- "A trial under way?" and "Results posted?" can sit in either the first/second group (yes) or the third (none). That is the absence rule, not a judgement: the third group only ever says "None on record".
- The longest-follow-up row appears only when every trial with a primary outcome has a stored reading; one missing reading would make "none" a guess.

### 3. Rule-read rows live in one pure site module

`site/src/lib/record-brief.ts` exports `recordBrief(claim): Group[]`; a row is `{ code, values, source }` where `source` names the trial, the field, how it was read and the date. Wording is looked up by code in a table beside the status wording and passed through `assertNeutral`. No clock: "under way" is the exported `state`.

Rejected: computing rule-read rows in the pipeline. Everything they need is already exported, and the site already derives trial wording the same way.

### 4. A reading is a code plus the words it came from

New package `pipeline/src/thenwhat/readings/`, built like `statements/`:

- **Input:** for one trial, the titles and time frames of its planned primary outcomes, as `trial-facts` already carries them. Nothing else from the record, so no sponsor description reaches the model.
- **Output, per outcome:** `follow_up` as a number and a unit from `{days, weeks, months, years}` with the time-frame words it read; `measure` as one code from a fixed list with the title words it read.
- **Measure kinds (first list, the operator to confirm in task 1.2):** symptom score, how often something happens, a body measurement or lab value, a scan or image finding, survival or time to an event, side effects, use of the treatment, quality of life, other.
- **Checks in `rules.py` (pure):** the words are a substring of the named field; the kind and unit are in the lists; for `follow_up`, the number appears in the words; "other" is stored but yields no plain phrase on the site.
- **Stored with:** the hash of the input fields, the instructions' version, the provider and model from the environment, the confidence, the decider `model`. A trial is read again only when the hash or the instructions' version changes.
- **Confidence:** the model's stated confidence, shown with the site's existing words ("Very likely in the record · 92%", `site/src/lib/confidence.ts`). A reading below the display threshold used for reported statements is exported and not shown.

Temperature and other request settings are set to the provider's most repeatable values, but repeatability is delivered by storing readings, not by trusting the model to repeat itself. The site never says "the same records always give the same notes".

Rejected: letting the model write the plain phrase (free prose, cannot be checked); reading the outcome description for the scale's range (not carried, can state a conclusion); a second model as checker (the rule check is exact, and a second opinion adds cost without adding certainty).

### 5. Readings are their own capability

`trial-facts` stays rule-only. Readings are stored and exported beside facts (`ExportedTrial.readings`), never inside them, and never feed status. This keeps the existing requirement "No model SHALL be asked" true as written.

### 6. Posted values stay small and closed

The answer about what the largest trial measured is closed by default and names only the measure. Opened, it lists each group's value and number analysed as body-size table rows, with "what the sponsor posted", the statistic's name and "a minus number is a fall" stated by rule from `spread_kind`, `unit` and the sign. A posted comparison is given as the record states it, in the grey source line. An outcome posted in several rows shows no values, as `trial-facts` requires.

### 7. Markup

A list of rows, each a native disclosure (`details`/`summary`), so it opens without scripting and prints open. On a wide screen the group's name stands in a column of its own beside its rows, as the topic directory does; under 40rem the group's name is a heading above them and each question is above its answer. Rows are 44 pixels tall on a phone. The section carries `data-pagefind-ignore` and the "Automatic · Unreviewed" label the extension uses.

### 8. An ADR records the model's part

`docs/adr/0002`: a model may read a stored record into a fixed code with the words it read; a rule checks it; the site words it; it never decides a status and never writes a sentence a reader sees. This narrows, and does not relax, "no model decides status".

### 9. `plain-claim-page`

Its requirement "A claim page answers three fixed questions by rule" is removed from that change, with its task group 3 and `STATUS_ANSWERS`. "Tested in people?" and "Approved by a regulator?" are rows here; "what the next record on the path would be" is not carried over, because the digest's stage track already shows the path. Its title and provenance-line requirements are untouched and can ship before or after this change.

## Risks / Trade-offs

- "What the records do not cover" can still read as a list of faults. Mitigation: absence-only wording, the one-line note, the neutral-wording check, and the reversal scenario.
- A wrong match makes a wrong answer. Mitigation: answers use only the trials and papers the page shows and link to them, each with its match score.
- A wrong reading is published before a person sees it. Mitigation: exact substring check, a number that must be in the words, the confidence shown, and archiving under ADR 0001. A measure kind is a judgement call; "other" is the safe answer and shows the registry's title.
- Export shape change: schema and seed must be regenerated, and tests fail until both match.
- Cost: one call per trial with a primary outcome, once. The spend ceiling stops a run; unread trials simply have no model-read row.
- The status can look out of step with the brief ("Trial registered" above "3 trials, all with results posted"), because a trial with no phase has no later place on the path. Not solved here; it is a status-rule question.
- Open for the operator: the measure-kind list (task 1.2) and whether the follow-up row should also appear when only some trials have a reading, worded "in the trials read".
