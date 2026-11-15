---
target: claim page (At a glance)
total_score: 22
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/site/src/pages/[slug].astro"
target_fingerprint: "sha256:1aa3fa6cde760af0eb55041987038e6c536420c44ee6d4dc884fa0eb09d1edcc"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/site/src/pages/[slug].astro
timestamp: 2026-11-15T20-16-20Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review · B: detector + browser overlay)

Target: claim page, site/src/pages/[slug].astro, after "At a glance" + band facts (PR 161). Pages: alexander-disease-zilganersen (4 cards), tourette-syndrome-wrist-nerve-stimulation (2 cards), pancreatic-cancer-daraxonrasib / alzheimers-nano-eraser (no cards). Desktop 1440/1024, phone 375.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Status, latest record, "not checked by a person" clear. Band notes "Matched by exact name" need the card to decode. |
| 2 | Match system / real world | 2 | Indexing definitions ("used as a probe (OLIGONUCLEOTIDE PROBES). (Dorland, 28th ed)"), "ZILGANERSEN" in caps, DSM citations inline. |
| 3 | User control and freedom | 3 | Folds and chips work; At a glance is the one long section left open on phone (~3 screens to pass). |
| 4 | Consistency and standards | 2 | Band "Kind: Oligonucleotide · Matched by exact name" (drug record) vs row "Kind of treatment: Oligonucleotides · 100%" (MeSH). Same term in two cases (Alexander disease / Alexander Disease). |
| 5 | Error prevention | 3 | Guardrail wording careful; "81%" in the band under the status is a misreading risk. |
| 6 | Recognition rather than recall | 3 | Section chips with counts good; band facts are links with no visible link cue. |
| 7 | Flexibility and efficiency | 2 | No compact view of cards; every definition open. |
| 8 | Aesthetic and minimalist design | 1 | Treatment and condition said 3 times before the first card; 2–4 underlined credit lines per card in the reading flow. |
| 9 | Error recovery | n/a | No input on the page beyond the Mastodon field. |
| 10 | Help and documentation | 3 | Method links and explained status strong; 9-sentence card note too long. |
| **Total** | | **22/36** | **Acceptable (61%)** |

## Design Specificity Verdict

LLM assessment: the page is authored for this product (digest that answers in words, stage track as position not progress, amber only for promises, the record in brief). "At a glance" is the generic part: it copies Examine's shape (label column, value column) but not its point, which is short answers. Every row carries a whole TermCard (role line, term, open definition, citation, score), so it reads as a database record viewer, not a glance. The band facts repeat the headline.

Deterministic scan: `impeccable detect` on the page and 7 components: 0 findings. Browser overlay: line-length on p.lede (~95 ch), p.glance-note (~96 ch) and the Data sources paragraph (~89 ch) on every page — true positives; stragglers on p.lede, p.sentence, p.means, p.entry-note — minor; flat type hierarchy at phone width (visible h1 23px / h2 20.4 / h3 18.7 / body 17, step 1.13) — partly real (two flagged h2s are visually hidden); th.year overflow — transient, not reproducible at 6 widths; cramped-padding on .brief-group — false positive (rule-headed group, not a box). The detector caught the measure and phone-scale issues the review missed; the review caught the structural ones the detector cannot see.

## Overall Impression

The answer still lands first and well. The new section turned the second screen into three screens of vocabulary citations: the right data, in the wrong density and the wrong place. Single biggest opportunity: make At a glance an actual glance (one line per row, source detail behind one disclosure) so the zilganersen page's 2,165px section comes down to the ~480px the no-card page already shows.

## What's Working

- The digest: status in words, its meaning stated, the stage track as a position. Calm and believable.
- Phone folding: 9 sections collapse to 27–66px each with chips pinned.
- The no-card case: daraxonrasib's At a glance is 483px, 5 plain rows, no placeholder. That is the target size.

## Priority Issues

1. [P1] At a glance is not a glance. 2,165px at desktop, 3,116px on phone (3.8 screens), pushes The record in brief to screen 7. Why: the reader from a shared link wants "what happened?", and gets "what do these words mean?" first, in indexing prose that can sound wrong ("used as a probe" for an approved drug). Fix: each row one line (value + kind, e.g. "Zilganersen · oligonucleotide"), definition + credit + score in one per-row disclosure, closed by default; keep the section open. Command: /impeccable distill.
2. [P1] Match percentages in the navy band beside the status ("High match · 81%"). Why: the contract refuses scores and meters near the answer; "81%" reads as a grade of the treatment. The rule that every match shows its score is met in the glance row, framed as "Match to this claim". Fix: drop the notes from the band; spec 6a's band requirement changes with it. Command: /impeccable clarify.
3. [P2] Band facts repeat the H1 and add a ~250px, 4-cell grid above the fold on phone, with no link cue (no underline, no hover on touch). Fix: show only what the title does not (Kind, Gene/Acts on); add a visible cue; or drop the row below 40rem. Command: /impeccable layout.
4. [P2] Inconsistent "Kind": band uses the drug record's molecule kind, row uses MeSH's plural term; drug label shown in source caps ("ZILGANERSEN"). Fix: one source per label everywhere; show the drug record's name in the claim's case with the source label in the disclosure. Command: /impeccable clarify.
5. [P3] Attribution louder than content, and over-long measures. Credit lines are 2–4 underlined lines per card; the card note is 9 sentences at ~96 ch; the lede runs ~95 ch. Fix: credits in one small grey line linking only the source name; note cut to 2 sentences with a link to the method page; cap lede and notes at 66ch per DESIGN.md. Command: /impeccable typeset.

## Persona Red Flags

Jordan (first-timer): meets "Kind / Oligonucleotide / Matched by exact name" and "Gene named / GFAP / High match · 100%" in the band before knowing what the site is; reads a lab-probe definition for an approved drug; "Records of studies: 2 in people — Trials, and papers as Europe PMC files them" is jargon.

Sam (screen reader / keyboard): band facts are a nav named "At a glance", and the section heading is also "At a glance" — two landmarks/headings with one name; links read "Kind Oligonucleotide Matched by exact name" with no "jump to" cue; content facts inside a nav landmark. dt/dd inside the glance is correct.

Casey (phone): answer in the first screen (good); any scroll lands in 3+ screens of definitions; 7 links under 24px tall (date link, "How a status is set", NCT IDs); Follow appears in the band and again under the summary.

## Minor Observations

- At a glance has a fold chevron at desktop; folding it hides the band links' targets (folds.ts re-opens on hash, so it recovers).
- "also known as … antisense oligonucleotide (ASO) treatment targeting GFAP" is a description, not a name (breaks the project's own naming rule; data fix).
- MeSH title case under the claim's sentence case: same term twice, two cases.
- Digest repeats itself: "Approved by a regulator" then "A regulator has recorded an approval."
- Phone type scale is flat (step 1.13); h1 23px.

## Questions to Consider

- If the cards are "not about this claim's evidence", why do they come before the record in brief and take three times its space?
- What is the smallest unit of "a term, its source and its fit" that fits on one line?
- Is the band row navigation or decoration? If navigation, why do half its links point at words already in the headline?
