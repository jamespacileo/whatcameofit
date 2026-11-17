---
target: claim pages vs examine.com
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro"
target_fingerprint: "sha256:671a9978cd5580bb1dc54bc563c9200cef02d829d765cbf998da99d620f57d26"
target_path: /Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro
timestamp: 2026-11-17T08-06-55Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review sub-agent · B: detector + browser evidence sub-agent)

Target: claim page `site/src/pages/[slug].astro`, origin/main at 3a34d6f. Reference: examine.com (creatine, eczema pages). Sample: `/dupilumab-atopic-dermatitis` (dense, Phase 3) and one sparse claim. Not checked: print, real screen-reader output.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Last-checked dates and section counts good; `Pop` triggers lack initial `aria-expanded` |
| 2 | Match system / real world | 3 | Plain questions strong; registry prose leaks into cells; chips like "Term match: From the drug's record" |
| 3 | User control and freedom | 3 | Folds, filters, popovers work; no expand-all / collapse-all |
| 4 | Consistency and standards | 2 | 3 table classes + 1 ARIA div grid + 4 list-row classes + 3 dl classes; 6 disclosure mechanisms; 4 column-label treatments |
| 5 | Error prevention | 3 | 146 near-identical registry links at 49px pitch invite mis-taps |
| 6 | Recognition rather than recall | 2 | Trial header and timeline legend scroll away across 4,524px and 9,653px sections |
| 7 | Flexibility and efficiency | 2 | No year jump, no trial sort; "Pass it on" folded at ~17,600px |
| 8 | Aesthetic and minimalist design | 2 | 147-row timeline open by default, repeats the trials; 18 visible font sizes |
| 9 | Error recovery | 3 | Empty states worded well |
| 10 | Help and documentation | 4 | "How a status is set", "What a phase is" sit where needed |
| **Total** | | **27/40** | **Acceptable (top of band)** |

## Design Specificity Verdict

**LLM assessment.** Content model and wording are authored for this product ("The record in brief", promise beside record, dated provenance). Visual layer is category-standard by contract. First viewport is already structurally examine (three-tone band, card at right) since `band-tones` (2026-11-16). Below the hero, a dense claim reads as a registry dump, not a digest: 18,413px, 3,868 visible words, 446 tab stops. Sparse claims (38.5% of 966) are 4,171px and work.

**Deterministic scan.** CLI: 0 findings on `[slug].astro` and 50 components, but .astro files get regex rules only, so that is an undercount, not a clean bill. In-page detector (1280px, light): 3 findings on the dense page. `nested-cards` on `.digest` is a false positive (band is not a card). `line-length` on the lede is real (~94 chars per line). Footer line-length is site chrome. Sparse page adds `cramped-padding` on `.brief-group`.

**Measured.** Contrast: all 1,372 visible text elements pass 4.5:1 in light, 857 in dark. No horizontal overflow at 375px. Touch targets under 44px at mobile: 151 (133 inline links); fold buttons 27px, score chips 25px, trial toggles 24px. 204 popovers, 958 links, 282 buttons in `main`.

**Visual overlay.** Injection succeeded; overlay with 3 outlined findings is in the "[Human] dupilumab…" browser tab (computed at 1280px).

## Overall Impression

The answer lands in two seconds, then the page stops editing itself. Examine feels calm because it has one table, one disclosure, one key-value pattern and collapsed-by-default answers. This page has the right content and about a dozen dialects for showing it. Biggest opportunity: six primitives and stricter open/closed defaults, not a component library.

## What's Working

1. **The digest.** Status in words, non-filled stage track with "Place 5 of 6" as text, "why" popover. Honours no-verdict and not-by-colour rules.
2. **"The record in brief"** (`RecordBrief.astro:21-35`). Question, answer, expandable provenance, 50px rows. Closest thing to examine on the page; model for the rest.
3. **Score chip mechanism.** `Pop.astro` already uses the native Popover API: number visible, panel on tap or key, printed in place. The pattern asked for exists; its content and formats are the problem.

## Priority Issues

**[P1] Pattern fragmentation.** Record data is carried by `table.timetable`, `table.index`, `table.result-table`, an ARIA div grid (`.trial-table`), four list-row classes (`.entries`, `.paper-list`, `.record-list`, `.match-list`) and three `dl` classes. Six disclosure mechanisms (FoldHead button, native `details` in 7 places, trial-row button, `Pop`, `data-clamp`, kind tabs). `global.css` is 7,567 lines in one file; `.digest` has 70 rule hits spread from line 563 to 7431. Why: this is the cohesion break, and every change is a patch. Fix: six Astro primitives (DataTable with optional group row and expandable row, KeyValue, RecordRow, Disclosure, ScoreChip, Legend) and split CSS per primitive. Command: `/impeccable shape`.

**[P1] Timeline swamps dense claims.** "Recorded" renders all 147 records open (`[slug].astro:653-860`): 9,653px, 52% of the desktop page, 67% on phone, and it repeats the 47 trials listed next. Fix: strip plus latest year open, the rest behind "The other N of 147 records" (pattern already at `[slug].astro:935`), or year group rows with counts. Apply above ~20 records. Command: `/impeccable distill`.

