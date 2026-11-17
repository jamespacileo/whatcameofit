# The daily run

One job on the operator's Mac mini that keeps the private database fresh once a day: `scripts/daily-run.sh`, started by launchd. It brings in work and stops at the audit. What is on the site changes only when a person or an assistant audits, exports, commits and merges, as before.

## What one run does

In this order, each step with its start, end and outcome in the day's log:

| Step | Command | Spends |
| --- | --- | --- |
| database | `thenwhat db-check` | no |
| fetch-links | `scripts/fetch_link_files.py hackernews --since-last-fetch DAILY_RUN_FETCH_DAYS` | no |
| load-links | `thenwhat backfill load-links hackernews <month's file>`, once for each month the window touched, oldest first | no |
| screen | `thenwhat backfill run link_screen` | no |
| score | `thenwhat backfill run link_triage --limit DAILY_RUN_TRIAGE_LIMIT` | model |
| read | `thenwhat backfill run link_read --limit DAILY_RUN_READ_LIMIT --workers DAILY_RUN_READ_WORKERS` | page reader, model |
| prepare | `thenwhat prepare --pending`: every claim awaiting review, and every published claim with a part of its preparation still due | registries, model |
| trials | `thenwhat backfill load-trials --trials interventional --changes-only` | registry |
| refresh | `thenwhat fetch <slug>` for published claims, `DAILY_RUN_REFRESH_LIMIT` a run, in turn | registries, model |
| measure | `thenwhat measure --days 1` | no |

- **The link window.** The fetch asks the public ClickHouse copy of Hacker News (`docs/sources.md`) only for the stories with a link posted since a day before the end of the last window it fetched, which it records in `data/link-files/hackernews/last-fetch.json` once every month file is written. With no record it starts at midnight UTC `DAILY_RUN_FETCH_DAYS` days ago (default 3, 1 to 28). One run covers at most 20 days, two queries at most, so after missed nights (paused, drive not mounted, database down, a failed fetch) the gap is caught up from its oldest day, 20 days a night, and nothing is lost; the summary's link-files line says "still behind" until it has caught up. Each story is merged into its month's file: a story already in the file is replaced by its newer copy, and no other row is dropped. A narrower window fetched by hand never moves the record past a gap. On 17 November 2026 three days came to 2,867 stories, one query of the 20 an hour the copy allows (a query answers at most 10,000 rows), where the whole month had taken 2 hours 34 minutes of waiting out that limit. The run then loads each month's file the fetch says it wrote, oldest first; loading a link already stored adds nothing. To fill a past month by hand: `scripts/fetch_link_files.py hackernews <month> <month> --merge`, which asks for that month again and merges it into the file there.
- **One at a time.** The run holds a lock, a folder under `~/Library/Application Support/thenwhat/daily-run/`. A second run that finds a live one does not start and says so in the log. A lock left by a run that died is taken over.
- **Spend.** Before each step marked as spending, the run reads the month's recorded model cost from the database. It stops when that cost plus `DAILY_RUN_SPEND_MARGIN_USD` would reach `LLM_MONTHLY_BUDGET_USD`, or when today's cost has reached `DAILY_RUN_DAY_BUDGET_USD` if that is set. During the refresh it checks again before every 25th claim. A spend that cannot be read stops the run too. The pipeline's own refusal at the ceiling still holds underneath. `LLM_MONTHLY_BUDGET_USD` has to be set in the settings file: the run does not start on the pipeline's default.
- **A failed step does not end the run.** It is recorded, and the next step starts. Every step takes up where it left off, so the next day's run takes what this one missed. A stop for spend, a missing drive or an unreachable database does end it.
- **Pace.** The read asks the page reader, which decides whether and how a site is asked (`docs/adr/0006`). `READER_READS_AT_ONCE`, `READER_OUTLET_GAP_SECONDS` and `SOURCE_ALLOWANCES` pace it as in any other run; the job adds no setting of its own to them, and `DAILY_RUN_READ_WORKERS` may not exceed 4.
- **Trials.** The `trials` step keeps every stored trial current (below). It calls no model, so no spend check stands before it.
- **A period.** `LEAD_TRIAGE_SINCE` and `LEAD_READ_SINCE` narrow what is scored and read, here as anywhere.

The run ends by writing a summary: what was loaded, screened, scored and read; how many trials the registry changed, new and already stored; how many claims await audit, await review, and are approved and not held, before and after; what failed; the spend today and this month.

## Keeping the stored trials current

