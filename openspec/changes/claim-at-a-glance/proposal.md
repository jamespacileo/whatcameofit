# Proposal

## Why

A claim page holds the facts a skimming reader wants, but not where a skimming reader looks. On the page for the wrist-worn device for Tourette syndrome, the reader has to pass the digest, the facts row and a timetable of nine near-identical registry lines before reaching the trials, and has to open a fold on each trial to learn that the largest enrolled 135 people, had a sham comparison and has posted results. Nothing on the page says what is absent from the record, such as that no trial is running now. A lay reader with a short attention span leaves with the status label and little else.

The operator reviewed four mockups on 2026-11-14 (https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE) and chose board A, "At a glance", to build first.

## What Changes

- A claim page with at least one trial or paper on record gains an "At a glance" section under the digest panel: two short lists, "On record" and "Not on record". Each line is fixed wording filled with counts, sizes and dates, chosen by rule from the records the page already shows. Each line that counts records links to those records on the page.
- A claim page gains a row of links to its sections, each with its count where it has one (trials, papers, the years the timetable spans). A section the page does not have is not linked.
- The neutral-wording build check covers every line.

Out of scope:

- Lines about approval, phase and whether a trial in people exists. The status label, its meaning and the three answers of change `plain-claim-page` already say them, and the page says a thing once.
- Any line read from a news report (for example, that the report gave no trial sizes). The export holds no such fact as a code, and no model writes these lines.
- Posted result values. They stay in each trial entry (mockup board B, a later change).
- The "review style" headings tried in the mockup ("Why it may be worth a look"). They read as a verdict.
- A sticky or scroll-following row, the phone "quick answers" (board C), home page claim cards (board D), cards, the embed, `lookup.json` and the extension.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: a claim page summarises what is and is not on record in two rule-built lists, and links to its own sections with their counts.

## Impact

- `site/src/lib/glance.ts` (new): a pure function from an exported claim to the two lists of line codes with their numbers, dates and link targets. No clock, no network.
- `site/src/lib/status.ts` or a sibling wording module: the fixed wording per line code, under the module-load neutral-wording check.
- `site/src/components/Glance.astro`, `site/src/components/SectionLinks.astro` (new), rendered from `site/src/pages/[slug].astro`.
- `site/src/styles/global.css`, `DESIGN.md`, `GLOSSARY.md`: the section, the row of links and any new term.
- `site/tests/site.test.mjs`: one test per scenario.
- No export shape change: trial state, enrolment, allocation, masking, comparators, posted results and paper years are already exported. No schema or seed regeneration.
- Change `plain-claim-page` (not yet started) adds "In plain words" between the facts row and the timetable. The two sections are independent; `design.md` records where each sits when both exist.
