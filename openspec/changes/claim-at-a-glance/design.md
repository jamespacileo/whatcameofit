# Design

## Context

- `site/src/pages/[slug].astro` (1,225 lines) draws the claim page in this order: reports, digest panel ("Where it stands"), follow offer, facts row, reported statements, timetable (`#timetable`), trials (`#trials`), papers (`#papers`), organisations, background, other claims, pass it on.
- The export already carries what the lines need. `ExportedTrial`: `state`, `phases`, `facts`. `ExportedTrialFacts`: `participants`, `allocation`, `masking`, `comparators`, `results`. `ExportedPaper.facts.year`. `ExportedEvent`: `type`, `event_date`, `trial_id` (results posted, trial completed).
- `site/src/lib/trial-facts.ts` already turns allocation, masking and comparators into fixed wording for a trial entry ("Randomised, quadruple-blind, compared with a sham procedure and no treatment"). `site/src/lib/status.ts` holds `assertNeutral`, run at module load.
- The site owns all wording; the export carries codes. `status/` in the pipeline is pure, and the same discipline suits a site-side summariser.
- `DESIGN.md`: say it once; no colour for any status; nothing moves on scroll; everything pressed is 44 pixels tall on a phone; a section with nothing to show has no placeholder.
- Change `plain-claim-page` is written and not started. It adds "In plain words" (three status-based answers) between the facts row and the timetable, and lists "an evidence snapshot of counts" and "a section rail" as out of scope. This change is that snapshot and that row.

## Goals / Non-Goals

**Goals:**

- A reader who stops after the first screen and a half knows how much is on record and what kind of record is missing.
- Every line can be traced: it links to the records it counts, and the rule that produced it is one function with one test per rule.
- No new data, no model, no export change.

**Non-Goals:**

- Judging the evidence. No line says a trial was small, weak, promising or enough.
- Repeating the status. Approval, phase and "tested in people" stay with the digest and `plain-claim-page`.
- Summarising a news report or a paper's findings.
- Showing posted result values outside a trial entry.

## Decisions

### 1. Rules live in one pure site module

`site/src/lib/glance.ts` exports `glance(claim): { onRecord: Line[]; notOnRecord: Line[] }`. A `Line` is `{ code, values, href? }`: a code, the numbers and dates it carries, and the id of the section it links to. Wording is looked up by code in a table beside the status wording and passed through `assertNeutral`. The function takes no clock: "running now" is read from each trial's exported `state`, not from today's date.

Alternative considered: compute the lines in the pipeline and export them. Rejected: it changes the export's shape for something derived wholly from fields already exported, and the site already derives trial wording the same way.

### 2. The line rules

Lines appear in this order; a rule that does not apply yields no line.

On record:

| Code | Applies when | Wording (values in braces) |
|---|---|---|
| `trials` | 1 or more trials | "{n} trials in people" + state clause: "all completed", or "{c} completed, {r} running" |
| `largest` | any trial states `participants` | "The largest enrolled {n} people" + comparator clause from `trial-facts.ts` when its record names one |
| `sizes` | 2 or more other trials state `participants` | "The others enrolled {a} and {b} people" (up to 3 values, then "between {min} and {max}") |
| `results` | 1 or more trials with results | "{k} of {n} posted results to the registry, the latest on {date}" ("All {n}" when k = n) |
| `papers` | 1 or more papers | "{n} papers" + ", published {y1} to {y2}" when any year is known (one year when equal) |

Not on record:

| Code | Applies when | Wording |
|---|---|---|
| `none_running` | trials exist, none recruiting or active | "No trial running now. The last one completed on {date}." (date sentence only when a completion date is on record) |
| `no_results` | trials exist, none has results | "No trial has posted results to the registry." |
| `no_comparison` | trials exist, at least one states its design, none names a comparator | "No trial on record had a comparison group." |
| `no_randomised` | trials exist, at least one states allocation, none is randomised | "No randomised trial on record." |

Mockup lines dropped, and why:

- "No approval" and "No trial with a phase": the digest's meaning sentence and `plain-claim-page` say them.
- "Two trials were small": "small" is a judgement. The sizes are stated under "On record" instead.
- "The news report gave no trial sizes or results": no exported code says so; only the model-written summary does.

### 3. Headings are "On record" and "Not on record"

The mockup's "review style" alternative is not built. The second list is drawn with a dashed outline and hollow markers, the first with a hairline and solid markers, in ink and the accent only. No tick, cross, red or green.

### 4. Placement

Order under the title: reports, digest panel, follow offer, **row of section links**, **At a glance**, facts row, then the page as it is. When `plain-claim-page` ships, "In plain words" keeps its place after the facts row. Both sections are short, and neither repeats the other because of decision 2.

On a phone the two lists stack, "On record" first.

### 5. The row of links is plain and still

Outlined pills in the existing pill style, each an anchor to a heading id that already exists (`#trials`, `#papers`, `#timetable`) or is added (`#glance`, `#background`). Counts come from the same arrays the sections render. It is not sticky. On a phone it is one row that scrolls sideways and fades at the ends, as the topic directory's jump row does. Reaching a section uses the existing "reached by a link" highlight.

Alternative considered: a sticky bar. Rejected for now: `DESIGN.md` keeps the page still on scroll, and a sticky bar on a phone takes space from the status.

### 6. Hidden from search and unchanged elsewhere

The section carries `data-pagefind-ignore`, like the other derived sections. Cards, the embed, `lookup.json` and the extension are untouched.

## Risks / Trade-offs

- A "Not on record" list can read as a list of faults. Mitigation: absence-only wording, the one-line note that it is not a verdict, and the neutral-wording check on every string.
- A wrong match makes a wrong line (a trial for another indication inflates the count). Mitigation: lines use only the trials and papers the page already shows and link to them, each with its match score.
- "Running" depends on mapping `TrialState` values correctly. Mitigation: an explicit set of running states in `glance.ts`, and a test that every `TrialState` value is classed as running, completed or other, so a new state fails the build until classed.
- Two summary sections near the top once `plain-claim-page` ships. Trade-off accepted; to be looked at together in the browser when the second one lands.
- Open question for the operator: whether "No approval on record" should appear here until `plain-claim-page` ships. This design says no.
