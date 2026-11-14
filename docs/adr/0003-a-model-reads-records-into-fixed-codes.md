# 3. A model may read a stored record into a fixed code; it never decides a status or writes what a reader sees

Date: 2026-11-14. Status: accepted. Change: `openspec/changes/claim-at-a-glance`.

## Context

A claim page says what its records show, and every sentence on it is the site's own fixed wording filled with values read by rule. Some things a lay reader wants cannot be read by rule. A registry gives a trial's main measure as a title ("Change in Yale Global Tic Severity Scale - Revised (YGTSS-R) Total Tic Severity Score") and its timing as free text ("Baseline and week 4 after starting stimulation"). A rule cannot say that the first is a score of symptoms or that the second is four weeks.

On 14 November 2026 the operator asked for a model to interpret records for readers, with the process as deterministic as it can be. Two design critiques that day rejected the forms that interpretation first took: two columns of points for and against, and notes grouped by whether they strengthen or limit the evidence. Both graded the treatment.

A model already reads news reports into reported statements, which are checked by rule, stored with a score and shown as the report's words, not the site's.

## Decision

- A model may be asked to read fields of a stored registry record and return **a code from a fixed list, or a number with a unit from a fixed list, together with the exact words it read**.
- The model is given only fields the trial's facts already carry. It is never given a sponsor's free-text description of a result.
- A rule, with no model in it, checks every reading before it is stored: the words must be in the named field of the stored record, character for character; the code and unit must be in their lists; a number must appear in the words. A reading that fails is not stored.
- The site words every answer from the code. A model never writes, chooses or edits a sentence a reader sees.
- A reading is stored with the record it came from, the version of the instructions, the provider and model, and how sure it is. A record that has not changed is not read again.
- A page shows, for every answer that rests on a reading, the words it was read from, that a model read them, that a rule checked them, and how sure the reading is.

## What does not change

Status is derived only by the pure rules in `pipeline/src/thenwhat/status`, from approved events. No model decides a status, a match score or a trial fact, and readings are inputs to none of them. Trial facts are still read by rule alone. No verdict wording, no medical advice, no article text, no paper abstracts. Provider and model come from the environment.

## Consequences

- A wrong reading can be public until archived, as with any automatic item under ADR 0001. The checks bound how wrong it can be: the words are always the record's own, and when no reading is usable the page shows the registry's title instead.
- Repeatability comes from storing readings, not from a model repeating itself. The site does not promise that the same records always give the same answers.
- The fixed lists are product wording decisions. Adding a code is a change to the site's wording table and to this pipeline step together.
- This narrows what a model may do on this site to a pattern that can be checked. A proposal to let a model summarise, rank or compare is outside it and needs its own decision.

## Amendment, 14 November 2026

The operator set a bar after the first run on the real database. 4 of 722 readings were read as wrong, all of them under 0.8 confidence. A reading the model gives less than `READING_ACCEPT_ABOVE` (0.8 by default, the same as the match and statement bars) is not exported, so the page and the data file give the registry's own words for that answer instead. There is no person review of single readings: the bar is the rule, and a wrong reading at or above it is still removed by archiving under ADR 0001.
