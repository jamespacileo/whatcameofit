---
target: "landing pages: conversion, churn, network effects, return visits"
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/clinical-trials-research-strategy-da25a5/site/src/pages/index.astro"
target_fingerprint: "sha256:5c424c527e2363a9efa21908352dc0f33e11c941ede8dd77a30eb51c18f150ef"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/clinical-trials-research-strategy-da25a5/site/src/pages/index.astro
timestamp: 2026-11-14T12-41-24Z
slug: site-src-pages-index-astro
---
Method: dual-agent (A: design review · B: detector + browser evidence), live site whatcameofit.com, 1024x768 and 375x812.
Lens asked for: conversion, churn, network effects, return visits to the home page.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|-----------|-------|-----------|
| 1 | Visibility of system status | 3 | Filter state said in words and in the address; "Registries last checked" only in the footer |
| 2 | Match system / real world | 3 | "It happened", "Look up" (for home) and "No signal" need learning |
| 3 | User control and freedom | 3 | Every view is in the address and survives Back; no way to keep a claim |
| 4 | Consistency and standards | 3 | Headlines tab links the headline, the other three link the intervention name |
| 5 | Error prevention | 3 | Little to get wrong |
| 6 | Recognition rather than recall | 2 | A returning reader must remember which claims they cared about and that feeds exist |
| 7 | Flexibility and efficiency | 2 | No shortcut for a returner: no kept list, no "new since", no topic feed |
| 8 | Aesthetic and minimalist | 3 | Calm, but four control rows precede the first headline; "Pass it on" holds 15 controls |
| 9 | Error recovery | 3 | No-result state offers topics and suggest, no reminder; "We say that a lot." misjudges the reader |
| 10 | Help and documentation | 2 | How it works is footer-only; extension has no install link anywhere |
| **Total** | | **27/40** | **Acceptable (top of band)** |

## Design Specificity Verdict

LLM assessment: grounded. Stage track as summary, legend and filter; amber for "promised"; quoted headline beside status now; "Was: X"; the dated share sentence. None transfer to another product. The generic part is the retention layer: ten equal social pills, a folded embed, a feed link in a closing line.

Deterministic scan: 0 findings across home, claim page, topic page, layout and components (exit 0).

Visual overlays: none. Injection of the detector script was blocked by the browser pane (ERR_BLOCKED_BY_CLIENT, localhost from an https origin). Not the site's CSP; the site sends none.

## Overall Impression

The site answers a question well and then lets the reader go. Everything that would bring someone back is either at 77–92% of a claim page's depth, in `<head>` only, or absent. The home page changes slowly and cannot say what changed. Biggest opportunity: make the home page the place a returning reader sees what moved since they last looked, for the claims they kept.

## What's Working

- Status strip: one control that is scoreboard, legend and filter, with state in words and in the address.
- State survives: tab, page, status and topic are in the address; Back from a claim restores the same rows.
- Share sentence carries its own date, and the calendar reminder offers the claim's own promised date: a return mechanism that collects nothing.
- Fast and clean: 77 KB first load, 6 requests, no third parties, no console errors from the site, contrast passes everywhere but one disabled button.

## Priority Issues

**[P1] Home gives no reason to return and cannot show what changed.**
Why: default list is new headlines, which readers already saw elsewhere, mostly "Preclinical only". What only this site has (status changes, promises against outcomes) sits behind tabs 2–4. Status changes arrive one or two a month. No "new" mark, no summary, nothing remembered. "Next anniversary: 5 December" is static for three weeks. A promise falls due in seven weeks and nothing says so.
Fix: a "What changed" line above the tabs, computed in the browser from dated rows already in the page ("Last 30 days: 21 new reports, 1 status change, 1 promised date reached"). With a last-visit date kept in the browser it becomes "Since 7 Nov" and newer rows carry a "New" text tag. Move "Registries last checked" into the tally line. Consider Status changes as the lead tab.
Command: /impeccable shape

