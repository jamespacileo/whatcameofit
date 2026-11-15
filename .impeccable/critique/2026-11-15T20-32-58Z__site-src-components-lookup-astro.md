---
target: search results
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/visual-assets-logo-updates-a33ca9/site/src/components/Lookup.astro"
target_fingerprint: "sha256:900df03bfa928a789a3c0b0e0ad70a6509f1094e747d8a796e457e1445f58730"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/visual-assets-logo-updates-a33ca9/site/src/components/Lookup.astro
timestamp: 2026-11-15T20-32-58Z
slug: site-src-components-lookup-astro
---
Method: dual-agent (A: design review sub-agent · B: detector and browser sub-agent)

## Design Health Score
| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Note under box stays "15 match" after a topic pick shows 4 with a different best match |
| 2 | Match with the real world | 3 | "No record found" echoes the status "No trial record found" |
| 3 | User control and freedom | 2 | "Clear" and "Back to Latest" do the same thing; topic pick not in the address; no topic picks on a phone |
| 4 | Consistency and standards | 2 | Copied report row is unmarked; /about answer lacks report row and Clear; best-match headline not a link |
| 5 | Error prevention | 3 | Unknown trial ID has no way on |
| 6 | Recognition rather than recall | 3 | Count said three times |
| 7 | Flexibility and efficiency | 2 | No topic narrowing on a phone |
| 8 | Aesthetic and minimal design | 2 | Best-match unit ~1,700px on a phone |
| 9 | Error recovery | 2 | "We say that a lot."; no paste-a-link suggestion |
| 10 | Help and documentation | 3 | Rail stays beside results |
| Total | | 25/40 | Acceptable |

## Design Specificity Verdict
Parts are product-specific (status in words, Found in lines, no scores, trial-ID answer). Structure is generic search; the answer is assembled from the digest and a copied day-list row that carry their own notices. Detector: source 0; built HTML 106, mostly cramped-padding on list dividers; browser 5 on search (straggler, 2 line-length outside search, weak nested-cards on the dashed note, skipped-heading is a false positive while searching). Contrast all AA (lowest 5.71:1); mark fill vs panel ~1.2:1. Touch: 5/13 links under 44px; Clear 26px, Back to Latest 22px.

## Priority Issues
- [P1] Best match for "regrow teeth" is the baby-teeth pulp claim, not USAG-1, shown in the full digest. Fix: rank headline/report-title phrase matches above single-word trial-title hits; keep the full digest for exact matches only, "Closest match" row otherwise. /impeccable clarify
- [P1] Best-match block too heavy on a phone (Other matches ~1,700px down). Fix: one-line unchecked note, drop hover paragraph and counts from the copied row, jump link to other matches. /impeccable distill
- [P2] Answer differs by page; copied row unmarked; /about has no row, no Clear, no scroll. Fix: build the row from data with marks; one answer unit everywhere. /impeccable harden
- [P2] Duplicate and stale controls and counts; small tap targets; no phone topics; topic not in URL. Fix: one 44px control, update note on topic pick, &topic=, phone pill row. /impeccable layout, /impeccable adapt
- [P2] No-result and unknown-ID copy: "No record found", "We say that a lot.", no link out for an unknown ID. Fix: "Nothing tracked here matches …", paste-a-link first, registry link for unknown ID. /impeccable clarify

## Persona Red Flags
Casey: wrong best match then two screens of scroll; 15 unfiltered results; Latest list visible during Searching. Jordan: retracted best match in display type; Found in/No phase jargon. Sam: best headline not a link, others not headings; first See the records unnamed; stale live note. Journalist: note quotes lowercase typing; headline unmarked; no last-checked date in digest; no link for an untracked NCT ID.

## Minor Observations
Move "not a treatment option" under the record; align First reported dates; marks per word are noisy; balance stragglers; mark fill near panel; show registry state on trial answer.

## Questions to Consider
Digest only when the site knows? Does the day-list row belong in search? Count no-result searches in aggregate as backlog?
