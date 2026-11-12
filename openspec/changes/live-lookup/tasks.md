# Tasks

## 1. Engine

- [x] 1.1 Name the trial question and record text in `decide/steps.py` so match scoring and lookup share them; verify the resolution and decision tests still pass
- [x] 1.2 Build `look_up`: read the text, look up stated registry numbers, search names and phrases within the condition, score and rank, name a tracked claim, store nothing; verify the seven lookup tests pass

## 2. Command

- [x] 2.1 Add `thenwhat lookup` for an address or pasted text, with `--json`; verify one success and one refusal

## 3. Measurement

- [x] 3.1 Run the lookup on the articles of claims that have reviewer-approved trials and report how often an approved trial is among the likely candidates and at the top (2026-11-12, twice: 23 of 32 claims, 72%; top candidate approved for 17 then 19)
- [x] 3.2 Record the result and its limits in `docs/lookup.md`

## 4. After the first measurement

- [x] 4.1 Search also under names the model knows the treatment by, reported apart; verify the test passes (measured: no gain with the present model)
- [x] 4.2 Search each part of a combination; verify the test passes
- [ ] 4.3 Map generic names to development codes from an open drug-name source, after checking its terms
- [ ] 4.4 Write registry cache entries with an upsert so two lookups at once cannot collide
- [ ] 4.5 Build a reviewed test set of article and trial pairs across many outlets

## 5. For the operator

- [ ] 5.1 Decide the five points in design.md
