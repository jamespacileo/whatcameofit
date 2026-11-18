# Proposal

## Why

A backfill from bulk files (`social-link-backfill`) works today inside the pipeline's database: every shared link is loaded as a row, then screened, scored and read there. With the truth store on Cloudflare (`cloudflare-source-of-truth`) that database is gone, and the operator said on 2026-11-16 that whatever a device uses while it processes a dataset is ephemeral and need not be a database at all: it can be dataframes.

Two measurements say the same. Over the 23 Hacker News monthly files for 2025-01 to 2026-11, read with the pipeline's own reader, address key and outlet list on 2026-11-16: 599,262 link posts, of which 535,124 (89%) are on outlets on no list and are never scored or read; 64,130 are on listed outlets, 54,863 distinct addresses. One streaming pass over all 23 files took about a minute. The work is a batch job over files of a few hundred thousand rows, and most of it is throwing rows away.

The present database shows what loading everything costs. Measured on the MacBook Pro on 2026-11-16: 2,686,680 link leads, of which 2,328,716 (87%) are on unlisted outlets and have no score, no read, no label and no link. `link_lead`, `link_share` and the ledger's `work_entry` are 2.9 GB of a 3.9 GB database.

The operator also wants the work to be possible on any device, the Mac mini today and a MacBook tomorrow, with nothing to install but Python.

## What Changes

- **A backfill runs in a folder of files.** Each stage reads the stage before it and writes its own file. There is no database on the device. **BREAKING** for `link-leads`: `thenwhat backfill load-links` no longer stores leads in a database.
- **Wide stages are tables, deep stages are records.** Loading, keying, filtering, screening and triage write columnar files. Reads, drafted claims and evidence are written one record a line, in the natural-key form the truth store's merge takes.
- **Only links on listed outlets go on.** A post on an unlisted outlet is counted by domain and dropped at the first stage.
- **A tally of unlisted domains** is written by the first stage: how many links each had and how many named a topic word. It is how the outlet list grows.
- **Nothing is paid for twice.** Before triage and before a read, a run leaves out every address the truth store has already scored or read at the current step version, from a reference file it pulls, and every address its own files already hold a result for.
- **A stopped run is started again.** A stage's results are on disk as soon as they are paid for.
- **Load checks.** A stage reconciles its counts, sets a failing row aside without its content, and stops when failures pass a budget. `--dry-run` reports and writes nothing but the tally.
- **Push.** `thenwhat backfill push` hands a run's results to the truth store's merge, shows its report, and can be asked for the report alone. The run folder can then be deleted.
- **Work slices** in the truth store record which platform, community and month a device has taken, so two devices do not pay for the same work.

Not in this change:

- The truth store and its merge. This change pushes to `cloudflare-source-of-truth` and cannot be finished before that change's merge exists.
- What triage asks, what a read extracts, how a claim is prepared or audited. Those rules are unchanged; only where their state is kept changes.
- The registry-first route (`backfill-work-ledger`) and the work ledger it runs on. Ordering that route by trial status and completion date, which the operator raised on 2026-11-16, is its own change.
- YouTube links (19,455 on Hacker News in the window) and links to journals. They are counted in the tally and go no further.
- Fetching the bulk files. `scripts/fetch_link_files.py` does that already.

## Capabilities

### New Capabilities

- `backfill-run-files`: a run as a folder of stage files; what each stage reads and writes; resuming; not paying twice; the spend ceiling; push.
- `reference-file`: what a device pulls from the truth store before it works, and what that file never holds.
- `work-slices`: which platform, community and month a device has taken, when a taking lapses, and that it never blocks a merge.

### Modified Capabilities

- `link-leads`: a load writes the leads on listed outlets to the run's files, tallies the rest, reconciles, quarantines and has a dry run.
- `lead-screening`: the outlet rule is applied at the load, screening reads the reference file, and its report takes unlisted domains from the tally.

`link-leads` and `lead-screening` are specified in `openspec/changes/archive/2026-11-18-social-link-backfill`, which is not yet synced to `openspec/specs`. This change's deltas are written against that text and apply after it is synced.

## Impact

- **Code:** new `pipeline/src/thenwhat/backfill/run/` for the stages and the run folder; `link_load.py`, `link_screen.py`, `link_triage.py`, `link_read.py` and `link_report.py` are rewritten to take and return rows and records in place of a database session, and their tests move to that seam. `link_readers.py`, `address.py`, `outlet_kinds.py` and `topics.py` are used as they are.
- **Dependencies:** `pyarrow` is already used. A dataframe library is added for the wide stages; which one is `design.md` decision 2.
- **Database:** none on a device. In the truth store: the `work_slice` table, and the reference export.
- **Configuration:** `BACKFILL_DATA_DIR`, `BACKFILL_RUNS_DIR`, `INGEST_URL`, `INGEST_TOKEN`, `WORK_DEVICE_NAME`, `LOAD_ERROR_BUDGET`, `SLICE_HOURS`; `.env.example` and the README's pipeline section.
- **Guardrails:** a run's files hold titles people shared articles under and, while a read is in progress, nothing of the article's text; they hold no post author, no post text and no post id. The folder is not committed.
- **Existing data:** the dataset files already fetched into `data/link-files/` are this change's first input.
- **Other changes:** `portable-backfill-promotion` is withdrawn; its load checks and tally are carried here.
