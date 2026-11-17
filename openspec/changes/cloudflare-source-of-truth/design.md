# Design

## Context

What exists, read on 2026-11-16:

- **Pipeline:** Python 3.12, SQLAlchemy and Alembic over Postgres. `db/models.py` has 29 tables, 14 JSONB columns and 8 array columns. Postgres-specific code: 8 upserts with conflict clauses, 2 skip-locked queue queries, one advisory lock, one regular-expression match.
- **Site:** Astro static build from `site/data/export.json`. CI deploys from the committed `site/data/published-export.json`.
- **Worker** (`site/worker/`): serves the static pages and `/api/lookup`. Its bindings are static assets, the KV namespace `LOOKUP_RESULTS` (structured answers cached 24 hours under a digest of the address), and two rate limiters. It calls ClinicalTrials.gov, Europe PMC, OpenAlex, ROR and a model. It has no database.
- **Extension:** compares the open page's address against the site's `lookup.json`, and asks `/api/lookup` only when the reader asks.

Cloudflare's documentation, read on 2026-11-16 (`developers.cloudflare.com`):

- **D1:** SQLite semantics. 10 GB a database on the paid plan; 2 MB a row or string; 100 bound parameters a query; 100 KB a statement; 30 seconds a query. "Each individual D1 database is inherently single-threaded, and processes queries one at a time." Restore to any minute of the last 30 days. JSON functions, generated columns and FTS5. Reached from a Worker by binding, or over an HTTP API. Import of a SQLite dump up to 5 GB. No change events were found in its documentation.
- **Hyperdrive:** pooling in front of a Postgres or MySQL hosted elsewhere; about 100 origin connections on the paid plan; 60 seconds a statement; included in the Workers plan. Cloudflare offers no Postgres of its own.
- **Queues, Workflows (with a Python SDK), cron triggers, R2 event notifications:** bound to a Worker, so available with either database.
- **Python Workers:** deployed with `pywrangler`; bindings are reachable from Python. Whether a Postgres driver runs in one was not established.
- **Prices:** D1 includes 5 GB, 25 billion rows read and 50 million rows written a month, then 0.75 US dollars a GB-month and 1 dollar a million rows written. R2 includes 10 GB, then 0.015 dollars a GB-month.

The operator is on the paid Workers plan.

The present database, measured on the MacBook Pro on 2026-11-16 by a read-only session there (Postgres 16 in Compose, database `thenwhat`, Alembic revision `0024`, 3,912 MB; a writer, `thenwhat prepare --pending`, was running, so counts moved slightly between queries):

- **Records:** 829 claims (596 approved, 80 pending, 153 rejected; 173 archived; 148 awaiting audit, 34 of those not archived; 400 with a published time), 1,119 source articles, 19,689 evidence events, 43,320 registry trials, 403,886 decisions, 34,835 usage rows.
- **Link leads:** 2,686,680, with 3,296,533 shares. By outlet kind: unknown 2,328,716; general news 354,730; press release 2,509; trade press 725. Every lead on a listed outlet has a triage score. No lead of kind unknown has a score, a read, a label or a link.
- **Largest tables, with indexes:** `link_lead` 1,413 MB, `work_entry` 778 MB, `link_share` 699 MB, `http_cache` 524 MB, `evidence_event` 197 MB, `decision_log` 141 MB, `registry_trial` 62 MB. Everything else is under 50 MB a table.
- **Raw payloads:** `registry_trial` 28 MB as text, largest 11,851 bytes. `evidence_event` 169 MB stored, 546 MB as text; 15 payloads are over 1,000,000 bytes as text and 4 are over 2,000,000. Those 4 are one registry record (NCT04368728, 2,366,561 bytes) stored once for each of four events of one claim.
- **Other databases on that server:** `thenwhat_links` (971,734 leads, no claims, revision `0018`) is the earlier separate load the task notes of `social-link-backfill` describe; six older copies with 84 claims; 22 test databases. None is authoritative.
- **Backup:** a custom-format dump was taken that day on the MacBook Pro, 681 MiB, SHA-256 `709eecae55508f4800f2084d87180fcc3a6f7e18a40a8ba54de63ede8c73057f`. It is on the same disk as the database.

What these figures say about the choice of store, before any spike:

- Three tables need not be migrated at all. `http_cache` is a device's cache. `work_entry` is the work ledger's bookkeeping, most of it for leads that go nowhere. The 2,328,716 unknown leads and their shares are the rows `file-based-backfill` stops making. Together they are about 3 GB of the 3.9 GB.
- What remains is under 1 GB in Postgres. SQLite does not compress, so decisions and events will be larger there; the assistant's estimate is 1 to 1.5 GB in D1 with payloads outside, to be measured in task 2.2.
- A payload over 2 MB exists, so under D1 payloads must be outside the row. Criterion 2 is otherwise met.

Measured the same day (task 2.2), by copying what would migrate into one SQLite file: **504 MB**, with 221 MB of distinct payloads outside it. The largest row is 344 KB. Criteria 1 and 2 of decision 1 are met with room: the database is a twentieth of D1's limit, and the payloads cost nothing in R2 under its included 10 GB. The estimate above of 1 to 1.5 GB was high. Criteria 3 to 5 are not yet tested.

Tested the same day (tasks 2.3 to 2.5), locally:

- **Criterion 3, met.** The merge is 18 fixed statements with one parameter. All 14 scenarios pass on SQLite and the same cases pass on the local D1 engine from a Python Worker.
- **Criterion 4, met.** Topic name matching gives the identical 322 leads by Postgres's regular expression, by the Python rule and by an FTS5 index. The queue of due work is one statement that takes a lease. Nothing has to move to Queues or Workflows to be correct.
- **Criterion 5, met.** A Python Worker reads and writes D1 and runs the merge as a batch; a Python Workflow ran two steps against D1. Run locally and then on a deployed preview: cold start 1.66 seconds, a merge of 22,000 rows in one batch 0.63 seconds, batches of 1,000 statements accepted. The Python SDK needed a private name to send a batch, which is a risk to carry: if it stays awkward, the merge is a few lines of JavaScript in the Worker and Python keeps the processing.

