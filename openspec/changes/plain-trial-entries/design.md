# Design

## Context

- `site/src/components/Trial.astro` draws an entry as: the identifier as a link with the registry's title in grey; "phase · state · participants" in semibold (`trial-standing`); the design in the registry's terms (`trial-design`); a grey line of notes (results posted, match score, papers, record read); then a `details` fold, "Planned measures and posted results", holding a `dl`: kind of study, studied in, sponsor, planned measures, reason for stopping, results, how sure the match is.
- Results inside the fold are a list per outcome: title, time frame and statistic, then one line per group (`groupValueText`: "-7.13 (Standard Deviation 1.1)", "39 analysed"), then comparisons (`comparisonText`). An outcome with several rows per group shows no values.
- `site/src/lib/trial-facts.ts` holds the wording tables (`ALLOCATION_WORDS`, `MASKING_WORDS`, `COMPARATOR_WORDS`, `TRIAL_STATE_WORDS`, `PHASE_WORDS`), `designText`, `participantsText`, `orderTrials`, and `assertNoOutcomeVerdict`.
- `site/src/lib/record-brief.ts` (change `claim-at-a-glance`) holds `MEASURE_PHRASES`, `READING_SHOWN_FROM`, `readingConfidenceLabel`, the rule that a measure is a change when the registry's title says "change", and the dummy noun by approach (a device has "a dummy device").
- The export carries `trials[].readings` (kind, outcome, words, number, unit, code, confidence) and, among `events`, `trial_status_change` with `trial_state: "completed"` and `trial_results_posted`, each with `trial_id` and `event_date`.
- `site-publishing` requires: each trial once with identifier, phase, state, facts and match score; furthest phase first; the first five shown; no word on how a trial turned out; nothing that presents a trial as open to join; the date the record was read.
- `DESIGN.md`, Trial entry: four lines a reader sees, one press opens a pale panel, "no colour and no word says how a trial turned out", notes parted by a gap and never by a mark. Tint is the topic chip's. No meters.
- The first mockup of this idea (board B) was critiqued on 2026-11-14: 30px result figures outranked the status, about 25 tint chips, one trial drawn as a hero.

## Goals / Non-Goals

**Goals:**

- A lay reader who lands on an entry from "The record in brief" learns in its first two lines how big the trial was, what it was compared with and what it measured.
- The posted numbers can be read down a column, with a line that says what they are.
- Nothing is lost: every fact the entry shows today is still on it or one press away.

**Non-Goals:**

- Interpreting a result. No word, colour, size or drawing says how a trial turned out.
- The scale of a measure.
- Reordering trials, or drawing any trial differently from another.
- Paper entries.

## Decisions

### 1. The entry, line by line

| Line | Content | Read from |
|---|---|---|
| Heading (`h3`) | "{n} people" or "{n} people planned"; then ", compared with {comparators}" when the record names any. With no stated size: the registry's title | `participants`, `comparators`, `approach` |
| Identifier | The registry identifier as the link to the record, on the heading's row at the right (under it on a phone) | `trial_id`, `url` |
| Measure sentence | "It measured {phrase}{ over {follow-up}}." Absent with no usable reading | `readings`, `MEASURE_PHRASES` |
| Plain facts | Gap-parted, semibold: how assigned; blinded or open label; state with date; results posted with date; phase when given | `allocation`, `masking`, `state`, `phases`, events |
| Fold control | "Who took part, who ran it, and the posted results" / "…and what it planned to measure" | whether `results` |
| Grey notes | Match score; record read; papers named by its record; "read by a model and checked against the record" when the measure sentence is shown | as today, plus the reading |

The comparators are worded with `COMPARATOR_WORDS`, except that a sham is "a sham device" for a device and "a sham procedure" otherwise, and each is joined with "and with" so the heading reads as a sentence.

### 2. Plain wording for design and state