Every interventional study on ClinicalTrials.gov was loaded into `registry_trial` on 16 November 2026 (467,064 trials, 468 requests). The `trials` step asks only for the trials the registry updated since the last completed load of the same set, `AREA[LastUpdatePostDate]RANGE[<that day>,MAX]`, a thousand to a request, and stores each in place with its raw payload and fetch time. Its line in the summary reads, for example, "Loaded 1,240 trials updated since 2026-11-16 in 2 requests: 85 new, 1,155 already stored."

- **From when.** A load is completed when it reaches its last page. The next asks from the day that one started, so the 16 November load is the first `--changes-only` load's starting point. With no completed load of the set (a new database, or the `registry_load` row gone) it asks for every trial: about 470 requests and twenty minutes, still well inside the allowance.
- **The first full load needs about 470 requests in one allowance period.** A load that stops is not recorded as completed and its next start asks from page 1 again, so with no completed load (and every night until one completes) the allowance for `clinicaltrials.gov` must cover the whole set at once: at least 500 requests per period, with room for what else asks the registry that day. The default of 5,000 a day does. A changes-only load after it needs a few requests a day.
- **The allowance.** Each request is claimed against the registry's allowance in `SOURCE_ALLOWANCES`, 5,000 a day for `clinicaltrials.gov` unless set, shared with every other process that asks it. When it is used up, or the registry still says "too many requests" after the client's retries, the load stops. A "too many requests" is recorded as a pause for `clinicaltrials.gov`, as long as the registry asked or `pause_minutes` of its allowance, and no process asks it before that ends. Either way the load stops with what it stored and a `Stopped:` line, and the step is not a failure; that load is not completed, so the next run asks again from the same day. The refresh after it reads the registries for published claims as before.
- **What becomes due.** One step reads stored trials: `news_search`, which asks Media Cloud for articles naming a trial's intervention and indication, one request per trial. A trial the load adds has never been searched, so it is due. A trial the load updates is due again only when its searched name or indication changed (`mark_changed` compares what the step read with what is stored now); a new state, phase or date changes nothing due. `thenwhat backfill plan` shows how many are due and what they would ask.
- **Nothing acts on it here.** The daily run never starts `news_search`, and `make scripts-test` fails if it would. Those trials wait for a `news_search` run started by hand, or by the separate `com.thenwhat.backfill` job (`scripts/backfill-job.sh`, docs/lookup.md) where that is installed, which stays within Media Cloud's own allowance (4,000 requests a week unless set).

## What it never does

- It never runs `thenwhat audit clear`. A claim a read drafts and the rules approve is held awaiting audit (`docs/adr/0007`), and it stays held.
- It never archives or unarchives.
- It never runs `thenwhat export` or `make publish-data`, and never touches `site/data/`.
- It never commits, pushes, pulls or switches a branch. The checkout it runs from is updated by the operator.
- It never starts Docker or the database.
- It never starts `news_search`, or any step over the trials it loads.

`sh scripts/daily-run.sh --dry-run` prints every command a run would start and touches nothing. `make scripts-test` checks, against a stand-in for the pipeline, that none of the commands above is ever among them.

## Yesterday's summary

```sh
sh scripts/daily-run.sh summary
```

- The summaries: `~/Library/Application Support/thenwhat/daily-run/summary-YYYY-MM-DD.md`, and `latest.md` beside them.
- The logs, one a day: `~/Library/Logs/thenwhat/daily-run/YYYY-MM-DD.log`. What launchd itself has to say goes to `launchd.log` in the same folder.
- Both are kept `DAILY_RUN_KEEP_DAYS` days. They hold counts, slugs, registry facts and addresses that failed. They never hold article text.

## Watching a run while it works

```sh
uv run --env-file .env --directory pipeline thenwhat measure --live
```

A second process, on the machine that holds `MEASURE_DIR`, that reads the day's measurement files from where it last read and draws the view again every four seconds until Ctrl-C. `--once` draws it once and exits, for a script or a quick look. It changes nothing: it adds no totals up, removes no file, and asks no source; its only other reads are two small queries each time it draws, the paused sources and the month's model spend. Without `MEASURE_DIR` it refuses, since there is nothing to watch.

What it shows:

