---
target: landing page search, third run on fix/search-answer-placement
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/worktrees/thenwhat/fix-search-answer-placement/site/src/pages/index.astro"
target_fingerprint: "sha256:54be7b54998abd4a72d511ec169a4080923b4356599d7de52caa24327e62b228"
target_path: /Users/jay/Projects/worktrees/thenwhat/fix-search-answer-placement/site/src/pages/index.astro
timestamp: 2026-11-17T18-02-05Z
slug: site-src-pages-index-astro
---
Method: dual-agent (A: design review sub-agent · B: detector/browser sub-agent)

# Third critique: home page search

Target: `fix/search-answer-placement` at 0b569f43, built site from the published export. Not exercised: a real paste, the field's cross, the failure state (source only), a screen reader, a real phone keyboard.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | "Results by topic" counts only the loaded rows: "All results 20" beside "First 20 of 59" |
| 2 | Match system / real world | 3 | "Closest match" on a broad word claims a closeness the rule cannot mean |
| 3 | User control and freedom | 3 | Link lookups leave no history step; "Clear search" only at the top of a 13,295px list |
| 4 | Consistency and standards | 2 | A suggestion says "Non-small cell lung cancer · 11 claims"; taking it gives "16 tracked claims" |
| 5 | Error prevention | 2 | A word the index does not hold is dropped silently |
| 6 | Recognition over recall | 3 | A close-claim guess never says which words it shared |
| 7 | Flexibility and efficiency | 3 | Keys, `?q=`, identifiers and narrowing all work |
| 8 | Aesthetic and minimalist | 3 | On a phone the same fact is said three times in 170px |
| 9 | Error recovery | 3 | The shortened-link message says "Open it" and offers no link |
| 10 | Help and documentation | 3 | The open suggestion panel cuts through the hint line |
| Total | | 28/40 | Good |

## Design Specificity Verdict

LLM assessment: specific, not template. One job, a consistent plain voice, unusually honest count wording. The form is category-standard by the operator's choice and holds. The weak spots are where the box promises more than the index delivers.

Deterministic scan: CLI 0 findings. In-page (results state, 375px): 1 finding, outside the search (h2 "Latest" to h4 inside the hidden "Ahead" list). Measured: status before the treatment line in DOM and on screen in all 20 rows; "Show 20 more" 20 to 40 to 60 rows, no duplicates, page scroll 0px, focus on the first new row; arrows on page rows only; lowest contrast 6.76:1; no horizontal scroll.

## What's Working

1. Honest counts and placement: heading and note update to 40 and 60; the page stays still on "Show 20 more".
2. The box and its answer stay in step: Escape, "Clear search", Back and Forward redraw correctly; a pill press rings the answer heading.
3. Contrast and targets: grey 6.97-8.10:1; phone input 16px, pills 47px, "Show 20 more" 132x47.

## Priority Issues

- [P1] Topic narrowing counts only the loaded rows. For "vaccine" the side column reads "All results 20, Infections 13, Cancer 5, Dementia 1" while 59 match. Fix: count topics from every found page, or label the block "In the first 20". site/src/components/Lookup.astro:1019. Command: /impeccable harden
- [P1] The placeholder's own example underdelivers. "tooth regrowth" gives no suggestions and one claim about an enamel film labelled "Closest match"; Mouth and teeth holds 28 claims. Fix: pick the example words by rule at build from a claim they find well, and test it. site/src/components/Lookup.astro:61. Command: /impeccable onboard
- [P2] The suggestion panel is cramped and clips the hint. At 1280x720 it is 231px tall and shows 4 of 10 rows; its top cuts the hint line; on a phone it is sized from innerHeight, so a keyboard would cover it (inferred). Fix: bring the form to the top first, measure visualViewport.height, start the panel below the hint. Command: /impeccable layout
- [P2] Unknown words are dropped without a word: "…cancercancer" returns the same 16 claims. Fix: say which searched word no tracked claim holds. Command: /impeccable harden
- [P2] On a phone the answer competes with the keyboard and with itself: focus stays in the field after Enter; label, hint, note, heading and count come before the first headline at 389px. Fix: on touch, focus the answer heading after a submit; drop the note on narrow screens. Command: /impeccable adapt

## Persona Red Flags

- Jordan: the example gives one off-topic claim; "Alzheimer's disease 22" and "Alzheimer disease 15" as separate rows; a shared `?q=` link opens scrolled 371px with the h1 off screen.
- Casey: 7,542px of rows before "Show 20 more"; no way back to the box from the bottom; the untracked answer is 1,108px with "Check again later" at the end.
- Sam: suggestion count not announced; search rows have no hidden text saying they search here; document.title never changes.
- Riley: nonsense words pass; a long typed URL runs under the native cross.

## Minor Observations

- "Show 20 more" is 31px tall on desktop; DESIGN.md says 44px.
- In an untracked answer "Check again later" is a 25.5px serif h2 over a 17px answer sentence.
- At 1440x1200 the page still jumps 371px though the answer would fit.
- NCT99999999 still ends "a name can also be typed".
- Feed h2 to h4 skip inside "Ahead": real, outside the search.

## Questions to Consider

1. A word search never gets the full digest because the site "does not know the claim". Why does it get a "Closest match" label at all?
2. Should close-claim guesses be shown when the address's one distinctive word matched nothing?
3. Rows are 350-435px. Is the real problem row height, not paging?
