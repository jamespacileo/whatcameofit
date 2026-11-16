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

A payload is stored once, under its checksum, however many events point to it. The present database stores that record four times, once for each event read from it; 546 MB of event payloads as text will be less once each distinct payload is kept once. How much less is measured in task 2.2.

### 3. What the store holds, and what it never holds

Holds: everything `db/models.py` holds today except HTTP cache rows, which are a device's own, and work ledger entries for the link steps, whose state a run's files and the store's own records of what was scored and read now carry (`file-based-backfill`). A link lead on an unlisted outlet is not held.

Never holds: article text, post text, a post's author, a reader's network address, a reader's identifier, the text a reader pasted, a screenshot. Subscriber emails are out of scope until Phase 2 and then need their own decision on where they live.

### 4. One merge, by natural key

Every write is a **run**: a registration (kind of writer, device or request class, code commit, step versions, time) followed by records in natural-key form, followed by a merge. The merge:

- matches a claim by slug, a source article by claim and address, an evidence event by claim and dedupe key, a registry trial by registry and number, a paper by identifier, an entity by kind and name, a link lead by address key, a share by lead, platform, community and time;
- inserts what is absent and leaves what is present, except as the rules below say;
- never unarchives; never replaces a person's decision with one by a rule, a model, the seed or an assistant; never changes a published time;
- on an evidence event with the same key and different content, keeps the stored one, keeps the new one apart with the reason, and marks the claim awaiting audit. Apart, not as a second pending event: events are unique by claim and dedupe key, which the spike ran into;
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
3. Create the store. Load the dump through the merge path, as one large run, so the migration exercises the same code every later write uses. Left out: `http_cache`, the link steps' `work_entry` rows, and the 2,328,716 leads of kind unknown with their shares, none of which has a score, a read, a label or a link. The 357,964 leads on listed outlets go with their scores, so no device scores them again.
4. Compare: an export from the old database and one from the store are the same, record for record.
5. Point CI's export at the store. Keep the old database read-only for 30 days.
6. Turn on lookup records behind a setting, off by default, after the operator confirms decision 6.

Rollback before step 5 is to do nothing. After step 5 it is to point CI back at the committed snapshot, which is kept until step 6 has run for 30 days.

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