**[P1] Return mechanisms are buried on the claim page and missing from home and topic pages.**
Why: most visitors land on a claim page. Reminder sits at 88–90% of page depth (5559 px on a phone, about seven screens), feeds at 89–92%, share tools at 77–82%. Home has no visible feed link (head only), no reminder, no follow, no extension link. Topic pages have none of it. "Follow" exists only in an extension the site never links.
Fix: "Check again later" control inside the digest panel beside "Latest record". "Keep on my home page": a browser-only list shown at the top of home with "Was: X. Now: Y." Visible feed link on home; per-topic feed and reminder on topic pages. Email alerts are the conventional fix and are ruled out until Phase 2.
Command: /impeccable shape, then /impeccable layout

**[P2] On a phone, 1.3 screens and 16–23 controls precede the first headline; two tabs are clipped.**
Why: first headline row starts at 1070 px on an 812 px screen. Strip is cut by the fold. Tab row is 569 px in a 341 px box: "Promises" shows as "Pr", "No signal" is off-screen, with no hint beyond the cut-off. 23 touch targets under 44 px on home.
Fix: below 40rem fold strip and topic select into one "Narrow these lists" disclosure, or place them under the tabs. Wrap tabs 2x2. Move the suggest line to the no-result state and footer.
Command: /impeccable adapt

**[P2] Network loops leak.**
Why: ten equal platform pills dilute the one action that spreads the site. Embed is folded away. "Suggest a headline" is a mailto with no confirmation, and is the only way a reader improves the product. A reader arriving from a shared card has no second question prompted. No "cite this record" line for journalists. Topic pages cannot be shared.
Fix: end the claim page with a small lookup box ("Another headline?") in place of the feed-reader line. Cut "Post it" to device share, Copy link and a "More" fold. Add Share to topic pages. Add a cite line (address plus checked date).
Command: /impeccable distill

**[P2] On a phone the caveat precedes the answer on a claim page.**
Why: "This page has not yet been checked by a person…" comes before the status, which lands at 715 of 812 px. Trust drops before the answer is read; a reader who does not trust it does not share it. Breaks DESIGN.md's own "answer first".
Fix: keep the notice visible, inside or directly under the digest panel.
Command: /impeccable layout

## Persona Red Flags

Jordan (first-timer): placeholder "https://… or tooth regrowth" does two jobs. "It happened", "No signal", "Promises" unexplained. Strip reads as a progress bar before any claim is seen. No link to How it works above the footer.

Casey (one-handed, interrupted): no claim can be kept, so an interrupted visit is lost. Reminder is seven screens down. Two tabs off-screen. Headline and outlet links touch (0 px gap) in every row.

Priya (relative's condition, headline from two years ago): 58 of 84 claims are from 2026, none from 2022–2025, so hers is probably not tracked. She gets "No record found … We say that a lot." then a mailto. Topic page gives no way to hear of a new claim or a change. "Should I check again?" is answered only per claim, at the bottom.

## Minor Observations

- Pager "Previous" on page 1: 2.86:1 contrast, still focusable, looks active.
- View-transition promise rejection uncaught on rapid strip clicks (StageFilter.astro).
- Strip button pressed state looked out of step with aria-pressed under scripted clicks in a throttled pane; needs a direct check on a real device.
- All assets, including hashed files, send max-age=0; repeat views revalidate.
- No twitter:title / description / image tags (og covers most readers).
- Per-claim feed is linked in the body, not in head.
- Topic page has an H1 and no H2.
- Each list row costs two tab stops; 20 stops from tab to pager.
- "Next anniversary" spends a home section on a date three weeks off.

## Questions to Consider

- If status changes and promises falling due are the only things unique to this site, why is the default list the headlines the reader already saw?
- Should the site keep a reader's claims in their own browser, as the extension does, so home becomes "my claims" on the second visit?
- Is the reminder, not the share, the real conversion, given "we will check again" is the brand's one promise?

Not checked: pasting an article link and the live registry search, the downloaded calendar file, the native share sheet, a real phone, a screen reader, widths above 1024.
