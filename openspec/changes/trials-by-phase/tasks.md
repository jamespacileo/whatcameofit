# Tasks

## 1. Build

- [x] 1.1 Add `phaseGroups` and `TRIALS_PER_PHASE` to `site/src/lib/trial-facts.ts`, with tests in `site/tests/trial-facts.test.mjs`; verify "Claim with fifteen trials across three phases" and "Claim with twelve Phase 2 trials" on the function
- [x] 1.2 Rebuild the row in `Trial.astro` (people, compared with, main measure and sponsor, state and posted results, identifier) and move the design into the fold; verify "A finished Phase 2 trial with posted results"
- [x] 1.3 Group the trials section of `[slug].astro` by phase, one table per phase with the column names shown on the first, and a fold per phase past ten; verify "Posted results among the trials not shown"
- [x] 1.4 Update `DESIGN.md` (trials table and trial entry) and the column list of "Trials read across as a table" in `page-frame`

## 2. Check

- [ ] 2.1 Run `make check` (16 Nov: site tests 677/677 and site build pass; ruff, ty and pytest not run, no pipeline change)
- [x] 2.2 In the browser preview at 375 and 1280 pixels wide, open the ivonescimab claim; verify no sideways scroll and that it matches mock B
