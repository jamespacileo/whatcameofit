# Proposal

## Why

A claim is one intervention for one indication, but candidate matches are scored on the intervention alone. The first live run (2026-11-11) showed what that does: for a mouse study of sleep in Alzheimer's disease, 31 trials of the laboratory drug in tumours scored 0.99, and for a melanoma vaccine claim the same vaccine's lung, bladder and kidney cancer trials scored the same as its melanoma trials. A reviewer approving by score would publish a wrong status. The assistant's review worked around it with a word comparison outside the pipeline; that belongs in the pipeline.

Broad intervention names are a second cost of the same design: "CAR-T cell therapy" or "Vitamin C" returns hundreds of trials, each scored by its own model call, one after another. Eight such claims did not finish searching in an hour.

## What Changes

- The registry search also sends the claim's indication, so a broad name returns trials for that condition first and far fewer of them.
- Match scoring is given the claim's indication and the record's conditions, and scores "this record is a trial of this intervention for this indication".
- A record for the same intervention in another condition is kept as a lower-scored candidate, labelled as another indication, so the reviewer still sees it.
- Scoring calls for one claim run concurrently, within the provider's limits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `entity-resolution`: search and scoring take the indication into account.

## Impact

- **Pipeline:** `resolve/`, the match-scoring decision step and its prompt, the ClinicalTrials.gov client's query. Recorded fixtures need a condition field.
- **Existing matches:** scores already stored were given without the indication; a re-score command or a note on old scores is needed.
- **Cost and time:** fewer candidates per claim, so fewer model calls.
