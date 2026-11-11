# Tasks

## 1. Before starting

- [x] 1.1 Put `CONTACT_EMAIL`, `LLM_MODEL`, the provider key, `LLM_INPUT_USD_PER_MTOK` and `LLM_OUTPUT_USD_PER_MTOK` in `.env`; verify `thenwhat resolve tooth-regrowth-usag1` reaches the registries instead of stopping at a refusal
- [ ] 1.2 Read `data/seed/claims-notes.md` and remove or correct any candidate row the operator does not want; verify `thenwhat claim import-csv` accepts the file
  - Checked 2026-11-11 against a scratch database: the file as it stands imports as 25 pending claims, 25 articles and 3 promises. The operator's pass over the rows is still to do, so this task stays open.
- [ ] 1.3 Review the seeded claim `tooth-regrowth-usag1` against its sources and record the result in `data/seed/tooth-regrowth-usag1.json`; verify its `note` says who checked it and when

## 2. First five claims

- [x] 2.1 Import the candidates, then run `extract article`, `resolve` and `fetch` for the first five claims; verify each has a draft, scored candidate matches and a recorded status
- [ ] 2.2 The operator reviews those five fully (draft, matches, follow-up papers, evidence stage); verify `thenwhat review list --claim <slug>` is empty for each and their pages build
- [ ] 2.3 Record the review time per claim and anything the live run got wrong; verify the notes are in `data/seed/claims-notes.md` and the target of 25 is confirmed or adjusted

## 3. The remaining claims

- [x] 3.1 Run extract, resolve and fetch for the remaining claims; verify none stopped on an error that is still unexplained
- [ ] 3.2 The operator reviews everything pending; verify `thenwhat review list` reports an empty queue
- [ ] 3.3 Export and rebuild the site; verify the export holds at least 25 claims, or the adjusted target

## 4. Check what is published

- [ ] 4.1 Check five published claim pages by hand against their sources; verify every status matches what the linked evidence shows
- [x] 4.2 Note any rule that gave a misleading result and open a change for it; verify each note names the claim, the rule and the evidence

## Where this stands (2026-11-11)

All 25 claims were prepared live in 80 seconds and decided by the assistant for the local preview; see the end of `data/seed/claims-notes.md`. Two rules that misled were changed (`score-matches-by-condition`, `quiet-period-starts-at-report`). The tasks still open are the operator's own: the pass over the rows (1.2), the seeded claim (1.3), the review (2.2, 3.2) with its timing (2.3), the export of reviewed claims (3.3) and the hand check (4.1).
