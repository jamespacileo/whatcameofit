# Design

## Context

- `site/src/pages/index.astro` (878 lines) declares the home page's lists as `views` (id, tab label, count) and draws each as a `section.feed-panel` holding a `table.index` and a `Pager` of 10 rows. Rows carry `data-status` and `data-topic`. One `StageFilter` above the lists (scope `[data-feed]`, address parameter `status`) and a topic select narrow every list at once. A script turns the panels into tabs and records the one in view in the address; with scripting off the panels follow one another.
- `site/src/components/ClaimTable.astro` is the site's claims table, used by the topic, year, source and approval pages, a guide entry, and "Other claims" on a claim page. Columns: Claim (`ClaimName`: name as the link, headline in grey), First reported, Latest promise (pale amber, only when a claim in the list has one), Status (`StatusCell`: label, small track, gloss). Under 40rem rows become labelled blocks. It pages at 25 and shows a stage filter from six claims.
- `site/src/lib/record-brief.ts` builds the first answer of "The record in brief" in `testedRow`: "In {n} trials. {max} people in the largest", "In {n} trials", or "None on record"; `resultsRow` words whether results are posted; `FIRST_REPORT` words what the first report was about.
- `site-publishing` requires: the home page's lists in dated orders that never rank claims; long lists paged; lists narrowed by status and topic; claim lists led by the intervention name.
- `DESIGN.md`: Index tables as above; Home tabs "four tabs on a hairline", on a phone in one row without counts, wrapping where a narrower screen cannot hold them; pale amber means "promised" and nothing else; tint is the topic chip's.
- The first mockup (board D) was critiqued on 2026-11-14: generic cards in place of the index table, the promise column dropped, five filter chips beside five tabs, chip labels that did not parse.

## Goals / Non-Goals

**Goals:**

- A reader can skim every claim the site tracks from the home page, in the table they meet everywhere else on the site.
- A row says how much testing stands behind a claim without the page being opened.
- The row and the claim page say the same thing, from one rule.

**Non-Goals:**

- Ranking or filtering claims by how much they have been tested.
- A new kind of control on the home page.
- Result values, or anything a model read, on a row.

## Decisions

### 1. Claims is a fifth list, second in order

`views` gains `{ id: "claims", tab: "Claims", count: data.claims.length }` after Headlines. Its panel is drawn like the other panels: heading "Every claim tracked", one grey line, a `table.index`, a `Pager` of 10. Rows are in order of `first_reported_date`, newest first; a claim with no date goes last, by name. Rows carry `data-status` and `data-topic`, so the existing status counts and topic select narrow it with no change to their script.

Second, not first: a reader arriving from a search or a shared link is looking for a headline, and "A headline starts on a phone's first screen" stays true.

Rejected: reusing `ClaimTable` for the panel. It brings its own pager of 25 and its own stage filter, and the home page already has one of each for all its lists.

### 2. The column, and the one rule behind it

`record-brief.ts` exports `testedSummary(claim): { lead: string; detail: string | null }`, built from the functions the brief already uses:

| Claim | `lead` | `detail` |
|---|---|---|
| Trials, a stated size | "In {n} trials" | "{max} people in the largest. Results posted by all {n}" / "…by {k} of {n}" / "No results posted" |
| Trials, no stated size | "In {n} trials" | "Results posted by …" / "No results posted" |
| One trial | "In 1 trial" | "{max} people. Results posted" / "No results posted" |
| No trial, first report known | "None on record" | "The first report was about a study in animals" (per `FIRST_REPORT`) |
| No trial, nothing known | "None on record" | none |

`testedRow` and `resultsRow` are rebuilt on the same counts, so the brief's "In 3 trials. 135 people in the largest" and a row's "In 3 trials" / "135 people in the largest" come from one place. A test compares them.

`site/src/components/TestedCell.astro` draws `lead` in semibold and `detail` on a grey line, the pattern `StatusCell` uses for a label and its gloss. No link in the cell: the row's link is the claim's name.

### 3. Where the column appears

In `ClaimTable`, so every claims table has it: topic, year, source and approval pages, the guide entry's list and "Other claims" on a claim page. Column order: Claim, First reported, Tested in people, Latest promise, Status. The promise stays beside the status, so what was promised still sits beside where the claim stands.

The note, "“Tested in people” counts the trials on record; it does not say what they found.", stands once above a table of six or more claims (where `ClaimTable` already shows its stage filter) and above the home page's Claims panel. A short table, such as the three "Other claims", carries the column without the note.

Rejected: the column on the home page only. A reader who learns the table on the home page would find it different on a topic page.

### 4. Widths and the phone

Wide: Claim 29%, First reported 14%, Tested 21%, Promise 16%, Status 20%; with no promise in the list the promise's share goes to Claim. A date never breaks. Under 40rem the row is a block, as today, with "Tested in people" as a labelled line after "First reported".

Home tabs become five. On a phone they wrap to a second line where a row cannot hold them, which `DESIGN.md` already allows.

### 5. No change to data

Every value is in the export already (`trials`, `facts.participants`, `facts.results`, `evidence_stage`). The Claims list is static HTML; the status and topic controls and the pager are the scripts already on the page.

## Risks / Trade-offs

- A count of trials can be read as a score. Mitigation: the note above the list, no ordering or marking by it, and the same words as the claim page, which carry their records.
- A wrong match inflates a row's count, as it does the claim page's. The row links to the page, where each match shows its score.
- A fifth tab crowds a phone's tab row. Accepted; it wraps. If it reads badly in the browser, the tab's label and order are the things to look at, not a new control.
- The home page gains up to 84 more rows of HTML. Ten are shown at a time; the weight is text.
- A fifth column narrows the claim's name on a wide screen. Mitigation: the widths above, and the headline is already held to two lines.
- This change edits `record-brief.ts`, which `plain-trial-entries` (PR 100) also edits to move its measure wording out. The two touch different functions; whichever merges second resolves a small conflict.
