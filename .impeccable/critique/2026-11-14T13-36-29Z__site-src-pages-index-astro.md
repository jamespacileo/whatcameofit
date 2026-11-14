---
target: "landing pages after return-to-home: conversion, churn, network effects, return visits"
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/clinical-trials-research-strategy-da25a5/site/src/pages/index.astro"
target_fingerprint: "sha256:84f82c4dc4f2229471bd20777345e6d6c4d30c60a3821e3eb44809af559a0c52"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/clinical-trials-research-strategy-da25a5/site/src/pages/index.astro
timestamp: 2026-11-14T13-36-29Z
slug: site-src-pages-index-astro
---
Method: dual-agent (A: design review · B: detector + browser evidence), live site whatcameofit.com after the return-to-home release, 1280x800 and 375x812. Neither reviewer saw the earlier run.
Lens: conversion, churn, network effects, return visits to the home page.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|-----------|-------|-----------|
| 1 | Visibility of system status | 2 | Pressing Follow shows a sighted reader only a label change; the sentence that says what happened is in a visually hidden status element. A since-line count does nothing visible when its list is already open |
| 2 | Match system / real world | 3 | "For a feed reader", "Narrow these lists"; no word "Home" though copy says "listed on the home page" |
| 3 | User control and freedom | 3 | "Stop following" is immediate with no undo |
| 4 | Consistency and standards | 2 | "1 status change" in the since line above a tab reading "Status changes 38"; "40 news reports" against "Headlines 104" |
| 5 | Error prevention | 3 | Any home load advances the last-visit day, so a glance uses up the window |
| 6 | Recognition rather than recall | 2 | Follow is explained only at the foot of the claim page; home never says following exists until it has been done |
| 7 | Flexibility and efficiency | 3 | Lookup, address state, feeds, embed all exist; none surfaced for a repeat reader on home |
| 8 | Aesthetic and minimalist | 3 | Calm; on a phone five thin meta lines stack before any content |
| 9 | Error recovery | 3 | Well worded from source; not all paths exercised |
| 10 | Help and documentation | 1 | How it works says nothing about following, reminders, feeds, embed or suggesting; names the extension with no way to get it |
| **Total** | | **25/40** | **Acceptable** |

## Design Specificity Verdict

LLM assessment: grounded. Quoted headline beside status, amber for promised only, the six-place track, "Was: X. Now: Y.", "Kept in this browser only." The return mechanics are honest and specific in wording but are visually the quietest things on every page.

Deterministic scan: 0 findings across home, claim, topic, layout and components.

Visual overlays: none. The browser pane blocked the detector script (localhost from an https page).

## Overall Impression

The machinery to bring a reader back now exists and works: the since line counted 14 reports from a stored visit, a followed claim showed "Changed. Was: Preclinical only. Now: Phase 3 trial." first in the list and cleared after opening. What is missing is the invitation. A first-time reader is never told the page will differ next time or that following exists, and the Follow pill is one unexplained word above the answer. Biggest opportunity: explain and confirm Follow at the moment of the answer, and give home an empty "Following" state that says what it is for.

## What's Working

- Returning-reader mechanics are correct: same-day reload keeps the earlier date, changed claims sort first, the note clears on viewing, every word is honest about where data lives.
- "Check again later" inside the status panel puts the return question beside the answer.
- Measured gains since the last run: all four tabs inside a 375 px viewport; home touch targets under 44 px down from 23 to 10 (8 of them links in a sentence); no contrast failure anywhere (pager Previous 2.86 to 7.49); hashed assets cached a year; no console errors; back from a claim restores tab, page and status.

## Priority Issues

**[P1] Follow is unexplained, unconfirmed and offered before the answer.**
Why: it is the only thing that ties a claim-page visitor to the home page, and most visitors land on a claim page. The explanation sits about seven phone screens below the button; the confirmation sentence is hidden from sighted readers. A first-timer may assume it wants an account.
Fix: a second Follow control in or under the status panel beside "Check again later", with the sentence visible: "Listed on the home page, with a note when the status changes. Kept in this browser only." Show the confirmation in view with a link to the list. A real button in the bottom section instead of "at the top of this page".
Command: /impeccable onboard

