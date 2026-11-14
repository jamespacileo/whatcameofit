---
target: mockup boards F-H (the record in brief)
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "url:https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE"
timestamp: 2026-11-14T20-40-55Z
slug: claude-ai-artifact-ypjvb4nta7uhypih9e2hue
---
Method: dual-agent (A: design review · B: detector + browser evidence). Target: reworked boards F, G, H ("The record in brief"). Both assessments saw the boards rendered from a local server. Overlay ran on F and G.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of status | 3 | 7 of 10 rows on F open to nothing; the chevron is not tied to the open state |
| 2 | Match real world | 3 | Closed layer is plain; opened layer has "sponsor", "mean change", "p < 0.02", "Read by rule" |
| 3 | User control | 3 | Native disclosure, no trap; no "open all" |
| 4 | Consistency | 2 | Label differs between F and G; H has no disclosures; "running now"/"recruiting" against the spec's "under way"; digest against brief |
| 5 | Error prevention | 2 | Nothing stops a misreading of −7.13 without its scale |
| 6 | Recognition | 3 | Every answer is visible closed |
| 7 | Flexibility | 3 | Skim or open; no anchor per row |
| 8 | Minimalist | 3 | Quiet, but ten bold answers of equal weight; repeats the facts row |
| 9 | Error recovery | 2 | A withheld answer vanishes silently; no way to report a wrong answer |
| 10 | Help | 3 | "How an answer is made", sham defined inline; p-value link missing on G |
| **Total** | | **27/40** | **Acceptable** |

## Design specificity verdict

The closed layer is authored for this product: questions a relative would ask, answers that are counts and dates, sources one press away. The frame is still a generic FAQ accordion plus spec table. The grouping is not what the design says: group 3 is defined by the answer being "None", not by the kind of fact, so it is the old "limits" column drawn as a list.

Detector: Brief.dc.html and BriefPhone.dc.html exit 2 with one `cramped-padding` each (unlocated, likely the fixed mockup frame; false positive). Advisory `flat-type-hierarchy` on BriefPhone and BriefStates (body 16, h3 16, h2 19, h1 21; largest step 1.19 against 1.25). Contrast passes (lowest 6.85:1). All 10 disclosures toggle; keyboard focus ring is 3px navy. Overlay: `unbalanced-heading` on F's h1; `straggler` ("advice." alone on a line) on G.

## Priority issues

- **[P1] Group 3 is a fault list (F, G, H).** "A trial running now?" and "Approved?" change group by answer; H1 says "None on record" in group 1 and again in group 3; the page opens on three "Yes" and ends on three bold "None on record". Fix: one fixed position per question by kind of fact, whatever its answer; drop the third heading or rename it by subject; change the spec's absence rule to match. Command: /impeccable shape
- **[P1] Digest contradicts brief (F, G).** "Trial registered · No trial with a phase has started" sits above "Yes, in 3 trials… results posted by all 3". Fix: a bridging clause in the digest sentence, or fix the status gloss first. Command: /impeccable clarify
- **[P1] The results row depends on a hole (F, G).** "[LOWEST] to [HIGHEST]" is a non-goal in the spec; without it the numbers are uninterpretable and p < 0.02 becomes the verdict. Fix: no values in the brief; name the measure and link to the trial entry. Command: /impeccable distill
- **[P2] Ten rows (all boards).** About 900px closed on a phone; ten chevrons; all answers at weight 700. Fix: cut to six by merging "Tested in people?" with "How many?", "Results posted?" with "What measured?", and dropping "Papers on record?" and "Who ran the trials?". Command: /impeccable distill
- **[P2] Repeats the facts row (F).** The live page already gives trial count and largest size. Fix: remove one; draw F with the real surrounding page. Command: /impeccable layout

## Persona red flags

- Jordan (first-timer): "Read by rule" / "Read by a model… [SCORE]%" is noise and the score reads as the chance the treatment works; the outlined "Automatic · Unreviewed" pill looks like a button.
- Casey (phone): the label is cut to "Automatic" on G; the inline NCT link is 17px tall; three "None" answers are two screens down.
- Relative of a patient: "Anything measured after 4 weeks? None on record" is a leading question; "The last completed 5 Mar 2023" hints at abandoned; "Unreviewed" beside results is mildly alarming.

## Minor observations

- "Ten questions" in the intro is wrong on other claims.
- 13px source text is small for the page's proof.
- H's approval note should be visible closed.
- The spec says posted values are closed by default; F and G draw them open.
- H has no disclosures and nothing focusable.
- Group headings are the same size as body text.
- Dead links: #guide, #method; #trials on G.
- Mockup artefacts: no viewport meta on G, 15px horizontal scroll on F from the fixed frame.

## Questions to consider

- If every "None" must live under one heading, is that heading anything but a verdict?
- Would six answers as two plain sentences in the digest do more than an accordion?
- Should a model-read row exist at all if its only output is an absence?
