# Tasks

## 1. Search

- [x] 1.1 Send the claim's indication with the ClinicalTrials.gov search; verify with a recorded fixture that a broad name returns only trials for the condition
- [x] 1.2 Check ClinicalTrials.gov's current query terms and limits before changing the client, and note them in `docs/sources.md`

## 2. Scoring

- [x] 2.1 Give the match-scoring step the claim's indication and the record's conditions; verify the two spec scenarios with a fake backend
- [x] 2.2 Label a same-intervention, other-indication candidate in the review queue; verify `review list` shows the label
- [ ] 2.3 Score a claim's candidates concurrently within the provider's limits; verify the usage ledger still records every call
  - Not built on 2026-11-11. Searching within the condition cut the candidates per claim enough that one-at-a-time scoring finishes in minutes. Needs the model client to separate the call from its ledger writes first.

## 3. Existing data

- [x] 3.1 Re-score matches stored before this change, or mark them as scored without the indication; verify no old score is shown as if it were new