| Code | Words on the entry | In the fold |
|---|---|---|
| `allocation: randomised` | Assigned at random | Randomised |
| `allocation: non_randomised` | Not assigned at random | Not randomised |
| `masking: none` | Open label: everyone knew what they had | Open label |
| `masking: single` to `quadruple` | Blinded | Single-blind … Quadruple-blind |
| `state: completed` | Finished {date}, or Finished | Completed |
| `state: under_way` | Under way | Under way |
| `state: not_started` | Not started | Not started |
| `state: terminated` | Stopped early | Stopped early |
| `state: withdrawn` | Withdrawn before it started | as today |
| `state: suspended` | Suspended | Suspended |

A code the record does not state yields nothing. Dates come from the claim's events for that trial: the latest `trial_status_change` to `completed`, and the latest `trial_results_posted`. A date never breaks across lines. All strings go through `assertNeutral` and `assertNoOutcomeVerdict`.

"Blinded" covers every level because the difference between levels is who was kept unaware, which the fold states in the registry's term. The operator to confirm this table (task 1.1).

### 3. The measure sentence shares the brief's words

`MEASURE_PHRASES`, the change rule, `READING_SHOWN_FROM` and `readingConfidenceLabel` move from `record-brief.ts` to a small module both import (`site/src/lib/readings.ts`), with a function `measureWords(trial, outcomeIndex)` returning the phrase, the follow-up and the confidence, or null. The brief's answer and the entry's sentence are built from it, so they cannot disagree. In the sentence the phrase starts in lower case.

Only the first main measure is worded. A trial with several main measures lists them all in the fold, in the registry's words, as today.

### 4. The fold

Order inside: who took part; run by; kind of study when not interventional; the registry's title (when the heading is not it); the design in the registry's terms; the phase, or "None given" with a link to the guide entry on phases; planned main measures; reason for stopping; posted results; how sure the match is.

Labels change from registry terms to plain ones where they differ: "Studied in" becomes "Who took part", "Sponsor" becomes "Run by".

### 5. Results as a table

For an outcome with one row per group: a `table` with a `caption` naming the measure and its time frame, and `th scope="col"` for Group, the statistic's name (from `MEASURE_WORDS`: "Mean change" is not derivable; the column is headed by the statistic, "Mean", and the caption carries the measure's title), the spread's name when the record gives one, and "People analysed". Values are the registry's text, right-aligned in tabular figures at body size. Under the table, in grey: "A minus number is a fall." when the title names a change and any value is below zero; the posted comparison as `comparisonText` gives it, with its groups; "The registry record says what this measure runs from and to, and which way is better." with a link to the record.

On a phone the spread moves into the value's cell ("−7.13, standard deviation 1.1") so the table keeps three columns and fits 320 pixels.

Rejected: large figures, tiles, bars or any drawing (the first critique); leaving the list as it is (no column to read down); carrying the scale (not in the facts).

### 6. What stays

Order of trials, the five-trial fold and its control, the entry's `id`, the timetable's links into entries, the highlight of an entry reached by a link, the papers link, the match score and its meaning, print. The entry stays a list item; the heading is an `h3` under the section's `h2`.

### 7. Tests that change

`site/tests/site.test.mjs` and `site/tests/trials.test.mjs` assert today's first lines ("Phase 2 · Completed · 83 participants enrolled", "Randomised, double-blind, compared with placebo"). They are rewritten to the new lines, and the registry's terms are asserted inside the fold.

## Risks / Trade-offs

- A heading of a size alone ("34 people") is bare. Accepted: the record names no comparison, and saying so in a heading would state an absence as a fact about the trial's design.
- "Blinded" hides the level. Mitigation: the level is in the fold in the registry's term.
- The measure sentence rests on a model's reading. Mitigation: the same checks, threshold and fallback as the brief; the grey note says so; no sentence when there is no usable reading.
- A table of results without a scale can still be misread. Mitigation: the line that says the record explains it, the link, and no emphasis on any number. The underlying hole, that the scale is not carried, is a `trial-facts` question.
- Moving the registry's title into the fold makes an entry harder to recognise for a reader who knows the trial by name. Mitigation: the identifier stays visible and the page's search still finds the title.
- Depends on `claim-at-a-glance` (PR 98). If that changes its measure wording, this change follows it through the shared module.
