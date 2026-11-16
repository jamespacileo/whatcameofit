# Design

## Context

What exists, read from the code on 2026-11-16:

- `backfill/link_readers.py` turns one row of a Hacker News parquet file, or one line of a Reddit zstandard file, into a `SharedLink` (address, community, time, score, title, item number) or a reason it is skipped. It asks a parquet file for eight columns only and reduces a Reddit line to seven fields at once, so an author or a text never outlives the row.
- `backfill/address.py` gives the address key the site's comparison also gives (one fixture proves them equal). `backfill/outlet_kinds.py` gives an outlet's kind by rule. `backfill/topics.py` says whether a title names a topic word.
- `backfill/link_load.py` stores every link as a `link_lead` row and a `link_share` row. `link_screen`, `link_triage` and `link_read` are steps of the work ledger (`backfill/ledger.py`, `runner.py`): each takes a database session, and the ledger keeps what is due, attempts, errors and step versions. Spend is counted in `llm_usage` against a monthly ceiling (`backfill/spend.py`).
- Tests sit at the seam "functions that take a session" (`CLAUDE.md`, working rules).
- `scripts/fetch_link_files.py` fetches the files into `data/link-files/`: 23 Hacker News months, and one file a Reddit community.

Measured on 2026-11-16 on the Hacker News files: 599,262 link posts; 535,124 on unlisted outlets; 64,130 on listed outlets (general news 63,771, trade press 180, press release 179); 513,117 distinct address keys, 54,863 on listed outlets. Largest unlisted domains: github.com 56,806, youtube.com 19,455, twitter.com 8,260, nature.com 3,677. 344 titles name a GLP-1 topic word, 178 of them on unlisted outlets. The Reddit files were still being fetched and are unmeasured.

`cloudflare-source-of-truth` defines the store this change pushes to, its merge by natural key and its conflict rules. This design assumes that merge and adds nothing to its rules.

## Goals / Non-Goals

**Goals:**

- A backfill needs Python, the repository and a folder. No database server on the device.
- The same run can be stopped anywhere and started again without paying for anything twice.
- A second device, or a reader's lookup, having already scored or read an address means this run does not.
- Rows that are never used never reach any store.
- A defect in a file or a row is counted, set aside and visible.

**Non-Goals:**

- Changing what triage asks, what a read extracts, or any rule that approves, prepares or audits.
- Replacing the work ledger for the registry-first route.
- A general pipeline framework. Five stages, in order.
- Sharing run folders between devices. What is shared is what was pushed.

## Decisions

### 1. A run is a folder

`BACKFILL_RUNS_DIR/<run id>/`, created by `thenwhat backfill run start <platform> <files…>`:

| File | Written by | Holds |
| --- | --- | --- |
| `run.json` | start | run id, device, commit, step versions, outlet list version, thresholds, the reference file's id, the input files with their sizes |
| `links.parquet` | load | one row a share on a listed outlet: address, address key, outlet, kind, title, platform, community, time, score, item number |
| `tally.csv` | load | unlisted domain, platform, link posts, posts naming a topic word |
| `quarantine.csv` | any stage | file, position, kind of error. Nothing of the row |
| `leads.parquet` | screen | one row an address key: earliest title, first shared, outcome, links to tracked claims and trials with reasons |
| `triage/part-*.parquet` | triage | address key, score, triage version, decision id; one part a batch |
| `usage.jsonl` | triage, read | one line a model call: step, tokens, cost |
| `reads/part-*.jsonl` | read | one line a lead read: outcome, and the claim, article, statements and events it produced, by natural key |
| `results/*.jsonl` | prepare | the records to push, one file a kind, in the form the merge takes |
| `report.json` | each stage | counts, reconciled |

The run id is a time and the device's name. Deleting the folder is the cleanup.

Where the folders live is a setting, not a place in the repository. Bulk files, run folders and database dumps are large and the Mac mini's internal disk is small (31 GB free on 2026-11-16), so the operator said that day to use the external NVMe volume there, which had 1.5 TB free. `BACKFILL_DATA_DIR` names where bulk files are fetched to and `BACKFILL_RUNS_DIR` where runs are made; neither has a default inside the repository once this change is applied, and a stage refuses to start when its folder's volume is not mounted, so a run never falls back silently to the internal disk. On the Mac mini, following that volume's own layout: datasets under `data/whatcameofit/`, runs under `scratch/whatcameofit/`, dumps under `archive/whatcameofit/`. A MacBook sets its own paths.

With that space, Reddit's monthly dumps (about 17 GB a month of submissions, some 375 GB for 2025-01 to 2026-10) fit, which they did not on the internal disk. `docs/sources.md` records why the search interface was used in their place; that reason no longer holds on this device.

Considered: a SQLite file a run. It keeps SQL and transactions, and under D1 it would even be the store's own dialect. It also keeps a schema and migrations on every device for work that is five passes over files. It stays the fallback if decision 4's file discipline proves fragile.

### 2. Tables for the wide stages, records for the deep ones

