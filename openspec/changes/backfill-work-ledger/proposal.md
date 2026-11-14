# Proposal

## Why

The pipeline works one claim at a time, from an article to its registry records. Filling the tracker at volume means working the other way too: starting from the registry's trials and looking for the news that reported them. A sample taken on 2026-11-14 shows the size of that job and how it fails without bookkeeping.

- ClinicalTrials.gov holds 611,771 studies. 43,320 are phase 3 trials of a drug or biological.
- Of 200 sampled phase 3 trials, 104 (52%) had a news article on the intervention for that indication, and 40 (20%) had one about that trial. Most of those articles were in the clinical trade press; a general news outlet was the best result for about one trial in twenty. A first pass with one search per trial had found only 31%.
- The sample run lost its results once to a cleared temporary folder, stopped once because four workers shared a search allowance none of them could see, and was refused by a news index for exceeding a rate nobody had counted beforehand.

Nothing in the pipeline records which record has been through which step, so a run that stops has to start again, and a new kind of processing cannot be added without re-running the old kinds.

## What Changes

- Add a **work ledger**: a database record of every step completed for every record, so a run processes only what has not been processed.
- Add **steps**: small units of processing that each declare which records they apply to, which source they ask, and what one record costs. A new step starts with nothing done and runs over everything once; existing steps are not re-run.
- A step carries a version. Raising it makes that step due again for every record, and for no other step.
- Add `thenwhat backfill plan`, which reports for each step how many records are due, how many requests that needs, what it costs and how long it takes, before anything is sent.
- Add `thenwhat backfill run`, which works through due records, can be stopped and restarted, and can run in several processes without doing the same record twice.
- Add **source allowances** kept in the database: how many requests a source may receive in a period, shared by every process, checked before each request.
- Add a **registry corpus**: trial records loaded in bulk from ClinicalTrials.gov's list endpoint and kept whether or not any claim refers to them.
- Add the first step, a **news search** for a trial's intervention and indication, which stores **article leads**: address, outlet, title and date, never text.

Not in this change:

- Turning an article lead into a claim or a source article. A lead is not published and changes no status.
- Searches of social media, matching of papers to new items, and organisation knowledge cards. Each is a later step that this change makes room for.
- A workflow orchestrator. Steps are plain functions run from the command line.

## Capabilities

### New Capabilities

- `work-ledger`: which step has been completed for which record at which version, how due work is found, planned, run, retried and resumed.
- `source-allowances`: request allowances per source and period, held in the database and shared by every process that asks that source.
- `registry-corpus`: trial records loaded in bulk and kept independently of claims, with their raw payload and fetch time.
- `article-leads`: news articles found for a registry trial by search, stored as address, outlet, title and date and kept apart from source articles.

### Modified Capabilities

None. Existing claim, resolution and evidence behavior is unchanged: nothing in this change writes a claim, a match or an evidence event.

## Impact

- **Database:** new tables for the ledger, source allowances, registry trials and article leads, added by a new migration. No existing table changes.
- **Pipeline code:** a new package for steps and their runner, and new `backfill` commands. Existing commands are untouched.
- **External services:** ClinicalTrials.gov's list endpoint, at about 620 requests for a full load. One news index, not yet chosen: its terms, authentication and rate limit must be read and written into `docs/sources.md` before its client is written.
- **Cost:** no model calls. The news search is requests only. The plan command reports the number before a run.
- **Documentation:** `GLOSSARY.md` gains step, work ledger, registry trial and article lead. `docs/sources.md` gains the news index and the bulk use of the trial registry.
- **Site and extension:** no change. Nothing here reaches the export.
