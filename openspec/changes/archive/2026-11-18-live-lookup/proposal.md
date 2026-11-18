# Proposal

## Why

The site answers only for articles it already tracks: 104 addresses on 2026-11-12. A reader who pastes any other link gets nothing, or a guess from words in the address. The operator named the missing piece as the product's main reason to exist (2026-11-12): given the address of an article or a social media post, find the clinical trial it is about, or the best candidates.

The pipeline already holds the parts: it reads an article politely, names the treatment and condition, searches ClinicalTrials.gov within the condition, and scores each record against the claim. They only run for claims an operator has entered, and they store everything for review.

## What Changes

- A lookup: text in, ranked trial candidates out, made on the spot and stored nowhere.
- Registry numbers stated in the text are looked up directly.
- The model also gives up to three search phrases for a treatment with no product name, so that a device, a procedure or a diet can be found.
- A claim already tracked under one of the names is named in the answer.
- A command, `thenwhat lookup`, that takes an article address or pasted text.
- A measurement of how often the lookup finds the trials a reviewer approved.

Not in this change, and each needing the operator's decision first (see design.md): showing lookup answers on the public site, where the lookup runs, how a blocked article is read, and reading social media posts by address.

## Capabilities

### New Capabilities

- `live-lookup`: what a lookup returns, what it searches, and what it never keeps.

### Modified Capabilities

None. Match scoring's question is shared with the lookup, unchanged.

## Impact

- New: `pipeline/src/thenwhat/lookup/`, `cli/lookup.py`, their tests.
- `decide/steps.py`: the trial question and the record text are named so both callers use the same words.
- Each lookup costs one model call to read the text and one per twenty records found.
- A lookup writes decision-log and usage rows, as every model call does. It writes no claim, entity, match or article, and none of the text.
