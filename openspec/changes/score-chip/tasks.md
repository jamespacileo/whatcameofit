# Tasks

## 1. Site

- [x] 1.1 `Score.astro` on `Pop.astro` (inline panel), `lib/score-id.ts`, chip styles. Verify: claim page at 1280px and 375px, light and dark.
- [x] 1.2 Wording helpers: `MATCH_MEANING`, `stageReading`, `LOW_READING_MEANING` in `lib/confidence.ts`; `rowScores`, `TERM_SCORE_MEANING` in `lib/glance.ts`. Verify: `site/tests/confidence.test.mjs`.
- [x] 1.3 Chip in place of each score: `Glance.astro`, `RegistryRecordRow.astro`, `MatchList.astro`, `Statements.astro`, `Paper.astro`, `Trial.astro`, the timetable and the lower-band reading in `pages/[slug].astro`. Verify: `site/tests/site.test.mjs`.
- [x] 1.4 `DESIGN.md`: "Score chip" entry; the entries that placed a score.

## 2. Later

- [ ] 2.1 The home page's day list, the live lookup's answers and the extension's cards still word a score their own way.
