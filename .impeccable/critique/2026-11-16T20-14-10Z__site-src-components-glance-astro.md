---
target: At a glance section
total_score: 23
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/at-glance-section-variants-e35890/site/src/components/Glance.astro"
target_fingerprint: "sha256:510397d6bf65a30e057f3008c26763ddc5a07d90a8bcc0999e4c8505af146e26"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/at-glance-section-variants-e35890/site/src/components/Glance.astro
timestamp: 2026-11-16T20-14-10Z
slug: site-src-components-glance-astro
---
Method: dual-agent (A: design review · B: detector + browser evidence)

## Design Health Score
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | Score and source in sight per row; clamped definition gives no cue the rest is in the card |
| 2 | Match System / Real World | 2 | MeSH capitals ("the LUNG", "BODY WEIGHT… FATS"), "Term match: from the drug's record", bare "Antibody" |
| 3 | User Control and Freedom | 3 | Native details, each row folds independently |
| 4 | Consistency and Standards | 2 | Same score named "Term match" in row, "Match to this claim" in card; source capitals in reasons |
| 5 | Error Prevention | 3 | Guardrails built into copy (no gene-to-treatment arrow, drug note) |
| 6 | Recognition Rather Than Recall | 3 | "Why this term" does not say what is inside |
| 7 | Flexibility and Efficiency | 2 | ~1,700px down on a phone; band links are the only shortcut |
| 8 | Aesthetic and Minimalist Design | 2 | Up to 7 elements per row; 60-word note; Treatment/Claimed for repeat the headline |
| 9 | Error Recovery | n/a | Static read-only section, no input |
| 10 | Help and Documentation | 3 | Method link, reasons on every card |
| **Total** | | **23/36** | **Good (64%: Acceptable band)** |

## Design Specificity Verdict
LLM: authored in voice, generic in form. Quoted, attributed definitions, "Lung cancer → Lung Neoplasms", "Term match" wording, Acts on vs Gene named are product-specific. The label/value list between rules could be any spec sheet.
Deterministic: CLI scan of Glance.astro + TermCard.astro clean (0). URL scan and overlay: 3 line-length warnings per page; one inside the section (p.glance-note, ~89 chars/line); others outside (page lede, details). Contrast all AA+ (grey 7.49:1); summaries 47px on phone; no horizontal overflow.

## Priority Issues
- [P1] One score, two names: row "Term match: high, 98%", card "Match to this claim: high, 98%". Fix: one phrase in both. → clarify
- [P1] Source text shown unclean: MeSH capitals in quoted definitions, "growth. ." double stop in MSTN, "APITEGROMAB" in reasons. Fix: display-only normalisation disclosed in the credit, or keep words verbatim and set cross-reference capitals as small caps; drug name through drugName(). → clarify / typeset
- [P2] Kind of molecule row says "From Open Targets Platform" while its credit says ChEMBL supplied the kind. Fix: name facts_source when present. → clarify
- [P2] Clamp has no cue, and a long definition is read twice by a screen reader. Fix: "Full definition" in summary when clamped; aria-hidden on one copy. → harden
- [P2] Summary line dense (3–4 parts + link), wraps to 2–3 lines on a phone; glance-note ~89 chars/line. Fix: drop source from summary on phone or move "Why this term" first; tighten note measure. → distill / layout

## Persona Red Flags
Jordan: "Antibody" unexplained; "by exact name", "from the drug's record" opaque; "Lung Neoplasms" no lay gloss; skips 60-word note.
Sam: summary accessible name ~25 words; CSS dots spoken or not by reader; long definition announced twice; row reached from band has tint only.
Casey: section two screens down; "Evidence when first reported" and "15 trial records · 7 papers" wrap in two-column facts; open card adds ~320px.

## Minor Observations
- Chip bar covers section heading after scrollIntoView on desktop (scroll-margin).
- Treatment card nearly empty once row shows definition.
- Date link 21px tall, method link 17px at desktop.

## Questions to Consider
- Should term definitions sit after the record in brief, as reference?
- One "What these words mean" disclosure for the section instead of one per row?
- Is a 100% term match on an identical name worth the reader's attention?
