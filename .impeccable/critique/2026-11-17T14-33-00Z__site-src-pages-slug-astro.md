---
target: claim page
total_score: 23
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/worktrees/thenwhat/claude-sections-rebuild/site/src/pages/[slug].astro"
target_fingerprint: "sha256:b0d8f8d4df3977891bb9bec36c93bde9d609f15b5f53b401d293a8ac4840ac1e"
target_path: /Users/jay/Projects/worktrees/thenwhat/claude-sections-rebuild/site/src/pages/[slug].astro
timestamp: 2026-11-17T14-33-00Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: critique-a-design · B: critique-b-detector)

# Critique: claim page

Target: `site/src/pages/[slug].astro` on `claude/sections-rebuild` (commit 6e38e726). Looked at fenebrutinib-multiple-sclerosis (small), aducanumab-alzheimers-disease (middle), dupilumab-atopic-dermatitis (large); 1400 / 1000 / 375px; light and dark. The top findings were re-checked in source and browser by the parent session.

## Design health score

| # | Heuristic | Score | Key issue |
|---|-----------|-------|-----------|
| 1 | Visibility of system status | 3 | Current section, counts on folded heads, last-checked dates all present |
| 2 | Match system / real world | 2 | "Low confidence · 95%", "Place 5 of 6", "Keep or pass on", nav count "1 and 13" |
| 3 | User control and freedom | 3 | Esc closes panels and returns focus; no open-all / close-all |
| 4 | Consistency and standards | 2 | Key says "Halted", rows say "Stopped early"; paper titles clipped on desktop, wrapped on phone |
| 5 | Error prevention | 2 | The status card invites the misreading that caveats lower down try to prevent |
| 6 | Recognition rather than recall | 3 | Five separate keys, about 20 marks; outlets are icon-only in statement rows |
| 7 | Flexibility and efficiency | 2 | 47 trials and 88 papers with no filter or sort |
| 8 | Aesthetic and minimalist design | 3 | Calm; the brief says six facts twice; hero actions repeat in "Keep or pass on" |
| 9 | Error recovery | n/a | Read-only page, no error state to meet |
| 10 | Help and documentation | 3 | Info marks, "How a status is set", inline glosses; nothing says which sources are not checked |
| **Total** | | **23/36 (64%)** | **Acceptable** |

## Design specificity verdict

**Review**: The sheet is authored for this product. "The record in brief" asks six lay questions, registry terms carry plain glosses, promises sit on amber, and every match shows its score with what the score is of. The generic part is the frame: a navy band, a side list and folding sections. The least specific element is the one that should be most specific: the status card reads the same on all three claims.

**Deterministic scan**: the source scan was clean (0 findings). In the browser, 3 findings per page on all three claims:
- line-length ×2: true. The brief's sentence (`p.brief-said`) runs about 91 to 96 characters a line (782px at 18px); the "Data sources" paragraph about 91.
- nested-cards ×1 on `.digest`: false positive. The inner "card" is the tab label "Where it stands" (`.card-tab`).

## Overall impression

Below the band the page reads as one system and is calm. The biggest gap is above it: the answer most readers leave with ("Phase 3 trial, place 5 of 6") is the same for a drug under way, a drug with five trials stopped early, and a drug with 24 Phase 4 trials.

## What's working

1. The record in brief: questions a relative would ask, a counted answer, one press to what it means and where it is from; "This does not say a trial is open to new participants" puts the no-advice rule where it is needed.
2. Confidence at the point of use: "High, 89%. Read as a study of this treatment for this condition", and the panel adds that it says nothing about whether the treatment works.
3. Folding by width: on a phone six sections start folded with a count line each. The focus ring is a visible 3px; a skip link is the first stop.

## Priority issues

### [P1] The status card gives one answer to three different stories
- Why: most readers stop at the card. On aducanumab the reader holds "Phase 3 trial", then finds five "Stopped early" marks far down with no sentence joining them; the same claim lists a report "US approves first new Alzheimer's drug…" beside "Approved by a regulator? None on record". Dupilumab shows 24 Phase 4 trials under a "Phase 3" status.
- Fix: one record sentence on the card from counts already on the page ("5 of 9 trials stopped early; none under way"). Word the approval row by source ("No approval in the registries this site reads"). Give Phase 4 a note.
- Limit: the status is set by pipeline rules; the site can add counts and wording, not change the status. Regulator data is pipeline work.
- Where: the hero card and stage track in `[slug].astro`; the approval row in `RecordBrief.astro` / `lib/record-brief.ts`.
- Command: /impeccable clarify

### [P1] "Low confidence · 95%" sits one section above "High, 89%"
- Why: 95% reads as high; the chip undermines every other score.
- Fix: name the band, not an adjective that fights the number ("Not confirmed · read at 95%").
- Limit: "low confidence" is the wording of ADR 0004; the operator decides.
- Where: `site/src/lib/confidence.ts` `stageReading`.
- Command: /impeccable clarify

### [P2] An opened fact row slices its own label
- Confirmed at 1400px on aducanumab: "Compared with a placebo?" wraps to two lines, the opened panel (`.fact-sheet .fact-more`, grid column 1 / -1) starts 9px above the label's bottom.
- Fix: start the panel under the taller of label and value.
- Command: /impeccable polish

### [P2] Paper titles are clipped to one line and readable nowhere
- `.paper-rows .paper-name` is `white-space: nowrap` with an ellipsis from 52rem; a 196-character title shows about a fifth, has no title attribute and is not repeated in the opened row. The phone wraps it.
- Fix: wrap to two or three lines on desktop.
- Command: /impeccable layout

### [P2] Marks and terms drift across sections
- The trials key says "Halted" (`[slug].astro` near line 1128); rows and the timetable say "Stopped early". Five keys carry about 20 marks. The trials key lists states the claim does not have.
- Fix: one word per state everywhere; a key shows only the states present.
- Command: /impeccable distill

## Persona red flags

- Relative of a patient, on a phone: aducanumab shows "Phase 3 trial, place 5 of 6"; "Trials on record" starts folded, so "Stopped early" is two taps and a scroll away.
- Jordan (first-timer): "Place 5 of 6", "Possible registry records", "Ringed: results posted", unlabelled share bars and "Keep or pass on" need translating.
- Casey (phone): section chips are 34px tall, score chips 25px. The brief costs over a screen to say six facts twice.
- Sam (keyboard, screen reader): dupilumab has 406 buttons and 1,044 links with no way past the trials table; 36 buttons on aducanumab share one name.

## Minor observations

- The brief's sentence and "Data sources" run about 91 characters a line; the page's measure is 66.
- The H1 is one report's headline, larger than the status, with only a small line under it saying so.
- "Keep or pass on" opened shows about 12 controls.
- "Check again later" appears twice in the band.
- The by-year timetable sits behind a small blue link.
- Aducanumab counts a trial where it is only the comparator among its 9 trials.
- 0.12s colour transitions on nav links and chevrons make a theme switch take more than one frame.

## Questions to consider

1. If three claims with opposite fates all read "Phase 3 trial", is that label an answer or an index key?
2. Should the page's largest words be what a newspaper said, or the claim and what is on record?
3. Would "promise beside record" be truer with the timetable open and the six-fact table folded?

Not checked: a real screen reader, a real touch device, print, no-script, 200% zoom, reduced motion, a claim with little on record.