Load, screen and triage handle hundreds of thousands of rows of a dozen flat columns: columnar files and a dataframe library fit. Read and prepare handle hundreds to a few thousand items, each a nested thing (a claim with its articles, statements and events): one JSON object a line fits, and it is already the merge's input form.

The per-row functions stay Python functions and are called a row at a time: `article_key`, `kind_of` and the topic match define what the site and the pipeline agree an address is, and re-expressing them as column operations would be a second implementation to keep equal. At these sizes that costs about a minute a platform.

The library: Polars, for lazy reads of parquet with only the columns asked for, joins and group-bys without loading a whole file, and no server. `pyarrow` is already a dependency and stays for the Hacker News reader. Considered: pandas, which loads whole files and adds nothing here; DuckDB, which is a good way to ask questions of the files by hand and is not needed in the code path.

### 3. The outlet rule is the first thing applied

The load reads each bulk file through the existing reader, computes the address key and the outlet's kind, writes the share to `links.parquet` when the kind is known, and otherwise adds the domain to the tally. Nothing downstream ever sees an unlisted link.

Adding an outlet later means starting a run over the same bulk files: the reference file (decision 5) then leaves out everything already handled, so only the new outlet's leads cost anything.

**Outlets added, decided by the operator on 2026-11-16.** Asked which of four groups of unlisted outlets to add, from counts over the 2,328,716 unlisted leads in the present database (400,729 domains), the operator chose all four:

| Group | Examples | Leads | Titles with a health word |
| --- | --- | --- | --- |
| News | arstechnica.com, vox.com, gizmodo.com, axios.com, businessinsider.com, newyorker.com, theverge.com, techcrunch.com, technologyreview.com, politico.com | about 145,000 | about 2,100 |
| Science news | phys.org, neurosciencenews.com, news.mit.edu | 16,112 | 461 |
| Journals and paper indexes | nature.com, science.org, jamanetwork.com, nejm.org, thelancet.com, bmj.com, pubmed, medrxiv.org | 26,891 | 2,173 |
| Regulator, video and social | fda.gov; youtube.com, twitter.com, medium.com | 203,858 | 967 |

The health-word count is the assistant's rough keyword match on titles, not triage.

The first two groups are news reports and go on as general news or press release, through the steps that exist. The other two are not news reports: a paper is evidence, a regulator's notice is evidence, and a video or a post is a way to an article. The rule that a claim needs a news article stands. So their kinds are added to the outlet list now and the load keeps their links as leads, with the screening outcome awaiting a route; each gets its route by its own change (papers; regulators' notices; video and posts), and until then none is scored or read. Keeping them costs rows and no money.

Score is not a filter. 29,263 of the 64,130 listed Hacker News shares have a score under 3; a post's score says who saw it, not what the article reports.

### 4. Paid results are on disk before the next call

- Triage writes one part file for each batch of twenty as the batch returns, and one usage line. A stop loses at most the batch in flight.
- A read writes one line when it finishes. A stop loses at most the read in flight.
- Every file is written under a temporary name and renamed, so a part is whole or absent.
- A stage starts by reading its own parts and leaving out every address key they hold. That is the whole of resuming.
- A failed item is written as a result with its error and an attempt count; a stage retries it up to the cap the ledger uses today and then leaves it.

This replaces, for this route, what the ledger's rows do: due, attempts, last error. A changed title making triage due again is handled by the triage part recording the title's hash.

### 5. The reference file is what the store already knows

`thenwhat backfill reference pull` asks the truth store's ingest address for one file: claim slugs with intervention, indication and state; source article address keys by claim; registry trials as the store holds them, without payloads; entity names; and, for every lead the store has, its address key with the triage version and score, and the read outcome where there is one. It also carries the work slices.

Screening anti-joins against it: an address that is a source article is already tracked; one the store has read is already read elsewhere. Triage leaves out an address the store has a score for at the current triage version, and copies that score into the run. Reading leaves out an address the store has a read outcome for.

A stale file costs a wasted call, never a wrong record: the merge decides against the live store. The run records which reference file it used, and a stage warns when it is older than seven days.

### 6. The spend ceiling is checked against two sums

Before each batch a stage adds the usage lines in the run folder to the month's usage the reference file reported for this device and for all writers, and stops when the next batch would pass the ceiling. `thenwhat backfill run plan` prints the estimate first, as `backfill plan` does today. The truth store's plan remains where the month's total is seen (`cloudflare-source-of-truth`, `specs/ingest-merge`).

Two devices working at once can together pass a ceiling each respects alone. The ceiling a device is given is therefore its own share, set in its `.env`.

**Set by the operator on 2026-11-16:** 100 US dollars a month in all: 40 for store-side processing, 30 for the Mac mini, 30 for the MacBook Pro. The separate cap of 13 dollars a month on readers' lookups is unchanged. For scale: scoring all 357,964 leads on listed outlets costs about 2 dollars at the price noted in `docs/sources.md`; reads are where the money goes.

### 7. Reconciliation, quarantine, budget