- **Each step, in the last 1, 5 and 15 minutes:** records finished a minute by outcome (done, found nothing, put off, need a fix, failed); the share of the step's time spent running and spent waiting, by wait cause, and the cause it waited on most; model cost a minute and cost a record. A step's cost includes what was measured inside it, such as its decisions, which also show as steps of their own.
- **The runs at work**, with their step, limit and workers. When nothing has been recorded for fifteen minutes it says so, and shows how the last run ended and why, with its counts, even if that was days ago.
- **Records in hand:** by step, how many and how long the oldest has been, with its address key. A record is in hand from the line written when it is taken until its measurement is written. A process holding a record writes a line at least every 30 seconds, so a record whose process has written nothing for 75 seconds is no longer counted in hand: a run that crashed leaves nothing in hand for longer than that. Such records are counted apart, as left in hand by a process that stopped.
- **Paused sources** and outlets the page reader has held, until when; **the month's model spend** against `LLM_MONTHLY_BUDGET_USD`.
- **Measurements that could not be written** today, and lines of the files that could not be read.

The view names the writers whose lines it read and how old the newest line is: only the writer runs steps, so a view on another machine is only as fresh as the files it is given.

**Wait causes.** Time a record spends not being worked on is measured as waiting, under the one cause that held it; the rest is running. The causes are a source's pacing, a source's pause, an outlet's turn or gap, a place among the page reader's requests in flight, a delay before a retry, the turn that settles which claim an article reports, a row another run holds, and `measure_writer`: measurements made faster than they could be written, so the work waited for them. In the measurements they are named: a source's pacing under the source's name (`clinicaltrials.gov`, `reader`); a delay before a retry under `retry:<source>`; an outlet's turn under `outlet_turn`; the claim turn under `claim_turn`; the writer under `measure_writer`. A source's pause and an outlet's gap put a record off instead of holding it, so they show as records put off with their reason, not as time waited; and a row another run holds is skipped, not waited for.

**Run events.** Beside the measurements, the day's file holds lines with a kind of their own, each with its time: a run started (`run_started`: step, limit, workers); a run ended (`run_ended`: why, one of nothing due, the limit, a provider that cannot be asked, the spend ceiling, stopped by the operator, or an error; and its counts, with how many stay due unless the operator or an error stopped it); a source paused (`source_paused`: source, until when); records made due by `thenwhat work requeue` (`made_due`: step, reason, how many). Every measurement a run makes, and its events, carry the run's identifier, one for each `backfill run` however many workers it has. A measurement also carries its outcome's class (final, later, needs_fix, failed) and its reason's code.

**Measurements are written apart from the work.** A worker hands a finished measurement on and goes on; a thread of its own writes them, several at a time, at least once a second, to files it holds open. When they come faster than they can be written, the work waits for them rather than one being dropped, and the wait is measured as `measure_writer`. A write that fails does not stop the work: what was not written is counted, the run's last line says how many (`backfill run` prints it), a `not_written` line is written once writing works again, and `thenwhat measure` reports it for that day while the day's file is kept. If writing never works again before the process ends, the process says so on stderr. With measuring on, a step that asks no source takes no more than a twentieth longer, and no measurement makes a statement to the database (`tests/test_measure_benchmark.py`).

## Audit and publish

This part is done on purpose, by the operator or by an assistant the operator asks. Nothing in the job leads into it.

```sh
thenwhat audit list                 # what is held
thenwhat archive <slug> …           # what is wrong
thenwhat audit clear <slug> …       # the rest
thenwhat audit attach <lead> …      # a listed read that reports the claim it overlaps
thenwhat audit dismiss <lead> … --reason "…"   # one that does not
make publish-data                   # then review, commit, open a pull request, merge
```

The audit itself is in `docs/backfill-loop.md` (steps 3 and 4) and the publish path in `docs/deploy.md`. A decision an assistant makes is recorded with `--as-assistant`. The site changes when the pull request is merged and CI deploys, and not before.

## Install and uninstall

The job runs from the checkout the script is in. Use a checkout that stays on `main` and that no other work switches. In it:

- `.env`, as for any run, with `DAILY_RUN_DATABASE_URL`: the database as this machine reaches it, at its published port on 127.0.0.1, `postgresql+psycopg://thenwhat:<POSTGRES_PASSWORD>@127.0.0.1:<DB_PORT>/thenwhat`. The settings file has no `DATABASE_URL`, because Compose gives its containers their own, and the job runs on the host. `sh scripts/daily-run.sh plist` writes it into the property list as `DATABASE_URL`; the run takes `DATABASE_URL` from its environment first, then `DAILY_RUN_DATABASE_URL`, then a `DATABASE_URL` line in `.env`, and with none of them it stops before its first step and says so. Only where the address came from is logged and named in each summary ("Database address from …"), never the address. Because the property list's `DATABASE_URL` comes first, changing `DAILY_RUN_DATABASE_URL` in `.env` changes nothing until the property list is written and loaded again (uninstall, then install); the summary line shows which one a run used.
- A JSON value in it (`SOURCE_ALLOWANCES`) is in single quotes: `uv run --env-file` loses every line after an unquoted one, and the run refuses to start on such a file, naming the setting.
- `data/link-files`, the folder `scripts/fetch_link_files.py` writes to. On the Mac mini it is a link to the external drive: `ln -s /Volumes/<drive>/…/link-files data/link-files`.