All five criteria are met. What the spike did not cover, and the build must: the migration's full size as one run (about 1.3 million rows, likely to need splitting into several runs), several writers at once, the designed schema in place of the mechanical copy, and how long the Python SDK's private name stays usable. The choice is the operator's and is recorded in task 2.6.

## Goals / Non-Goals

**Goals:**

- One authoritative store, on Cloudflare, that readers' requests, devices and scheduled jobs all write to.
- Every writer goes through one merge with one set of rules.
- What a reader's lookup finds is kept as records, without keeping anything about the reader or any text.
- Nothing becomes public by a new route: the existing rules and the audit hold decide.
- The choice of database is made on measurements, not on preference.

**Non-Goals:**

- Request-time rendering of pages.
- Rewriting status derivation outside Python.
- A second authoritative copy anywhere.
- Deciding how devices process datasets (`file-based-backfill`).

## Decisions

### 1. The store is D1, chosen by a spike with stated criteria

**Decided by the operator on 2026-11-16: D1, with raw payloads in R2** (`docs/adr/0008`). All five criteria below were met; the figures follow them. What follows is kept as the reasoning the decision rests on. Where later sections say "under D1" and "under Postgres", the first now applies and the second describes the fallback.

D1 with raw payloads in R2 is tried first. It is chosen when all of these hold on a copy of the real data:

1. The database, with raw payloads moved out, is under 3 GB. That leaves room under the 10 GB limit for several years at the present rate; the figure is the assistant's and the operator may set another.
2. No row needs more than 2 MB once payloads are moved.
3. The merge of decision 4, written against SQLite, passes the same tests as it would on Postgres.
4. Screening's name matching and the queue of due work can be expressed without the regular-expression operator, skip-locked and advisory locks, or are moved to Queues or Workflows.
5. A Python Worker can read and write the store, and a Python Workflow can run a lookup's steps. If not, the Worker stays JavaScript and only records; see decision 7.

Otherwise the store is a hosted Postgres reached through Hyperdrive, in a United Kingdom or European Union region, and the schema stays as it is.

Why D1 first, although it costs a port: the operator wants the store inside Cloudflare; a Python Worker binds to D1 directly; a device's working copy can be a SQLite file of the same dialect; nothing outside Cloudflare holds a database password; restore to any minute is built in. The architecture is being reworked in any case, so part of the port's cost is paid under either choice.

Why Postgres stays the fallback: the 10 GB and 2 MB limits are hard, the schema and its migrations exist, and concurrent writers are handled by the database with no design effort.

### 2. Raw payloads are objects, with a pointer row

Under D1, an evidence event's or registry trial's raw payload is stored in R2 under a key made from the source, the record's identifier and the fetch time, and the row holds the key, a SHA-256 and the fetch time. The guardrail "store the raw API payload and fetch timestamp for every evidence event" is met by the pair. Under Postgres the payload stays a column.

A registry record with posted results can exceed 2 MB, which is what forces this under D1: the present database holds one of 2,366,561 bytes.

**Decided by the operator on 2026-11-16** (decision 16, and the amendment at the end of `docs/adr/0008`): a payload of 16 KB or less is kept in the store itself, in the `payload` table, and only a larger one is an R2 object. That is every registry listing record (467,064 of them, 642 bytes on average, 12 KB at most) and none of the large records. Half a million tiny objects would otherwise have to be uploaded before the first merge, and a trial's page would need a second service to show its record. `docs/adr/0008` said R2 for every payload and is amended.

**Raised on 2026-11-17 to 524,288 bytes (512 KiB), counted in bytes.** The first cut-over to the preview passed every stage, and 659 of its 810 seconds went on putting 3,211 payloads into R2 one object at a time; at this bound about 37 are objects. The bound is the CHECK on `payload.body` in `store/schema.sql`, which the service reads its own from and the pipeline is held to. It is in bytes because D1's 2,000,000 a row is, and a body's characters can each be four bytes; through the service a payload also travels inside its staged record, escaped, under 1 MB a record, which 512 KiB leaves room for. Migration `0007` makes the table again to change the CHECK (SQLite cannot alter one): the rows are copied aside, the table dropped and made again under its name, and the rows copied back, with foreign keys deferred, because that is the one way D1's local engine accepted on a table that rows reference.

A payload is stored once, under its checksum, however many events point to it. The present database stores that record four times, once for each event read from it; 546 MB of event payloads as text will be less once each distinct payload is kept once. How much less is measured in task 2.2.

### 3. What the store holds, and what it never holds

Holds: everything `db/models.py` holds today except HTTP cache rows, which are a device's own, and work ledger entries for the link steps, whose state a run's files and the store's own records of what was scored and read now carry (`file-based-backfill`). A link lead on an unlisted outlet is not held.

Never holds: article text, post text, a post's author, a reader's network address, a reader's identifier, the text a reader pasted, a screenshot. Subscriber emails are out of scope until Phase 2 and then need their own decision on where they live.

### 4. One merge, by natural key

Every write is a **run**: a registration (kind of writer, device or request class, code commit, step versions, time) followed by records in natural-key form, followed by a merge. The merge:

