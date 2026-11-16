# Tasks

## 1. Build

- [x] 1.1 Add `phaseGroups` and `TRIALS_PER_PHASE` to `site/src/lib/trial-facts.ts`, with tests in `site/tests/trial-facts.test.mjs`; verify "Claim with fifteen trials across three phases" and "Claim with twelve Phase 2 trials" on the function
- [x] 1.2 Rebuild the row in `Trial.astro` (people, compared with, main measure and sponsor, state and posted results, identifier) and move the design into the fold; verify "A finished Phase 2 trial with posted results"
- [x] 1.3 Group the trials section of `[slug].astro` by phase, one table per phase with the column names shown on the first, and a fold per phase past ten; verify "Posted results among the trials not shown"
- [x] 1.4 Update `DESIGN.md` (trials table and trial entry) and the column list of "Trials read across as a table" in `page-frame`

## 2. After the critique of 16 Nov 2026 (22/36)

- [x] 2.1 Read each arm from the stored record and decide the claim's arm by exact name match (`trial_facts.py`, `export/build.py`); regenerate the schema and seed export; verify "Arms in the record's words" and "Whether the claim's treatment is the arm under test"
- [x] 2.2 Name the comparison from the arms and say when the claim's treatment is only the comparison; verify "The claim's treatment is only what a trial compares with"
- [x] 2.3 Lead with trials that posted results; word mixed phase headings "<phase>, including …"; keep headings in view; show column names on every table; verify "Trials with posted results lead"
- [x] 2.4 Say registry abbreviations plainly once per section; name the open control; say the match and the design once in the fold, in two columns on a wide screen; verify "An abbreviation in the main measure"
- [x] 2.5 On a phone, put the identifier opposite the size as a 44px target
- [ ] 2.6 On the writer machine (Mac mini), re-export and publish so live claims carry `arms` and `claim_arm`; no new fetch is needed, the facts are read from stored records

## 3. Check

- [x] 3.1 Run `make check` (16 Nov, its parts one by one: ruff, ty, pytest 1693 on a branch test database, site tests 681, site build, extension tests 175)
- [x] 3.2 In the browser preview at 375 and 1280 pixels wide, open the ivonescimab claim; verify no sideways scroll and that it matches mock B
