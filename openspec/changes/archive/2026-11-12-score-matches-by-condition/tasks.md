# Tasks

## 1. Search

- [x] 1.1 Send the claim's indication with the ClinicalTrials.gov search; verify with a recorded fixture that a broad name returns only trials for the condition
- [x] 1.2 Check ClinicalTrials.gov's current query terms and limits before changing the client, and note them in `docs/sources.md`

## 2. Scoring

- [x] 2.1 Give the match-scoring step the claim's indication and the record's conditions; verify the two spec scenarios with a fake backend
- [x] 2.2 Label a same-intervention, other-indication candidate in the review queue; verify `review list` shows the label

## 3. Existing data

- [x] 3.1 Re-score matches stored before this change, or mark them as scored without the indication; verify no old score is shown as if it were new

## 4. A faster flow (asked for on 2026-11-11)

- [x] 4.1 Score a claim's candidates several to a model call; verify the batch tests pass and one call is one ledger line
- [x] 4.2 Drop a search name that is still broad within the indication; verify the client test "Name that identifies nothing"
- [x] 4.3 Record only names as other names at extraction; verify the name and description tests pass
- [x] 4.4 Keep one line of each registry record on its candidate and show it in the queue; verify the queue test passes and migration 0004 applies
- [x] 4.5 Decide several items at once, by id or by score within a claim; verify the four bulk tests and the command tests pass
- [x] 4.6 Add `thenwhat prepare` for many claims side by side with per-step timings; verify its planning and command tests pass
- [x] 4.7 Time the new flow live; result: five claims prepared in 68 seconds side by side, 134 candidates scored in 14 model calls
- [x] 4.8 Reject by rule a new candidate scored under `MATCH_REJECT_BELOW` (default 0.05), list them with `review list --by-rule`, and let the operator approve any; verify the rule, listing and command tests pass

## Dropped

- Scoring one claim's candidates concurrently (was 2.3). Dropped on 2026-11-12: searching within the indication and scoring several candidates per model call (4.1, 4.2) brought a claim's scoring down to a handful of calls, and `prepare` already runs claims side by side. It would also need the model client to separate a call from its ledger write.