- matches a claim by slug, a source article by claim and address, an evidence event by claim and dedupe key, a registry trial by registry and number, a paper by identifier, an entity by kind and name, a link lead by address key, a share by lead, platform, community and time;
- inserts what is absent and leaves what is present, except as the rules below say;
- never unarchives; never replaces a person's decision with one by a rule, a model, the seed or an assistant; never changes a published time;
- on an evidence event with the same key and different content, keeps the stored one, keeps the new one apart with the reason, and marks the claim awaiting audit. Apart, not as a second pending event: events are unique by claim and dedupe key, which the spike ran into. "Content" is the fields a status is derived from, not the raw payload: a registry record changes between fetches in ways that say nothing new of the event, and comparing payloads would hold every published claim with a trial on the next refresh (`store-tables.md`, the finding);
- carries the audit mark and never clears it;
- refuses a run whose step versions are older than the store's;
- reports added, matched and conflicting per kind, and applies nothing when those do not sum to what the run handed over;
- is a no-op the second time for the same run.

Where it runs: under D1, in a Worker (the merge is statements in a `batch`, which D1 applies as one transaction), reached by devices over an authenticated ingest address and by the lookup path in-process. Under Postgres, as one database function called by both. The rules and their tests are the same; `specs/ingest-merge` is written to hold for either.

Considered: letting each writer upsert tables directly. The rules would then be whatever version of the code each writer runs.

### 5. A device's credential

A device holds a token for the ingest address, scoped to registering runs, handing over records and reading the reference export. It cannot run arbitrary statements. Tokens are per device and revocable one by one. Under Postgres the same is a role with rights on staging tables and on the merge function only.

### 6. A lookup makes records, and a claim it starts is published by rule

**Decided by the operator on 2026-11-16** (`docs/adr/0009`): of four answers offered, publication by rule with no audit hold. The assistant had recommended drafts held for audit.

- A lookup of an untracked article stores a link lead for the article (address, outlet, title, date) with a share whose platform is `reader` and no community, and registers the registry trials it found in the registry corpus with their payloads.
- It stores its reading of the article (treatment, condition) as a record awaiting the rules, with its scores and reasons, not as a claim.
- The lead then goes through the steps a lead from a file goes through. A claim drafted from it is approved by rule and is **not** held for audit: the next export publishes it, marked as not checked by a person. The audit hold of `docs/adr/0007` stays for claims drafted from a backfill's read batch, which the operator confirmed the same day.
- The operator can list, by day, the claims published from readers' leads. Proposed by the assistant and accepted by the operator on 2026-11-16. A report, not a gate.
- Nothing in the answer the reader sees changes: it is still marked automatic and is still not a status.

What this means: a person who is not the operator can cause a claim to be published by asking about an article on a listed outlet that the rules then approve. The outlet list, the rate limits, the extraction and the rules are the whole of the gate on this route. The lookup itself still creates no claim: the claim is made by processing the lead.

The KV cache stays as a cache. What is new is the durable record beside it.

### 7. Where on-demand processing runs

**Decided by the operator on 2026-11-16: queued, within minutes.** The second shape below, with the Queue's consumer in Python. The reader's answer never waits on it.

The two shapes that were considered:

- **Python on Cloudflare.** A Python Workflow runs the lookup's steps and the same rule code the pipeline runs. One implementation of the rules.
- **Record and queue.** The JavaScript Worker answers the reader as it does now, writes the lead and the found trials through the merge, and puts the lead on a Queue. A Python process, on Cloudflare or on a device, takes it from there. The reader's answer is immediate; the tracker's record follows in minutes.

Not chosen under either: a second implementation of status rules or matching in JavaScript.

### 8. The site stays built, from the store

CI takes a normal export from the truth store, validates it as it validates the committed snapshot today, and builds. The publication gate and "build from the export alone" in `site-publishing` are untouched: the build still sees one file. `site/data/published-export.json` stops being committed; topic publication history stays in the repository.

A build is started on a schedule and when a merge releases claims from audit. Between builds, a reader who asks about an address the store tracks gets the tracked answer from the store through the Worker, so a claim published an hour ago is found by the extension before the next build.

Considered: rendering claim pages from the store on each request. It would replace the site's build, its checks on wording, and its offline build guarantee, for freshness the Worker can give for the one case that needs it.

### 9. Migration

1. The present database is `thenwhat` on the MacBook Pro; a dump was taken on 2026-11-16. Stop the writers there and take a final dump before step 3: `prepare` was running when the first was taken.
2. Spike on a copy (decision 1). Record the outcome as an ADR.
3. Create the store. Load the dump through the merge path, so the migration exercises the same code every later write uses. Not as one run: a batch has 30 seconds, so it is a sequence of runs of about 20,000 records, parents first, each whole (decision 11). Left out: `http_cache`, the link steps' `work_entry` rows, and the 2,328,716 leads of kind unknown with their shares, none of which has a score, a read, a label or a link. The 357,964 leads on listed outlets go with their scores, so no device scores them again.
4. Compare: an export from the old database and one from the store are the same, record for record.
5. Point CI's export at the store. Keep the old database read-only for 30 days.
6. Turn on lookup records behind a setting, off by default, after the operator confirms decision 6.

Rollback before step 5 is to do nothing. After step 5 it is to point CI back at the committed snapshot, which is kept until step 6 has run for 30 days.

### 10. The schema and the merge, as drafted

Drafted on 2026-11-16; the operator took its eight recommendations the same day (decision 16). Nothing is deployed. `store/schema.sql` is the schema, `store/merge.sql` the merge, `store/ingest.sql` what surrounds it, and `store-tables.md` says where each Postgres table goes and why.

What differs from the spike's merge, and why:

