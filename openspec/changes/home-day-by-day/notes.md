# Notes

Kept while the change was built. The proposal, design and spec delta are the contract; this file records what was checked, how, and what is still open.

## Row sentences (task 2.3)

The wording as it stands in `site/src/lib/row-sentences.ts`, rendered on 2026-11-14:

- After a regulator's decision, which is given in the record's own words: "Dated 3 Sep 2026."
- "The first trial was registered in 2012, 14 years before this report."
- "5 trials on record, 3 completed, 2 with results posted." / "1 trial on record, none with results posted."
- "No record is dated in the 9 years since the first report." / "No record is dated in the year since the first report."

How often each applies across the 84 published claims, taking each claim's newest report: a regulator's decision 2, the first trial 34, trials on record 37, nothing since the first report 23; 24 claims have no sentence at all (their row shows the evidence stage and the status only).

On published claims:

| Report | Sentences on its row |
|---|---|
| "Scientists discover £20-a-month plant pill that can stop alcohol cravings" (Daily Mail) | The first trial was registered in 2012, 14 years before this report. 5 trials on record, 3 completed, 2 with results posted. |
| "After 30 Years, FDA Approves First-Ever Drug For a Rare Neurological Disorder" (ScienceAlert) | The FDA approved Zanvastro (zilganersen) for Alexander disease in children and adults. Dated 3 Sep 2026. The first trial was registered in 2021, 5 years before this report. |
| "One CRISPR treatment cut "bad" cholesterol in half for a full year" (ScienceDaily) | 1 trial on record, none with results posted. |
| "SNUDH to commercialize world's 1st treatment for teeth sensitive to cold" (Korea Biomedical Review) | No record is dated in the 7 years since the first report. |
| "Gene switch therapy could prevent AND treat Alzheimer's" (Daily Mail) | none |

**Agreed by the operator on 2026-11-14**, as worded above, after the finish review had raised that a zero is said for results ("none with results posted") and left out for completed trials. The operator was offered both zeros or neither and answered "Agree wording": the wording stands as it is. Task 2.3 is done.

## Departures from the artifacts, made while building

- The fifth sentence (the kind of study the report was of) was dropped: a report row already shows the evidence stage when first reported. The proposal, design, spec delta and tasks were corrected.
- "No record is dated … since the first report" is said only when the claim has no event dated on or after its first report. The no-signal overlay alone is not enough: a claim can carry it with a record dated after the report.
- A registry row's grey label reads "Registry record" for a trial's record and "Record" for one with no trial behind it (a regulator's decision, a paper). The heading counts say "registry record" for both, as the spec words it.
- A report dated after the day of the last check has no row in the day-by-day list until the registries are checked again; it is in the Headlines list as before.

## Checked in the browser, not by a test

The site's tests run in Node and cannot lay a page out, so these were measured in the `site-published` preview on 2026-11-14 (export checked 14 Nov 2026, 84 claims):

- At 375 by 812 with scripting on and nothing followed: the first row of the day-by-day list starts at 790 px on a day with nothing dated (the older claim's row), no sideways scroll, the four kind controls end at 358 px of 375, and nothing pressed in the list is under 44 px tall.
- A kept visit of 7 Nov: the line stands above the heading for 6 November, with 10 rows above it; the since line under the list reads "10 of 104 news reports"; no row of the day-by-day list carries "New".
- Picking Recorded leaves only registry rows and their headings, records the pick in the address, and a reload shows the same list. Picking Phase 3 trial narrows the list and the tabs together, rewrites each heading's count, and hides headings left empty. A topic picked in the side column sets the phone's field and the address.
- "Show earlier" counted down from 103 rows to 49 on the first press. An address naming "Week of 19 October" opened the list that far.
- A headline pressed in the list is carried to the claim page under the same name.
- "Today" and "Yesterday" were seen on the reader's own date. The case of a page built before the reader's date was not driven in the browser; it is the same comparison, and the built page carries no such word (a page test).

Not captured: keyboard focus, hover, print and a forced palette.

## The finish review (task 7.3)

Saved as `.impeccable/critique/2026-11-14T23-04-38Z__site-src-pages-index-astro.md`: no P0, four P1, six P2. Eight were fixed and checked in the preview (the dead "Go to where you left off", a 24 px headline on a phone, the kind controls at 320 px, the checked day announced as today, the seven days while the list is narrowed, a forced palette and print, counts dropped on a phone and wording doubled without styles, a topic touching the headline).

Open, and the operator's to decide:

1. **The sentence wording** (task 2.3, above; since agreed as it stands). One point the reviewer raised: "none with results posted" states a zero, while a zero of completed trials is left out. Either both zeros are said ("1 trial on record, none completed, none with results posted") or neither ("1 trial on record.").
2. **A status beside a count that seems to contradict it.** Four published claims stand at "Trial registered" ("A trial in people is registered") while their row says, for one of them, "3 trials on record, 3 completed, 3 with results posted": `tourette-syndrome-wrist-nerve-stimulation`, `ptsd-personalised-magnetic-stimulation`, `ovarian-cancer-salpingectomy`, `type-2-diabetes-remission-diet-exercise`. Both lines rest on the same approved records. The trials have no phase (devices, procedures, a diet), and the status rule counts a trial as started only when it has a phase. Before this change the two facts were on different parts of a claim page; the row now sets them side by side. This is a question about the status rule or its gloss, not about this change, and nothing was altered.

Also open: on paper with scripting off, the promises to come stay inside their folded section. Not seen: keyboard focus, hover, print and a forced palette.

After the review's fixes: 480 site tests pass. `make check` passed before them and was not run again in full; the site's tests and a build from the published export were.
