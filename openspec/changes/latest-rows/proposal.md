# Proposal

## Why

On 2026-11-16 the operator asked for the rows of the home page's Latest list, and of search results, to be simpler to skim: less in sight, more said by position and shape, detail opened on demand. Four variants were mocked (`.impeccable/mocks/latest-rows/index.html`), critiqued (`.impeccable/critique/`), and a second round (`round-2.html`) chosen. The operator's picks: the status in words with a neutral position mark, one colour for every status, the headline on the left with the status in a fixed column on the right, and all five critique issues fixed.

## What Changes

- A report row leads with the outlet, date and topic, then the quoted title and the claim's intervention and indication. Where the claim stands sits in a column on the right: "On record now", the status in words, its place on the path, any change or no-signal note, and the counts.
- That status column is a button. It opens the row's detail under the row: the evidence when first reported, what the status means, the path with each place named, why the claim is there, the latest promise, and links to the records and the guide. The hover pop-up in the status card is removed, so touch and keyboard readers reach the same detail. Without scripting, and on paper, the detail is open.
- A registry row takes the same shape. It leads with the claim's newest report, quoted, and says how many years ago the claim was first reported when that was in an earlier year. What was recorded is one dated item on the panel blue: the identifier, linked to its source, what was recorded and the date. The status column says "Changed" with the status before and after, or the status now.
- A status off the path (no trial record found, failed, terminated, retracted) is drawn as the path with no place marked and a square after it, beside its words.
- In search results the status column moves to the right of the match, the same as in the Latest list.
- Status words stay in the site's one accent colour. No status has a colour of its own.
- The meaning of "Trial registered" becomes "A clinical trial is registered. None that has started has a phase." The old wording, "No trial with a phase has started", read as a contradiction beside a detail saying the claim's trials had started (decided by the operator on 2026-11-16).

## Not changing

- Rows stay one per dated item, under the heading of their own date, so the kind and span controls, the counts and the last-visit line work as before. Merging one claim's items across days, as the mock did, would file a record under a day it is not dated, so it is left out.
- Promise rows, the to-come list and the older claim keep their content.