- **One staging table for every kind.** A record is staged as its kind, its natural key and a JSON body (`stg`). The spike had a staging table a kind, which at 32 kinds would double the schema. A chunk of records is staged by one statement with one parameter, a JSON array, so a device sends a few large requests and not a thousand statements.
- **Only the first two statements take the run.** They put an accepted run in a one-row table, `merging`; every later statement reads views over it. The spike repeated the run's state in each statement's WHERE.
- **A record whose parent is missing undoes the merge.** It is absent from the view that finds parents, so it is neither stored nor counted, the counts differ from what the run stated, and `merge_guard` fails.
- **Publication comes before archiving in the merge.** Found while writing the preview: the migration brings a claim's published time and its archiving as two actions of one run, and with archiving first the published time of 11 archived claims would have been refused.
- **Decisions have a rank.** A person's over an assistant's over a rule's or the seed's, and at equal rank the later. That gives the same store whichever order two runs arrive in, which "a person's decision wins" alone did not.
- **The operator's commands are records too.** Audit clear, archive, unarchive, merge, rename, accepting or dismissing evidence kept apart, and the export's setting of a published time are staged as `action` records and applied by the same batch. Only a person's action unarchives, and a CHECK holds that.
- **A claim can be renamed or merged without losing a late push.** A renamed claim keeps answering to its old slug (`claim_alias`). A merged claim is archived pointing at the one that stays (`claim.merged_into`), gives it its articles, their statements and promises, and its leads; its own entities, matches and events stay with it; and the claim that stays is due to be prepared again. A device that pushes records for either old slug reaches the claim that stays.
- **Nothing a lookup leaves has a time of day.** Its run's times, its share and its queue entry are dates; CHECKs hold the first two.

