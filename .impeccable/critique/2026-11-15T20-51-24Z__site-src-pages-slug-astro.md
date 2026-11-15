---
target: claim page (At a glance, after fixes)
total_score: 23
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/site/src/pages/[slug].astro"
target_fingerprint: "sha256:cac6b928d6d71c38784434bbe900f4debecd10d5a0c26726b3543eb190f46caf"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/site/src/pages/[slug].astro
timestamp: 2026-11-15T20-51-24Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review · B: detector + browser overlay)

Target: claim page, site/src/pages/[slug].astro, after the critique fixes on PR 161 (one-line glance rows, closed disclosures, trimmed band). Pages: alexander-disease-zilganersen (4 cards), tourette-syndrome-wrist-nerve-stimulation (2 cards), alzheimers-nano-eraser (no cards). Desktop 1024/1280, phone 375. Export: 126 claims; 55 have no card, 35 one, 28 two, 7 three, 1 four.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Status in the first phone viewport; a band-fact link lands on a row with no :target highlight and focus stays on body. |
| 2 | Match system / real world | 2 | "High match · 100%" beside a drug name reads as efficacy; "Kind of molecule", "Gene named" unglossed; "also known as" introduces a description on Nano-ERASER. |
| 3 | User control and freedom | 3 | Folds, closed disclosures, in-page links clear the sticky nav. |
| 4 | Consistency and standards | 2 | Kind of treatment "Oligonucleotides" above Kind of molecule "Oligonucleotide" with two score vocabularies; two keys back to back in Recorded; dashed outline on the unchecked note (dashed belongs to promises). |
| 5 | Error prevention | 3 | Guardrail copy strong; bare percentage is the one misreading risk. |
| 6 | Recognition rather than recall | 3 | Chips with counts; four disclosure summaries share one accessible name. |
| 7 | Flexibility and efficiency | 2 | 9 chips scroll sideways on phone; no route from "2 registry records matched" to the glance. |
| 8 | Aesthetic and minimalist design | 2 | Three back-to-back intro notes; two Follow buttons; rows that restate the headline. |
| 9 | Error recovery | n/a | Read-only page, no input. |
| 10 | Help and documentation | 3 | Method links placed where needed. |
| **Total** | | **23/36** | **Acceptable (64%)** |

## Design Specificity Verdict

LLM assessment: authored for this product: the navy band with the white status card, stage track, amber for promises, the question-led record in brief. "At a glance" is the borrowed part: a stock label/value infobox with no shape of this product's own, and on most claims it restates the headline (Treatment, Claimed for). With 44% of claims having no card, the section usually adds four rows, two of them repeats.

Deterministic scan: impeccable detect on the page and 7 components: 0 findings (exit 0). Browser overlay at 1280: line-length on p.lede (~94 ch), p.glance-note (~89) and the footer data-sources p (~89) on all three pages; straggler on .take p.sentence at 1024 (URL alone on the last line); cramped-padding on .brief-group on the no-card page. Classification: th.year overflow is an artifact of the hidden pane (does not reproduce at 1280 or 375); cramped-padding is likely false (hidden details content); line-length is the documented 66ch measure, which in Figtree sets ~89–95 characters because ch is the wide "0" glyph — not a rule breach but a fair design question; the straggler is real and minor. Phone 375: no findings, no horizontal scroll (the record strip scrolls on purpose).

## Overall Impression

The previous critique's main problem is fixed: the glance is no longer three screens and its cards wait behind closed disclosures. What remains is duplication and placement: the band facts arrive after the actions and below the phone fold; the glance repeats the headline and shows two kinds for one drug; and the bare "High match · 100%" next to a drug name is still the one place a reader can mistake a term-fit score for an efficacy score. Biggest opportunity: decide what the glance is for when the headline already names the treatment and the condition.

## What's Working

- Status first: the white status card answers in words in the first phone viewport.
- Closed disclosures with the score in sight on the summary keep the box short; phone tap targets 47–50px.
- Contrast solid everywhere checked (7.5:1 grey on white, 10.7:1 and 15.4:1 on navy); no horizontal scroll at 375.

## Priority Issues

1. [P1] Band facts below the phone fold, after the actions. On phone the row sits at y=822–894 (viewport 812), under Follow/Share, reading as a footer strip; on Tourette it is one lone cell. Fix: move the facts to a quiet meta line under the headline (replacing the approach label beside the topic chip), above the status card on phone; or drop the band row when it would hold one fact. Command: /impeccable layout.
2. [P1] Duplication in the first two screens. Kind of treatment and Kind of molecule both shown for zilganersen; Treatment and Claimed for restate the headline on every claim; a second Follow under the lede. Fix: skip the kind row when a drug row exists; on a claim with no card, fold First reported / Evidence / Records of studies elsewhere or drop the term rows; keep one Follow. Command: /impeccable distill.
3. [P1] "High match · 100%" beside a drug name reads as efficacy. The closed summary has no noun for the number; the explanation sits in a 5-line note phone readers skip. Fix: word the summary "Term match: high, 100%" (the card inside already says "Match to this claim"). Command: /impeccable clarify.
4. [P2] Disclosure names and in-page landing. All summaries announce "Source and definition High match · 100%"; band links land on an unmarked, unfocusable row. Fix: visually hidden "for GFAP" in each summary; :target highlight on glance rows matching the record rows; tabindex=-1 on the row so focus follows. Command: /impeccable harden.
5. [P2] Summary wraps badly on phone. At 375px the chevron drops to its own line and "Matched by exact name" falls below the link. Fix: keep label and chevron in one nowrap group and let only the score wrap. Command: /impeccable adapt.

## Persona Red Flags

Jordan (first-timer): "Kind of molecule", "Gene named", "Oligonucleotide(s)" twice and "glial fibrillary acidic protein" with no plain gloss outside closed cards; "also known as" before a description; 9 chips with no reading order; three "not advice" notes before the record.

Sam (screen reader / keyboard): identical disclosure names; after a band link focus stays on body and the target row is not focusable; desktop summaries 34px tall.

Casey (phone): answer arrives fast, then a 810px stretch of lede repeat, second Follow and dashed note; glance starts at y=1705 (screen 3) and is 1206px; band links jump 900px down.

## Minor Observations

- Glance note is 5 lines at 375px in a semicolon legal register; could be one sentence and a link.
- "Records of studies: 2 in people" overlaps the "Trials on record 2" and "Papers on record 1" chips.
- The approach label "Drug" beside the topic chip on Nano-ERASER (a nanogel delivery system) shows the pipeline's approach code, not what the treatment is.
- 66ch in Figtree is ~90 characters a line; DESIGN.md's measure may want restating in characters.
- Straggler URL in the Pass it on sentence at 1024.
- The dark floating pill in captures is the Astro dev toolbar (dev only).

## Questions to Consider

- With 44% of claims cardless, does "At a glance" earn the first slot, or should term facts live in the band and the sheet open on the record in brief?
- Could "What is it?" be the first question of the record in brief, so there is one question-led summary instead of an infobox plus a Q&A list?
- Would one standing line under the status card ("Records, not advice. Scores rate how well a term fits, never the treatment.") let every later section start with content?