- Load: posts read equal shares written, plus posts skipped for each reason (no link, removed, own platform, no title, unusable address, outlet not listed), plus rows quarantined. A mismatch fails the stage.
- Each later stage: rows in equal rows out plus rows left out for each reason.
- A row that cannot be parsed goes to `quarantine.csv` as file, position and exception class. A Reddit line holds an author and text, so nothing of it is written.
- `LOAD_ERROR_BUDGET`, a share of rows with no default, stops the load when passed.
- Before reading rows, the load checks the file has the fields its reader takes.

### 8. Push

`thenwhat backfill push <run>`:

1. Registers the run with the store from `run.json`.
2. Hands over `results/*.jsonl` and `usage.jsonl` in parts, with counts and a checksum for each.
3. Asks for the merge and prints its report: added, matched, conflicts by kind; claims held for audit; slices marked done.
4. Marks the run pushed in `run.json`.

`--report-only` stops after the merge's dry-run report. Pushing a pushed run is refused by the store as already merged, which is the retry.

What is pushed for a lead that was not read: its address key, shares, screening outcome, triage score and version. That is how the next device knows not to score it again. **Confirmed by the operator on 2026-11-16:** every scored lead is pushed, rejected ones included, so triage can still be measured against its rejections; a lead that was screened and never scored is not. What is not pushed: anything on an unlisted outlet, and the tally, which stays with the files.

### 9. Preparing and auditing happen against the store

**Confirmed by the operator on 2026-11-16:** prepare runs store-side, in the same Python consumer that processes readers' leads, and the audit hold stays for claims drafted from a backfill's reads (it does not apply to claims a reader's lookup starts: `docs/adr/0009`).

A read drafts a claim; `prepare` searches registries for it and approves by rule; the audit then releases it. Under this change a run's `results` carry drafted claims with their reads' records, marked awaiting audit. Registry search and approval by rule run as they do today, against the store, after the push: they need the store's whole view of a claim (its other articles, its existing matches), which a run folder does not have.

So a device does the wide, cheap, discardable work and the reads; the store's side does what must see everything. The audit is where it is today: `thenwhat audit list` and `audit clear` against the store.

### 10. Work slices

A table in the truth store: platform, community, month, device, taken at, lapses at, the run that finished it. `thenwhat backfill slices take|release|list` call the ingest address. `run start` takes the slices its input files cover and warns when another device holds one. A merge marks a slice done when the run's `run.json` says the whole file for that slice was processed. Nothing checks a slice before merging: the merge is correct without them.

### 11. What becomes of the session-based steps

`link_screen`, `link_triage` and `link_read` each split into a pure function over rows and records (the rule or the call) and a thin stage that reads and writes files. The pure functions are what the tests exercise, with synthetic rows and the recorded Decisions fixture; one CLI test a command covers a success and a refusal.

The ledger, the runner and the session-based `news_search` step stay as they are for the registry-first route until that route is moved to the truth store by its own change.

## Risks / Trade-offs

- **A crash corrupts a run.** → Temporary name then rename; parts are small; a stage re-derives what is left from the parts present.
- **File discipline re-implements a ledger badly.** → It implements only due, done, attempts and error for a run that lives hours. If it grows past that, decision 1's SQLite fallback is taken.
- **Two rewrites at once: the store and the steps.** → This change is built after the store's merge exists, and the steps' rules are not touched; the pure functions are moved, not rewritten.
- **A stale reference file wastes model calls.** → The warning at seven days; `run start` pulls a fresh one by default.
- **Run folders hold titles.** → Not committed, deleted after push, on the device only.
- **Adding an outlet needs the bulk files.** → They are kept; the fetch script can fetch them again.
- **Prepare runs store-side, so a device cannot finish a batch alone.** → Intended; see decision 9. If the operator wants a device to prepare, the reference file has to carry far more.

## Migration Plan

1. Build the load stage, tally and checks. Dry-run the files already in `data/link-files/`. Show the operator the tally and agree outlet additions.
2. Split screen and triage into function and stage; run both on one month of Hacker News with a reference file made by hand from the present database, and compare outcomes and scores with what the session-based steps give for the same leads.
3. Split read; read one batch of 200; compare with the session-based read on the same leads.
4. When `cloudflare-source-of-truth` has its merge in preview: push that batch with `--report-only`, then for real, into preview.
5. Slices, when a second device is set up.
6. Remove the session-based link steps and `load-links` into a database once two batches have gone through the new route.

## Open Questions

- **Answered on 2026-11-16:** prepare is store-side (decision 9); the ceiling is 100 dollars split 40, 30 and 30 (decision 6); all scored leads are pushed (decision 8); all four groups of outlets are added (decision 3).
- **Reddit's listed share.** Unmeasured until the fetch finishes. r/science links mostly to journals and university sites.
- **The exact domains in each group.** The groups are decided; the lists are drawn up from the tally in task 2.8 and shown to the operator.
- **Order of the three routes** for papers, regulators' notices, and video and posts.