**[P1] Hero reads as two blocks.** Band tones `#0B2545` / `#12325E` / `#1C4179` differ by only 1.2–1.5:1, and the status card sits outside the main-column surface (panel ends x≈867, card 874–1231). h1 28.9px vs status label 29.75px compete. Fix: one `--band-main` surface under both columns; status card as a recessed or raised tone inside it (examine: mid band, darker recessed card); widen the tone step; give h1 clear size lead. Command: `/impeccable colorize`.

**[P2] Rows carry prose; chips carry five formats.** Papers run 5–7 lines × 88 rows (`Paper.astro:42`); organisations repeat one sentence per row (`Organisations.astro:42`); "Main measure" cells hold registry prose; glance rows carry up to 6 parts. Score chips: "Term match: High, 100%", "Match to this claim: High, 98%", "Possible match: Medium, 79%", "Very likely in the report · 100%", "Drug record: By exact name". All 47 trial-score popovers share one generic sentence; no per-record reason is in the DOM (`Trial.astro` has none), which sits badly with the rule that every match carries its score and reasons. Fix: one thing per cell, prose into the expanded row; chip = percentage in tabular figures (low band keeps word + dashed outline), subject and reasons in the popover; non-numeric provenance as muted text, not a chip. Command: `/impeccable distill`.

**[P2] Type scale sprawl.** 18 visible font sizes in `main`, seven within 1.5px of each other (13.26–14.96px); ~40% of text nodes bold; 33 distinct `font-size` declarations, raw `0.9rem` ×34 and `0.85rem` ×25 while `--label-size`/`--note-size` are used 5 times each. Fix: 5-step token scale, raw sizes banned. Command: `/impeccable typeset`.

## Operator's Notes

1. **Tinted top section.** Agree, and it is half built (`band-tones`). Examine's band is mid-purple on a pale page with a darker recessed card, and a 60px title over 16px body. Ours is near-black navy with steps too small to read as tone. Widen the steps; keep navy (decided 2026-11-12, never NHS blue).
2. **Phase 3 card on shared tint.** Agree. One surface under headline and status, card as a tone inside it, 1px rule between. On phone, status before "Kind of molecule / Acts on".
3. **Collapse paragraphs.** Lede and section notes already clamp. Still open and worth folding into an info popover beside the heading: glance lead (`Glance.astro:80`), brief intro, statements intro (~55 words), Follow explainer, per-row repeated notes. Must stay open: status, gloss, lede, one-line "not yet checked by a person", "not counted in the status", every score number.
4. **Reusable components.** Confirmed by measurement; see P1.
5. **Examine table style.** Works through: one filled header row, fixed column widths, one thing per cell (≤3 words or glyph + caption), tinted group rows with counts and a collapse control, two type sizes total. Translates without grades: filled header, group rows per phase or year with counts, people as right-aligned tabular number, state as word + existing `KindIcon`, results as date or "None posted". No coloured cells, no effect arrows.
6. **At a glance.** Already two columns from 60rem (`global.css:7471`); lower to 40rem. Reduce each row to label, value, chip; definition inside the disclosure. Source as a muted tag on the label line ("MeSH", "ChEMBL"), always visible: ChEMBL facts are CC BY-SA (ADR 0002), so hover-only attribution is not safe.
7. **Scores.** Mechanism exists; standardise format and fix content (P2). Add initial `aria-expanded="false"`, raise hit area from 25px.
8. **shadcn / library.** Do not adopt. shadcn needs React and Tailwind; the site has neither. Astro-side lookalikes (Basecoat, starwind, fulldev/ui) still assume Tailwind (from memory, current docs not checked) and would fight 7.5k lines of token CSS, the print rules and the zero-framework rule. The site already uses the right platform pieces (`details`, Popover API with anchor positioning). Borrow shadcn's vocabulary and API shape (Table, Collapsible, Popover, Badge) for own primitives.

## Persona Red Flags

- **Jordan (first-timer):** "Drug record: By exact name", "Place 5 of 6", the basis diamond and "Read as this treatment for this condition" are unexplained at first sight. Dashed "not yet checked by a person" box right under the answer undercuts it. Two "Follow" buttons 300px apart.
- **Casey (mobile):** masthead 128px + hero 766px puts the summary on screen two. "At a glance" 1,293px. ~13 screens of timeline before trials. Section pills truncate. Chips 25px, row toggles 24px.
- **Sam (keyboard / screen reader):** 446 tab stops. 146 timeline buttons named only "Trial registered" / "Trial completed", no NCT id. Trials are 7 separate `role="table"` grids.
- **Journalist re-checking a story:** the trial that sets the status is not singled out; first trial row is a 433-person Phase 4, not the 2,733-person Phase 3. Copy and embed tools folded at the very bottom. No "since your story of 1 Oct 2016" summary.

## Minor Observations

- Two legends stacked in "Recorded" (`[slug].astro:660-665`).
- `.brief-group` uses `--ring` for its rule where everything else uses `--rule` / `--row-rule`.
- Chip border `#D9E2EE` on white is 1.31:1; chips barely read as controls.
- DOM order puts "The news report this page follows" before "Where it stands"; visual order is the reverse at desktop.
- Dark scheme: outlet favicon tiles keep a white background.
- Page ends on folded utilities; no closing restatement of status and date.

## Questions to Consider

1. Timeline and trials table show the same 47 records twice. If one had to go, which?
2. If the dense page were capped at 600 visible words, which 600, and why is that not the default?
3. Is a score without a per-record reason still "shown with its reasons"?