The local proof (`store/proof/`, run again on 2026-11-17 against main's revision `0032`): 62 scenarios pass in plain SQLite, the spike's 14 among them. A sample of 55,096 records exported read-only from the working database (407 claims with their records, 5,908 trials, 2,528 leads) loads through the merge in three runs, the slowest 2 seconds on a laptop's disk (4.9 seconds the day before, on a busier machine), and pushing the first run again adds nothing. Projected to the whole database: **1.67 GB, 17% of D1's limit**. It was 1.20 GB on 2026-11-16; the difference is the wider trial record, whose payloads in rows went from 292 MB to 670 MB. The schema and one merge also run on D1's local engine through `wrangler d1 execute --local`.

What the proof does not show: timings on D1 itself, several writers at once, and a merge of 20,000 records on D1 (the spike merged 22,000 simpler rows in 0.63 seconds).

**Reporting without applying** (written later on 2026-11-16, unattended). A D1 batch cannot be undone on request, so a report-only run cannot run the merge and take it back. `store/preview.sql` counts instead: for each kind, the staged records whose parent the store holds or the same run brings, those the store has none of under their key, and the events that differ from an approved one stored. It writes nothing that stays, and `discard_run` then drops the run and what it staged. Two reports that must agree could drift, so the proof takes the preview before every merge it runs and compares it with the merge's own report: every merge of the scenarios (60 when it was written, more since) and the three runs of the sample agree, actions included, and a run whose counts do not reconcile is seen not to. It cannot see what only a CHECK or a foreign key refuses (a reader share with a time of day, a payload never handed over); the merge refuses those. It is not exact, by design, for a run that names one claim by a present and a former slug for the same record, or whose actions depend on one another beyond a clear before a publication.

### 11. The read side

**Stays a static build:** claim pages, topic pages, the landing pages, the method page, the site's own search over claims, and `lookup.json` for the extension. The build sees one export file, as now.

**How the export is taken.** The ingest service gives a holder of the export token a snapshot of the tables an export reads (not leads, not the trial corpus, not decisions), as pages of rows. `thenwhat export` loads them into a SQLite file made from `store/schema.sql` and reads that. So the export's queries are written once, in the store's own dialect; its tests run against the same schema with fixtures and no network; and CI holds a token that can read a snapshot and nothing else, not a Cloudflare API token. Each deployment's export is also kept in R2 under its checksum, which is what rollback uses.

**Served on request, by the site's Worker through its D1 binding:**

| Route | Reads | Kept in cache |
| --- | --- | --- |
| A trial's plain page | One row of `registry_trial` by registry and number, its `payload` row, its states from `registry_trial_status`, and the public claims whose approved events name it (`evidence_event` by source and identifier, joined to `claim_public`) | A day at the edge, by address; a trial changes at most once a day, when the daily job merges |
| Trial search | `registry_trial_fts`, 20 results by rank | An hour, by the words asked for |
| A lookup of a tracked address | `source_article` by address key, joined to `claim_public` | Not cached: one indexed read, and it must see a claim released a minute ago |
| A lookup of an untracked address | Nothing from D1; as now, with the answer cached in KV for 24 hours | KV, as now |

The trial page is rendered by the Worker from the site's own wording module, copied at build as the extension's is, so the site still owns all wording. Whether trial pages are listed in a sitemap, and what they say, belongs to `trial-first-route`; this change gives it the table and the read.

A page served on request is still no new route to publication: `claim_public` is the gate (approved, published, not held, not archived), and a trial's page shows registry facts and public claims only.

Read replication is left off. The database is in the European Union; a reader elsewhere waits longer only on the routes above, and the cache answers most of those.

### 12. The write side

**Two Workers and a queue.**

- **The ingest service**, a Worker of its own, not on the site's hostname. It holds the D1 and R2 bindings and answers only to tokens: a device's (register a run, put a payload, stage, merge, read the reference file, take a slice), the operator's (the same, and actions), and the export's (read a snapshot). It is a few hundred lines with no rule in it: every rule is in `store/merge.sql`, which is bundled into it at build. It is written in JavaScript, because the Python SDK cannot send a batch without a private name (decision 16).
- **The site's Worker** gains the D1 binding. After it has answered a reader, and only when records from lookups are turned on, it registers a run of the kind lookup, stages the lead, the reader share, the trials found and its reading, runs the same bundled merge, and sends the lead's address key to the Queue.
- **The consumer**, in Python, takes work the store says is due (`work_item`, leased by one statement). The Queue's message only wakes it: what is due is read from the store, so a lost message loses nothing, and a lead left due at the spend ceiling is still due next month. For a reader's lead it asks the page reader at home for the article (`docs/adr/0005`, `0006`), reads it, drafts or joins a claim and merges that as a run of the kind consumer. For a pending claim it runs `prepare`: registry search, matching, evidence events, status by the Python rules, approval by rule, and merges again.

**Where `prepare` runs: store-side, for every claim.** A merge leaves each pending claim it added due for `prepare`. A reader's claim is approved without the audit mark; a claim from a backfill's read batch is approved with it. `file-based-backfill` already says the same (its decision 9): a device pushes what it read, and the store prepares it. Its own `prepare` stage only writes the records to push.

**Where the consumer runs.** As a Python Workflow on Cloudflare, provided the pipeline's packages load there (task 8.9 tries that first), each step of a lead a Workflow step, so a slow outlet costs waiting and not CPU, and a failed step is retried by the platform. The spike ran a two-step Python Workflow; it did not run the pipeline's own packages there. If they do not load, the same consumer runs on a device and leases work through the ingest service; it is the same code and the same statements, so the choice can be changed later (decision 16).

**How a device's run folder becomes a merge.** `thenwhat backfill push`:

1. reads the run's files and writes each result as a record in natural-key form, by one mapping function a kind, each tested by a round trip;
2. puts each payload over the bound a row may hold (16 KB when this was written; 524,288 bytes since 2026-11-17, decision 2) to the ingest service, which checks its checksum and stores it in R2 once;
3. splits the records into store runs of about 20,000, parents first, and for each registers the run with its counts and step versions, stages it in chunks of under 2 MB, and asks for the merge;
4. prints each merge's report and marks the folder pushed when the last is merged.

A folder's push is therefore several store runs, each whole or not at all. If it stops between two, the store holds complete records and pushing again finishes it, because a merged run is not merged twice. The bound on a run's size is also what keeps a large push from delaying a reader's lookup: D1 runs one batch at a time, and a lookup's merge waits at most for one run. The bound is to be set from timings on D1 in the preview (task 3.5).

**The daily job** (`docs/daily-run.md`, not yet merged) becomes a writer of the kind daily: it loads what the registry changed and pushes it, and its link files go through a run folder like any backfill.

**The operator's commands** (`audit clear`, archive, unarchive, and the claim merge and rename another session is adding) each become a run of one or more `action` records. The command does not change the store itself; it states the action, and the merge applies it under the rule written above its statement.

### 13. The cut-over

1. **Build in preview.** The store, the ingest service and the merge's tests, with no real records.
2. **Migrate.** Stop the writers, take a final dump, restore it to a scratch database, and push it through the merge as the migration's runs. The report's counts must equal the dump's by kind, less what `store-tables.md` leaves out.
3. **Run in parallel, for at least 14 days.** Postgres stays the source of truth and the site is still built from the committed snapshot. Every device push and every daily job also pushes to the store. Each night:
   - an export is taken from Postgres and one from the store, both written as sorted JSON without the time they were made, and compared claim by claim. They must be the same;
   - the counts of each kind in both are compared;
   - 1,000 trials chosen by number are compared field by field;
   - the day's evidence kept apart is counted, to learn how often content really differs before the hold acts on published claims.
4. **Cut over,** after 7 nights in a row with no difference and no merge refused without a known cause: stop the writers, push what is left, compare once more, point CI's export at the store, and stop committing `site/data/published-export.json`. That day the snapshot file stops being the source. Postgres is made read-only and kept 30 days.
5. **Turn on what is new,** one at a time and each behind its setting: trial pages, records from lookups, the consumer.

### 14. Rollback

- **Before the cut-over:** nothing to undo. The store is dropped and built again.
- **A bad deployment after it:** deploy the previous export again from R2. Each deployment's export is kept there under its checksum.
- **A bad merge:** before a migration run or a run above the set size, the ingest service records D1's restore bookmark on the run. Restoring to it undoes every later write too, so the runs merged since are pushed again from the devices' folders, which is safe because merging is by natural key. What readers' lookups left in between is lost and is left again when the articles are next asked about.
- **The store itself fails us within 30 days of the cut-over:** point CI back at the last committed snapshot and make Postgres writable again. Records made in the store since are exported in natural-key form and loaded into Postgres by the same mapping.
- **D1's limits are reached, later:** the fallback of decision 1. The store's records leave in natural-key form, which is what any store's merge takes.

### 15. Cost a month, at today's volumes

Read from Cloudflare's pages on 2026-11-16 (listed below). The operator already pays 5 US dollars a month for the Workers plan; everything here is counted against what that plan includes.

| What | Included a month | Used at today's volumes | Cost |
| --- | --- | --- | --- |
| D1 storage | 5 GB | 1.67 GB | 0 |
| D1 rows written | 50 million | About 9 million once, for the migration (2.7 million rows, each written again for each index and search index it is in); then under 2 million a month: a daily refresh of a few thousand changed trials, 2,000 leads scored a day, and lookups | 0 |
| D1 rows read | 25 billion | Under 1 billion: a build's export reads about 150,000 rows; a trial page about 10; a lookup's merge a few thousand | 0 |
| R2 storage | 10 GB | 0.37 GB of payloads, and each deployment's export | 0 |
| R2 writes and reads | 1 million and 10 million | 19,723 writes once; a few hundred a day | 0 |
| Queues | 1 million operations | 3 for each reader's lead | 0 |
| Workflows | 500,000 steps, 30 million CPU milliseconds | About 10 steps a lead | 0 |
| Worker requests and CPU | 10 million requests, 30 million CPU milliseconds | Lookups, trial pages, the ingest service. Static pages are not counted | 0 |
| KV | 10 million reads, 1 million writes | As now | 0 |

So the platform adds about nothing to the 5 dollars, and the store-side share of 40 dollars is, in practice, model spend by the consumer. From the working database's usage records: reading a lead and preparing its claim has cost about 0.0025 dollars (10 dollars for some 4,000 leads read, across extraction, matching, statements and readings). **40 dollars is about 16,000 leads a month, or 530 a day.** Readers' lookups have made 247 model calls in all so far. The consumer checks the month's spend by the writers lookup and consumer before each lead and leaves the rest due when the share is used.

What would first cost money, and how much: rows read past 25 billion at 0.001 dollars a million; rows written past 50 million at 1 dollar a million; storage past 5 GB at 0.75 dollars a GB. A second copy of the whole trial corpus written every day would be about 100 million rows written a month, or 50 dollars: the daily job must push what changed, not everything, which `registry_load` exists for.

Pages read, all under `developers.cloudflare.com`: `d1/platform/limits`, `d1/platform/pricing`, `d1/configuration/data-location`, `d1/best-practices/read-replication`, `d1/sql-api/sql-statements`, `r2/pricing`, `queues/platform/pricing`, `queues/platform/limits`, `workflows/reference/pricing`, `workflows/reference/limits`, `workers/platform/pricing`, `workers/platform/limits`, `workers/languages/python`, `kv/platform/pricing`, `workers/runtime-apis/cache`. What they said that the Context above did not have: a query's result is at most 50 MB; a batch counts as one query against the 30 seconds; a jurisdiction of `us` now exists beside `eu` and `fedramp`; each index a row is in counts as one more row written; a Queue's consumer has 15 minutes; a Workflow step has no limit on waiting and 30 seconds of CPU, or 5 minutes when set. The pages do not say whether Python Workers or Python Workflows are still in beta, nor how many statements a batch may hold; D1's local engine refused a compound SELECT of some thirty terms, which its limits page does not mention.

### 16. What the operator decided on the draft

**Decided by the operator on 2026-11-16**, taking the assistant's recommendation on each of the eight questions put at the top of pull request 273:

1. **A payload of 16 KB or less is kept in the store**, in `payload`; only a larger one is an R2 object. `docs/adr/0008` is amended.
2. **Evidence differs when its content differs**, not its payload: the fields a status is derived from, as `content_sha256`.
3. **The `lead_triage` decisions stay local** (420,115 of them). A lead keeps its score and the version that gave it.
4. **The ingest service is JavaScript.** It holds no rule; the rules are the SQL. Processing stays in Python.
5. **The consumer is a Python Workflow on Cloudflare**, if the pipeline's packages load there, which task 8.9 tries before anything is built on it. Otherwise it runs on a device and leases work through the ingest service.
6. **`prepare` runs store-side for every claim**, a backfill's included, as `file-based-backfill` decision 9 already had it. That change's `prepare` stage on the device only writes the records to push; its text now says so, and that a folder's push is several store runs (task 9.5).
7. **CI's export reads a snapshot from the ingest service** into a SQLite file of the store's schema. CI holds no Cloudflare API token for the database.
8. **A merged claim keeps its entities, matches and events**, archived with it. Its articles, their statements and promises, and its leads move, and the claim that stays is prepared again.

### 17. What the operator decided on 2026-11-17

**Decided by the operator on 2026-11-17**, on the five questions at the top of pull request 273:

1. **The preview resources are created now, by the operator.** The D1 database `thenwhat-store-preview`, the R2 bucket `thenwhat-payloads-preview` and the Queue `thenwhat-work-preview`, each in the European Union jurisdiction, which is set at creation and cannot be changed. The commands are in task 3.3. The Queue's jurisdiction is the assistant's addition: its messages carry article address keys.
2. **Deciders have an order:** a person's decision, then an assistant's, then a rule's or the seed's; at equal rank the later one. `specs/ingest-merge` now says so.
3. **Evidence that differs is counted first.** During the 14 days of the parallel run the store is not what the site is built from, so a hold there takes nothing off the site; each night's count of evidence kept apart is recorded, and whether the hold acts on published claims from the cut-over is decided then, with the number.
4. **The cut-over waits** for at least 14 days in parallel and 7 nights in a row of identical exports (decision 13).
5. **Reporting without applying stays as written,** with its two stated limits (decision 10).

### 18. Brought up to main on 2026-11-17

Main gained migrations `0027` to `0032` while this was drafted. What changed in the store's SQL to match:

- **The wider trial record** (`0031`): `registry_trial` has the eleven columns the registry states of a trial's activity and results (dates and their types, whether results are posted, the acronym, the lead sponsor's name), and the indexes the named sets of trials select on. The stored payload grew with them, from 642 to 1,711 bytes on average and 55,425 at most; 32 of the 467,064 are over 16 KB and are R2 objects, the rest stay in rows.
- **Claim merge and rename** (`0032`, `claims/corrections.py`): the store's merge now does what the pipeline's does. What an article reported moves: articles, their promises and statements, leads, the papers, organisations and people an article named, and the names of the intervention that the action lists. What a registry said does not: matches and events stay with the claim that went. A rename can correct the intervention's name, keep the old one as a synonym, give a new slug, or any of these, and leaves the claim's registries due to be searched again. Which names a merge gains is the pipeline's rule, so the action carries them; the store applies them.
- **A claim has one intervention**, held by a unique index as in Postgres.
- **`claim_change`** has no table of its own: a merge or rename is a row of `claim_action` and a former slug is a row of `claim_alias` (`store-tables.md`).
- **Not mirrored:** undoing a merge (`claim unmerge`). Postgres keeps, by row id, every row a merge moved; the store has no such record yet, and its statements are task 4.7.
### 19. The ingest service, as built locally