**[P1] Home never tells a first-time reader it will differ next time, or that following exists.**
Why: churn. "In the last 30 days: 40 news reports, 1 status change." reads as a statistic. The Following block appears only after someone has followed.
Fix: an empty Following state ("Follow a claim from its page and it is listed here, with a note when its status changes. Kept in this browser only."). One sentence after the since line on a first visit. Name the feed plainly near it.
Command: /impeccable onboard

**[P2] Phone: no headline on the first screen.**
Why: first row at 989 px on an 812 px screen, 16 controls before it; 1262 px with a status in the address. The band (585 px with the masthead) is the operator's choice, so 404 px of tally, pill, since line, two rows of tabs and a heading must shrink by about 180.
Fix: fold tally and since line into one line; put "Narrow these lists" under the tabs; tabs in one row or a compact switcher. Desktop is unchanged from before: 23 controls and 961 px before the first headline, 1169 px with a followed claim.
Command: /impeccable adapt

**[P2] The since line's counts conflict with the tab counts, and its controls can do nothing.**
Why: "1 status change" above "Status changes 38" forces the reader to reconcile two systems; pressing "40 news reports" on the open Headlines tab has no visible effect; a zero is dropped, so the reader is never told "no status changes". The since line also ignores changes to followed claims.
Fix: make a since count filter its list to rows dated since, with "Show all"; always state the zero; label tab totals as totals or drop the pills.
Command: /impeccable clarify

**[P2] Topic and method pages are dead ends; embed and extension have no doorway.**
Why: topic page ends on Share and a feed line at 76–83% depth, nothing on the first screen, no lookup, no suggest. How it works does not mention following, reminders, feeds or the embed. "Show this status on another site" is a closed fold with no reason given.
Fix: end the topic page as the claim page ends; mark rows dated since the last visit there too; a short "Ways to keep up" section on How it works; one line of reason on the embed fold.
Command: /impeccable onboard

## Persona Red Flags

Jordan (first-timer): reads the status counts as a scoreboard with no hint the dots are buttons. Meets "Narrow these lists" before seeing a list. Sees "Follow" and expects an account. May read "High match · 99%" as a score for the treatment.

Casey (one-handed, interrupted): Follow is in the top row, out of thumb reach, with no second one lower. "Stop following" 21 px, since-line counts 26 px, "18 topics" 20 px. Headline and outlet links still touch (0 px) in every row. Nothing marks their place on a 6,400 px claim page.

Priya (relative's condition, two-year-old headline): home leads with this week's headlines; year chips that would help are near the bottom. The "not yet checked by a person" notice arrives straight after the status with no line on how far to rely on it. The only durable change notice offered is a calendar file or "a feed reader".

## Minor Observations

- A "Changed" claim opened from home shows no trace of the change on the claim page: the payoff is not confirmed where the reader lands.
- Pager "Previous" on a first page still takes focus (aria-disabled).
- Follow pill border is about 1.2:1 against white; state is carried by fill and wording.
- Claim page: nine timetable source links at 39 px, three NCT links at 26 px, "Post it to a network" summary 24 px.
- Two pager navs share the label "Pages of claims".
- "Suggest a headline (opens your mail)" is the highest-effort action and is the page's last.
- Search results in the band push the lists down about 170 px on desktop.
- With one followed claim the since line leaves the first desktop screen.

## Questions to Consider

- If the weekly change is new headlines and the product's point is what happens after them, should the first list be status changes and promised dates reached?
- Should a followed reader's home be their own list, with the lookup above it?
- Would one visible sentence, "Nothing has changed on record since your last visit", do more for trust and return than any count?

Not checked: native share sheet, clipboard, the saved calendar file, pasting an article link, no-JavaScript path, print, screen reader, a real phone, Following at phone width, the "Since your last visit" wording in the measuring pass (seen in the design pass only).
