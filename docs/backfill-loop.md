# The backfill improvement loop

How a backfill is run so that each batch leaves the next one better: a batch, its audit, its defects, a labelled sample, one change, and the figures before and after.

The record of it is a spreadsheet in the operator's Drive, "whatcameofit: backfill improvement loop". It is not in the repository: it holds real addresses and headlines. Nothing in it is article text, and nothing says who shared or asked about an article.

Commands below are run as `docker compose run --rm pipeline thenwhat …`, or `uv run thenwhat …` in `pipeline/`.

## What done looks like

Set by the operator on 2026-11-16, for the production database:

- 1,000 or more clinical trials tracked: trials active in phase 2 or 3, and trials recently completed.
- 1,000 or more article addresses, and the places they were shared, linked to those trials and to papers.

Where it stood that day: 2,101 distinct trials with approved events on 424 approved claims; 640 source articles on approved claims; 4,814 leads passed by triage, of which 1,603 had been read.

Two things in the target are not settled and are the operator's to define: what counts as a trial having succeeded, which no registry states and which the site may not word as a verdict; and whether a shared post is itself kept, which today it is not beyond its community, time and score.

## One loop, one batch

A batch is about 200 reads. Each step names what goes on which tab of the spreadsheet.

### 1. Before

- Measurements are on: `MEASURE_DIR`, `MEASURE_KEEP_DAYS` and `MEASURE_LOOKUP_KEEP_DAYS` are set. A batch run without them has no figures and does not count.
- `thenwhat backfill plan`: what is due and what it would cost. Show the operator before a step that spends.
- Decide the **one** change this batch tries, if any, and write it on *Strategies* with the figure it should move and that figure now. One change a batch: with two, neither can be credited.

### 2. Run

```sh
thenwhat backfill run link_read --limit 200
thenwhat prepare --pending
```

A claim `prepare` approves for a read is held awaiting audit.

### 3. Audit

```sh
thenwhat audit list
```

Read every held claim: its article, its approved trial matches with their reasons, its papers, its status. Archive what is wrong. Clear the rest:

```sh
thenwhat audit clear <slug>…
```

The list ends with the reads that overlap a claim that is not archived: the read drafted that claim's treatment and condition, the decision did not say the article reports it, so no claim was made and nothing was attached. Such a read is never tried again. Settle each by its lead number:

```sh
thenwhat audit attach <lead>…                 # the article is a report of that claim
thenwhat audit dismiss <lead>… --reason "…"   # it is not
```

`audit attach` asks the page reader for the page again, under the rules of any read (a held outlet, or one asked a moment ago, is left for later and the command is run again; a refusing outlet is not asked; the request counts against the reader's allowance), and takes the headline and publication date from the page, never from the title or time the link was shared with. It reads the page once with the model for its reported statements, as any read does. Only an approved claim that is not archived is given an article; its review state is unchanged and it is put on no hold. A lead it cannot attach is said so and stays listed. `audit dismiss` attaches nothing and keeps the reason, privately.

A review decision an assistant makes is recorded with `--as-assistant`.

### 4. Defects

Every wrong thing found, in the audit or anywhere else, is one row on *Edge cases*: the address, the step that went wrong, a category from *Defect categories*, what happened and what should have. A defect that was archived still gets its row: the archive removes the claim, the row keeps the lesson.

Use the categories as they are. "other" is for what fits none of them, with a note; three of the same "other" is a new category.

### 5. Sample

```sh
thenwhat backfill sample-leads --size 100
```

This draws scored leads in equal numbers from each tenth of the score range, without showing the scores, and leaves out leads already labelled. Most leads sit in the lowest tenth, so that is where a missed report hides: add `--tenth 0.0` for a second draw from it alone. Once the prefilter exists, leads it settled are sampled the same way.

Label each on *Samples* as a treatment report, other health, or not health, and record the labels from a file of lead numbers and labels:

```sh
thenwhat backfill label-leads <file>                  # the operator's own labels
thenwhat backfill label-leads <file> --as-assistant   # an assistant's
thenwhat backfill evaluate-leads
```

Scores go on the sheet only after the labels are in. Labels by an assistant are marked `assistant`; the operator checks a share of them with `thenwhat backfill spot-check-leads`, and the *Operator check* column says how each came out.

Precision is the share of passed leads that are treatment reports. Recall is the share of treatment reports in the sample that were passed or held.

### 6. Scorecard

```sh
thenwhat measure --days 1
thenwhat backfill funnel
```

One row on *Batches*: leads in, settled, triaged, passed, read, unreadable, new claims, articles added, approved, archived at audit, published, precision, recall, model cost, time working and waiting, what was waited on longest, defects logged.

### 7. Go on, or stop

Stop and fix before another batch when either holds:

- the archive rate at audit is higher than the batch before;
- precision is lower than the batch before.

One worse batch is enough to stop. The cause is on *Edge cases*; fix the commonest category first.

### 8. Close the change tried

On *Strategies*, fill the figure after, what else moved, and whether it is kept. A change is kept only on measured figures, on the same leads where that is possible (`openspec/changes/work-reuse-and-metrics`, "A saving is claimed only from measurements").

## From an edge case to a test

A defect seen in two batches gets a regression test before the third.

- The test is written at the seam the defect belongs to: a pure function, a function that takes a session, or a command.
- **The test uses a made-up article.** Article fixtures are always synthetic, and no article text is stored anywhere, test fixtures included. Write a synthetic headline and page with the same shape as the real one: the same trap, none of the words.
- The real address stays on the sheet. The row's *Regression test* column names the test; *Fixed in* names the commit or step version.
- A fix that changes what a step decides raises the step's version, so the records it touched are due again and the before and after can be compared.

## Order of batches

1. Leads that name a topic the operator follows.
2. Leads already passed and not yet read. They cost no triage.
3. Then by month, oldest first: an older report has had longer for a trial to follow.

## What the loop does not decide

- What is published: rules approve, the audit releases, the operator archives (`docs/adr/0001`, `docs/adr/0007`).
- Thresholds, the outlet list, the spend ceiling: the operator's. The loop supplies the figures.
- Whether a strategy is tried at all: one a batch, named beforehand.