Built on 2026-11-17 in `store/ingest/`, with no Cloudflare account: a JavaScript Worker (decision 16, point 4) run on D1's local engine. Nothing is deployed. What the build settled, beyond decisions 10 and 12:

- **The first migration is `store/schema.sql`, byte for byte.** The service bundles the statements of `merge.sql`, `preview.sql` and `ingest.sql` unchanged; a generator writes both and a test fails when either drifts from the SQL.
- **The service has one table of its own**, `ingest_chunk`, in a second migration: the checksum of each chunk a run handed over, written in the same batch as the chunk's records. `run.stated_checksum` had no defined meaning; it is now the SHA-256 of the chunks' checksums, sorted and joined by a line feed, and a run whose chunks are not the ones stated is not merged. The table is not part of `store/schema.sql` and holds no record of the tracker.
- **The service sets a run's time**, from its own clock, a day only for a lookup. A writer does not state it, so a lookup's run cannot carry a time of day by mistake.
- **A merge has four outcomes:** merged (again, when it was merged before), refused by the merge, undone by D1 with the constraint named, and not merged because the checksum does not hold. A run that was undone still waits and its writer drops it.
- **A report without applying drops the run**, as `store/README.md` describes, and says what it cannot see.
- **Six kinds of token**, least scope each (`specs/ingest-merge`, "A writer is held to its scope"). The service knows a token by its SHA-256, read from one secret; a secret holds 5 KB, so about 35 tokens.
- **The door's checks**, none of them a rule of the tracker: content type, a stated length, the bounds, a known kind, a natural key, only fields a statement reads, and no string long enough to be an article's text.
- **Bounds**, each under a limit read from Cloudflare's documentation that day (`docs/sources.md`): a chunk of 1.9 MB (D1 binds it as one string of at most 2 MB) or 5,000 records; a run of 20,000 records until timings on D1 set it; a payload of 8 MB; a record of 1 MB. The merge is one batch of 98 statements, the longest far under 100 KB, with one bound parameter; a batch counts as one query against the 30 seconds and against the 1,000 queries an invocation.
- **After a merge the service sends the Queue one message for each step with work due.** The message names the step and nothing else.