Look at what it would do, then install:

```sh
sh scripts/daily-run.sh --dry-run
```

```sh
(umask 077 && sh scripts/daily-run.sh plist > ~/Library/LaunchAgents/com.thenwhat.daily-run.plist)
```

The property list holds the database address with its password, so it is written readable by you alone (mode 600); `plist` says so when it writes the address. A property list written before this, mode 644, is put right with `chmod 600 ~/Library/LaunchAgents/com.thenwhat.daily-run.plist`.

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.thenwhat.daily-run.plist
```

The property list is `scripts/com.thenwhat.daily-run.plist` with its blanks filled in. Every path comes from one place, the top of `scripts/daily-run.sh`, so the checkout can be moved by writing the property list again. The hour is `DAILY_RUN_HOUR` and `DAILY_RUN_MINUTE`, 04:30 unless set, in the machine's own time. Installing starts no run: the first is at that hour.

Uninstall:

```sh
launchctl bootout gui/$(id -u)/com.thenwhat.daily-run
```

```sh
rm ~/Library/LaunchAgents/com.thenwhat.daily-run.plist
```

The logs, the summaries and the work done stay.

## Pause

```sh
sh scripts/daily-run.sh pause     # no run starts; one in hand finishes
sh scripts/daily-run.sh resume
```

A paused day leaves one line in the log. Pause it while a large backfill uses the database or the month's spend, and before changing the schema.

To end a run in hand, find its process number in `~/Library/Application Support/thenwhat/daily-run/lock/pid` and `kill` it. Each record is committed on its own, so at most the record in hand is lost, and it stays due.

## After a restart, and when the drive is away

- **The job** is a launchd agent of the logged-in user. It comes back by itself at login. A run missed while the machine slept starts when it wakes. A run missed while the machine was off, or while nobody was logged in, is not made up: the next is at the usual hour.
- **The database does not come back by itself.** The `db` service has no restart policy, so after a restart it is down until someone runs `docker compose up -d --wait db`. Until then each run stops at its first step, starts nothing else, and the summary says: "the database did not answer".
- **The external drive.** When `data/link-files` is not there, the run stops before its first step and starts nothing, and the summary says the drive is not mounted. Nothing is fetched to another place. If `MEASURE_DIR` is on the same drive, that is one more reason to stop: a run without measurements has no figures.
- **A lock left behind** by a restart in the middle of a run is taken over by the next run, which says so.

## Why `uv run`, and not Docker Compose

The job runs the pipeline with `uv run --env-file .env --directory pipeline`, from the checkout. Compose was the other choice and is not ready for it:

- The `pipeline` image on the Mac mini is built from an old commit, so it would run old steps. A checkout on `main` runs what is merged.
- A `docker compose run --rm` container loses its measurements when it ends, because `MEASURE_DIR` is not mounted. The fix is pull request 237, which is open.
- Nothing mounts `data/link-files` into the container, so `load-links` would not find the files; and `scripts/` is outside the image, so neither the fetch nor the figures the spend check reads could run there.
- The pipeline is already run this way on this machine, by hand.

To move the job to Compose later, first: merge pull request 237; add a read-only volume for `data/link-files` and a way to run the two scripts in `scripts/` (a mount, or a copy into the image); rebuild the image (`docker compose build pipeline`) and build it again at each update of the checkout; then change the two lines of `scripts/daily-run.sh` that start with `uv run`.

What `uv run` asks in return: `uv` on the job's `PATH` (the property list gives `~/.local/bin` and `/opt/homebrew/bin`), and the quoting of JSON in `.env` described above.

## What is not covered yet

- **Reddit links are not refreshed.** `scripts/fetch_link_files.py` keeps one file per community for the whole period asked and leaves a file that exists alone, so it cannot add a month to one. The daily run takes Hacker News only until the script can.
- **The first `trials` step after the 0027 migration.** It has been run only against a stand-in and recorded fixtures. Its first real run should be by hand, after the migration is applied: `uv run --env-file .env --directory pipeline thenwhat backfill load-trials --trials interventional --changes-only`, to see how many trials a day's changes come to.
- **First real run.** The job has been run only against a stand-in. The first run on the Mac mini should be started by hand (`sh scripts/daily-run.sh`) and its summary read before the job is installed. macOS may ask once whether a background job may read the external drive.
