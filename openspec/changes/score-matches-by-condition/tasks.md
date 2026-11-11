# Tasks

## 1. Search

- [ ] 1.1 Send the claim's indication with the ClinicalTrials.gov search; verify with a recorded fixture that a broad name returns only trials for the condition
- [ ] 1.2 Check ClinicalTrials.gov's current query terms and limits before changing the client, and note them in `docs/sources.md`

## 2. Scoring

- [ ] 2.1 Give the match-scoring step the claim's indication and the record's conditions; verify the two spec scenarios with a fake backend
- [ ] 2.2 Label a same-intervention, other-indication candidate in the review queue; verify `review list` shows the label
- [ ] 2.3 Score a claim's candidates concurrently within the provider's limits; verify the usage ledger still records every call

## 3. Existing data

- [ ] 3.1 Re-score matches stored before this change, or mark them as scored without the indication; verify no old score is shown as if it were new