What a review of the build changed, on 2026-11-17:

- **The store is given the value the door checked, written out again.** The first build bound the request's own text. JavaScript keeps the last of a key given twice and SQLite reads the first, so one body could pass the door as a rule's publication and be stored as a person's audit clear. The same hole let a long text, a mismatched payload and a person's review past. Bytes that are not UTF-8, half a character and a NUL are refused.
- **A device's token records a rule's or the seed's decision only**, and hands over an approved claim only with its audit hold, unless the store already holds the claim approved and released. A script's decision is never recorded as a person's, so a person's or an assistant's travels with the operator's token alone. This closes the choice the first build left open.
- **One form of time:** `YYYY-MM-DDTHH:MM:SS.ffffff+00:00`, the form the pipeline's records already have, or a day alone. The merge compares times as text. The door refuses any other form and the service writes its own times this way. `store/merge.sql` still writes `run.merged_at` to the second with `Z`; nothing compares it.
- **A field is taken only on a kind whose statements read it.** The generator derives each kind's fields from the SQL. A lookup's token may not send a lead's `claim_slug`.
- **Registering a run again writes nothing**, and is refused when it differs.
- **A trial's joined arm names may hold 20,000 characters.** Other fields a source can make long are to be named from a measurement of the working database.

All 62 of the proof's scenarios pass through the HTTP routes on the local engine. Where a scenario hands over a person's decision, or an approved claim with no hold, it travels with the operator's token. Where the proof wrote SQL directly, the test asks the service: a person's rejection is pushed as a record, a run that was undone is dropped by its writer, and the queue's and a slice's times are the service's clock. What this does not show is what decision 10 already lists: timings on D1 itself and several writers at once.

### 20. The store in two tiers

**Decided by the operator on 2026-11-17** (`docs/adr/0010`), after the whole working database was built into one store file (5 min 47 s, 2,239 MB) and loaded into the preview D1 in full the same day:

- **The hot tier is loaded into D1:** the tables something on Cloudflare reads. These are what the export of the site from the store reads (claims, their actions and aliases, articles, promises, statements, entities, matches, terms, events, conflicts, failure flags, trial reads, a source's records, decisions, outlet icons, the claims' search), the merge's and the ingest service's own tables (runs, staging, the report, the guard, work items and slices, deployments), and the count of unlisted domains a lookup keeps.
- **The bulk tier is one SQLite file kept in R2 and not loaded into D1:** registry trials with their states, search and loads, article leads, link leads with their shares, links, labels, search and a lookup's readings, the registry route's ledger, model spend and the measurements. Restoring it is downloading the file.
- **A payload goes with what points at it.** An event's, a conflict's and a source record's payloads are hot; a trial's are bulk; a payload both point at is in both. A payload object over 16 KB goes to the tier's folder of objects.
- **No hot row references a bulk row.** The schema's foreign keys run from bulk to hot only (a lead to its claim and article, an article lead to its trial, a measurement to its claim), and a hot record that names a bulk one names it by text: an event, a match and a trial read name their trial by registry and identifier, a decision names what it decided by natural key. `pipeline/tests/test_store_tiers.py` holds this against the schema.
- **Verification is by checksum, not by reading rows back.** For each table, one SELECT of aggregates (`thenwhat store checksum`, `pipeline/src/thenwhat/store/tiers.py`): rows, and for each column the values held, their total bytes and the code points of each value's first, middle and last character. D1 answers it with one row from one scan and no sort; the same statement on the store file gives the same row, and both are hashed the same way. It shows that a load arrived whole. It does not detect two rows swapping values, or a change inside a value that keeps its length and those three characters.
- **After the cut-over, the bulk file is the truth for bulk kinds, with one writer: the daily job.** The hot kinds of a day go through the ingest service to D1 as before (`thenwhat backfill push`, hot kinds only unless `--every-tier`: a bulk kind's parents are not in D1, so its run would not reconcile). The bulk kinds go into the bulk file on the device, by the same `store/merge.sql` (`thenwhat store merge-bulk`). The bulk file keeps a copy of the hot rows bulk rows hang from (claims, their aliases and actions, articles: `REFERENCE` in `tiers.py`), refreshed by the same merge, so its foreign keys hold.
- **A day ships as a delta beside the last build, not as a new build.** `merge-bulk` writes the day's records, gzipped JSON lines in the form a writer stages, as one object kept beside the last bulk build; a restore downloads the build and replays its deltas in order (`thenwhat store apply-delta`). A typical day, read from the working database on 2026-11-17 (seven-day averages): about 810 new leads and 940 shares, a few kilobytes each gzipped, and the trials the registry changed, in the thousands once the daily job pushes only those (task 7.3), at about 1.7 KB each: a delta of a few megabytes, against 1.9 GB for the whole file. A new whole build is taken when the deltas since the last one pass a tenth of its size, or weekly, whichever is sooner.
- **What a lookup creates of a bulk kind is an inbox in D1.** A reader's lookup stages leads, shares, trials and readings into D1's own copies of those tables, which hold nothing else. The daily job reads them through the ingest service, merges them into the bulk file, and clears them from D1 (task 4.9). Until then, a lookup's lead or trial is not matched against the bulk file's, and a lookup's share, label or reading whose lead is only in the bulk file does not resolve and its run is undone: the lookup answers the reader, and its record waits for the next lookup or the daily fold.
- **A hot row that needs a fact of a trial or a lead carries it itself.** An event carries its trial's payload and identifiers; a claim page's trial title, sponsor and status come from that payload (the export reads nothing of `registry_trial`).

What this costs, against decision 1's one source of truth:

- **Two places, not one.** D1 is the truth for the hot tables; the bulk file in R2, with its deltas, for the bulk ones. A loss of the device that writes the bulk file loses at most the deltas not yet uploaded.
- **One writer for the bulk file.** Only the daily job merges into it. Two devices cannot write bulk records at once; a device's bulk records reach the store through Postgres and the daily job.
- **No Worker query over leads or stored trials** until a table is moved to hot.
- **Going back is one full load.** `thenwhat store build --tier all`, dumped and loaded, put the whole store in the preview D1 on 2026-11-17 in about 9 minutes.

- **The bulk tier cannot be queried from a Worker.** A trial's page served from the store (phase 5, tasks 7.1 to 7.3) needs `registry_trial` in D1; those tasks now begin by moving it to the hot tier, which the full load of 2026-11-17 showed fits.
- **A reader's lookup still stages leads, shares and readings into D1.** After the cut, D1's `link_lead`, `link_share` and `lead_reading` hold only what lookups add, and the bulk file holds the history. A lookup of an article whose lead is only in the bulk file is answered as for a new lead. Promoting `link_lead` to hot reverses this.
- **A claim merge in D1 moves the leads D1 holds**, not those in the bulk file; the next bulk build carries the change from Postgres.
- **A full D1 load remains possible:** `thenwhat store build --tier all` writes the one whole file, which was loaded into the preview D1 in full on 2026-11-17.

## Risks / Trade-offs

- **D1's limits are reached later.** → Criterion 1 leaves headroom; payloads are already outside; the merge and its tests hold for Postgres, so moving stores later is a data migration, not a redesign.
- **Readers can now cause writes.** → The existing per-reader and overall limits apply before any write; a lookup writes a lead and found trials only; nothing it writes is public without the rules and the audit.
- **Junk addresses fill the store.** → A lead from a reader is kept only when its outlet is listed, as for a lead from a file; the rest are counted, not stored.
- **A stored record of what was asked could identify a reader.** → Nothing of the request is stored but the article's own public facts; no time finer than the day is kept on a reader's share; see `specs/on-demand-records`.
- **The store is no longer on the private network.** → It is reached only through bindings and the ingest token, never served publicly as a database. This still needs the operator's ADR.
- **Two rule implementations drift.** → Decision 7 allows none.
- **The spike cannot run because the real database is not found.** → Then it runs on the registry corpus and the Hacker News leads reloaded from files, and criterion 1 is an estimate marked as one.

## Open Questions

- **Answered on 2026-11-16: where the present database is.** `thenwhat` on the MacBook Pro, confirmed there by its counts and by being the only database at the newest revision; see Context. The figure of 971,734 leads in earlier notes was the separate database `thenwhat_links`.
- **Is the registry-first route's part of `work_entry` migrated?** The link steps' entries are not. Whether the `news_search` entries for the 43,320 trials are needed depends on whether that route keeps its ledger; not yet looked at.
- **The dump sits on the same disk as the database.** A second copy elsewhere is the operator's step.
- **Answered on 2026-11-16:** a claim a reader's lookup starts is published by rule with no audit hold (decision 6, `docs/adr/0009`).
- **Answered on 2026-11-16:** on-demand processing is queued and finishes within minutes (decision 7).
- **Moot:** the 3 GB criterion was met at 504 MB.
- **Answered on 2026-11-16:** the D1 database and the R2 bucket are created in the European Union jurisdiction. Read from Cloudflare's documentation that day: the jurisdictions offered are `eu` and `fedramp`, there is none for the United Kingdom alone, and a jurisdiction is set when the database is created and cannot be added or changed afterwards.
- **Answered on 2026-11-16:** the daily list of claims published from readers' leads is wanted (decision 6).
- **Where does the Queue's Python consumer run:** as a Python Worker on Cloudflare, or on a device? The spike showed the first works; its limits under a real read (a page fetch through the reader at home, a model call) were not tested.
- **Which Postgres provider, if the fallback is taken.** Prices were read; terms were not.
- **How a source's allowance is shared** between a device and the store-side consumer, which both ask the registries. Each keeps its own count today (`source_allowance_use` stays local); the consumer's share of each allowance is a setting until something better is needed.
- **How often an approved event's content differs** under one key between two fetches. Counted during the parallel run (decision 13).
- **Answered on 2026-11-16:** a merged claim's entities, matches and events stay with it, and the claim that stays is prepared again (decision 16). The session adding the pipeline's command is told in the shared notes.
- **Answered on 2026-11-16:** reporting without applying is counted by `store/preview.sql`, not tried (decision 10).
