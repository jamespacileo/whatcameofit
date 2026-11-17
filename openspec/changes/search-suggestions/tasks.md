# Tasks

- [x] 1 Mock four options from real rows of the published export. Verify: 1440px light and dark; the phone frames at 375px.
- [x] 2 The rules as pure functions (`suggest`, `suggestParts`, `suggestWords`). Verify: `site/tests/suggest.test.mjs`.
- [x] 3 The panel in the box's script: rows as links, the keys, a press, closing on Escape, on a press elsewhere and on a search. Verify on the dev server with the published export, typed "lung": five kinds; down chooses the first row, up from the box the last, Escape closes and keeps the words; a condition's row searches for it and puts it in the address; "nct0793" finds trials by identifier; an address, one letter and letters that match nothing offer nothing; a treatment's row leads to its claim.
- [x] 4 Styles on the type scale, in both themes. Verify: 1440px, the panel the width of the box and its button, over the card under it, ending inside the screen and scrolling within itself; 375px, rows 44 pixels or more, over the list's kept heading, no sideways scroll; `site/tests/primitives.test.mjs`.
- [x] 5 `DESIGN.md`.
- [ ] 6 Conditions written several ways in the published claims ("Alzheimer's disease", "Alzheimer disease", "Alzheimer’s disease") are offered as separate rows. Bringing them to one name is the pipeline's, not this change's.

Not checked: a screen reader's reading of the rows; a row taken by Enter in a real browser (the keys were sent by script); forced colours; the box on pages other than the home page.
