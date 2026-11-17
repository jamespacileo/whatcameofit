# Deploying What came of it?

The public site is https://whatcameofit.com, served by the `thenwhat` Cloudflare Worker in the Palladio account. Source code is public at https://github.com/jamespacileo/whatcameofit. The pipeline, review database, local preview and provider keys stay on the private machine.

## Normal publishing workflow

Changes to `main` run the complete test suite and a public deployment rehearsal in GitHub Actions. Only after those pass does GitHub deploy production and check the live home, method, sitemap and claim pages. Pull requests run the checks and get their own preview (below); they never change production. The Actions page also offers a manual run for `main`.

To publish newly approved claims, run:

```sh
make publish-data
git diff -- site/data/published-export.json
```

The icons command saves logos for newly encountered publishers. Use `thenwhat icons --retry-missing`
inside the pipeline container to retry publishers that previously returned no usable image.
Unavailable icons use a letter tile; pages never fetch logos from third-party hosts.

The site build regenerates browser, launcher and share-brand assets from the canonical SVGs.
Brand URLs include an artwork revision so returning readers receive updated icons.

Commit `site/data/published-export.json`, `site/data/published-topics.json` and `site/data/published-trials-listing.json` (the trial listing, staged by the same command; see `docs/trial-records.md`) with the intended changes, then push to `main` (or merge a reviewed pull request). This snapshot is the only data GitHub publishes. Since the auto-publish decision (ADR 0001, 13 November 2026) it holds every approved, unarchived claim, whoever decided it; each says whether a person checked it. Assistant decisions are never converted to human approvals. Take a claim down with `thenwhat archive <slug> --reason`, then run `make publish-data` again. Staging preserves the topic history so future builds cannot silently break a published topic address.

Staging first asks the running pipeline for a normal export with preview mode disabled. It validates the export and replaces the snapshot atomically. Invalid JSON, a preview or an empty export leaves the previous snapshot unchanged. GitHub cannot reach the local database; database changes alone therefore never publish anything.

## Pull request previews

Decided by the operator on 16 November 2026 (change `pull-request-previews`). Every pull request from a branch of this repository gets its own copy of the site on its own Worker, `thenwhat-pr-<number>`, at `https://thenwhat-pr-<number>.<account subdomain>.workers.dev`. The `Pull request preview` workflow publishes it when the pull request opens, replaces it on every push, and deletes the Worker when the pull request is merged or closed. One comment on the pull request carries the address, links to the main pages and files, the claims the pull request adds, the commit, the build log and the Worker's dashboard page. Every run and re-run edits that same comment (`site/scripts/pr-preview-comment.mjs`); a failed build and the removal are written into it too. The workflow does not wait for the tests, so the address is usually ready before `Tests and build` finishes; a preview existing says nothing about whether the checks pass.

How a preview is kept quick (change `fast-ci-and-deploy`, measured on pull request 267 on 16 November 2026):

- **A copy says what it was made from.** `site/scripts/build-key.mjs` hashes every tracked file under `site/` except the tests and notes, with the settings the build and the Worker are given. The copy serves that key at `/build-key.txt`. The workflow's first step, `make pr-preview-state`, reads it back: when it equals this commit's key, nothing is installed, built or sent, and only the comment is edited. Such a run takes about 11 s. A setting the build newly reads must be added to `SETTINGS` in that file.
- **Drawn card images are kept.** Drawing the three cards of every claim was 76 s of an 82 s build. `site/src/lib/card-image.ts` keeps each drawn card in `site/.cache/cards` under the hash of the description handed to the renderer, its size, the fonts and the renderers' versions, so a build draws only cards that changed. `CARD_STORE=off` draws everything; `CARD_STORE=<folder>` keeps them elsewhere. The built files are byte for byte the same with and without the store.
- **GitHub keeps the cards and the installed dependencies between runs** (`site-cards-*` and `site-deps-*` in the repository's Actions caches). A pull request reads its own and those kept by runs on `main`; `CI and deploy` keeps them on `main`. Deleting them costs one slow run and nothing else.

With all three, a push that changes the site republishes in about 50 s: 11 s to start the job and restore the stores, 20 s to build, 9 s for Wrangler to send, 2 s for the comment. Before, it was about 146 s.

A preview differs from production in these ways, all set in `site/wrangler.preview.jsonc` and `site/scripts/pr-preview.mjs`:

- It is built from the pull request's own `site/data/published-export.json`, as a public build for the production address, so canonical links, feeds and embed snippets name `whatcameofit.com`.
- Every file is sent with `X-Robots-Tag: noindex`.
- It has no registry search: no model settings, no `OPENAI_API_KEY`, no `OPENALEX_API_KEY`, no `LOOKUP_RESULTS` namespace. `/api/lookup` answers "not set up" and can spend nothing.
- The trial reader works, with its own rate-limit counter and no saved copies.
- Worker logging stays off.

A pull request from a fork, or from Dependabot, gets no preview: GitHub gives those runs no Cloudflare token. A data pull request's preview shows its claims at a public address before the merge, as the pull request itself already does.

The preview uses the same `CLOUDFLARE_API_TOKEN` repository secret as production, which any workflow run on a branch of this repository can read. Only people with write access can push such a branch. A separate token limited to Workers Scripts, stored in its own GitHub environment, would narrow this; it is not set up.

To publish or remove one by hand:

```sh
PR_NUMBER=12 make pr-preview-check   # builds and rehearses; publishes nothing
PR_NUMBER=12 make pr-preview
PR_NUMBER=12 make pr-preview-state   # says whether the published copy is already this commit's
pnpm --dir site exec wrangler delete --name thenwhat-pr-12 --config site/wrangler.preview.jsonc
```

`pnpm --dir site exec wrangler deployments list --name thenwhat-pr-12` shows what a preview is serving. A Worker named `thenwhat-pr-*` whose pull request is closed is a leftover and can be deleted.

## GitHub configuration

The repository uses a `production` environment restricted to `main`. Production deployments are serialized; a superseded revision is skipped when it reaches the deployment queue. GitHub Actions are pinned to reviewed commit revisions; Wrangler is pinned in `site/package-lock.json` and installed with `npm ci`. Main requires the `Tests and build` check and disallows force pushes and deletion; repository administrators retain GitHub's standard bypass.

Set these repository values in Settings → Secrets and variables → Actions:

| Kind | Name | Value |
| --- | --- | --- |
| Secret | `CLOUDFLARE_API_TOKEN` | The dedicated production deployment token; never commit it |
| Variable | `CLOUDFLARE_ACCOUNT_ID` | `ee6dc8763af66b85cf2333e1ea5a4d9f` |
| Variable | `SUGGEST_URL` | `mailto:suggest@whatcameofit.com` once forwarding is active |
| Variable | `CORRECTIONS_URL` | `mailto:corrections@whatcameofit.com` once forwarding is active |
| Variable | `CHROME_STORE_URL` | The extension's Chrome Web Store listing, once it is published there |
| Variable | `SAFARI_STORE_URL` | The extension's Mac App Store listing, once it is published there |

The token permits Workers Scripts editing in Palladio, Workers Routes editing for `whatcameofit.com`, and Zone read for that domain. It expires on 12 November 2027; replace the encrypted GitHub secret before then. It has no billing, database, model-provider, or email permissions.

Cloudflare's [GitHub Actions guide](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/) documents deployment credentials. Keep deployment credentials out of workflow logs, and out of any run a fork's pull request starts.

## Local checks and emergency deployment

Wrangler is a project dependency; a global install is unnecessary.

```sh
make check
make deploy-ci-check # rehearses the committed snapshot; needs no private database
make deploy-ci       # publishes that snapshot; needs Cloudflare authentication
```

For local authentication, run `pnpm --dir site exec wrangler login` and verify with `pnpm --dir site exec wrangler whoami` before deployment. `make deploy-check` and `make deploy` remain available: both first export directly from the running local pipeline. `SITE_URL` defaults to https://whatcameofit.com and can be overridden explicitly.

Never run raw `wrangler deploy`: it bypasses the public-data checks and could publish an old preview build. ("Preview build" here means a build of unreviewed data, not a pull request preview.) All supported deploy targets validate the export, build it afresh as a public site, and check its sitemap and preview flag before invoking Wrangler.

## Domain and contact settings

`site/public/_headers` sets the response headers Cloudflare sends with every page and file: no content-type sniffing, a limited referrer, and HTTPS only for a year. It sets nothing that forbids framing, because the embed is made to be framed.

Cloudflare owns the apex custom-domain attachment and certificate. Enable Always Use HTTPS. Configure `www` as a proxied DNS record with a permanent redirect to `https://whatcameofit.com`, preserving paths and query strings. Do not enable an additional Cloudflare Git build pipeline alongside GitHub Actions, which would cause competing deployments.

`suggest@whatcameofit.com` and `corrections@whatcameofit.com` forward to the verified operator inbox. Configure their GitHub variables only after Email Routing reports active rules. Forwarding receives mail; it does not provide an outgoing mailbox.

No added reader analytics are installed. Cloudflare retains operational request/error counts independently of Worker logging; [Cloudflare metrics documentation](https://developers.cloudflare.com/workers/observability/metrics-and-analytics/) explains those counts. The method page states this, and Worker observability remains disabled.

## Optional registry search

Public searches use the dedicated OpenAI project **whatcameofit production** in Abstract Meld LTD (`proj_EAXw8QLftFeaYWLL2qGX51xA`). Its monthly hard spend limit is **$13**, with alerts at 80% ($10.40, also sent to the operator inbox) and 100%. Only the configured model is allowed; Fast and Ultrafast service tiers are disabled. Provider limits are 30 requests and 100,000 tokens per minute. The project is separate from the private pipeline and its local usage ledger.

OpenAI's [hard-limit documentation](https://developers.openai.com/api/docs/guides/spend-limits) explains that affected requests fail once tracked spend reaches the cap and resume at the next monthly reset. Enforcement has a propagation delay, so final usage can slightly exceed the setting; this is not an exact-dollar guarantee. Cloudflare's per-reader and per-location minute limits slow bursts but are not a global money cap.

Store the dedicated project's `OPENAI_API_KEY` only as a Cloudflare Worker secret. Do not use the private pipeline's key or put a key in source, GitHub variables, build output or the extension.

The production key was installed on 12 November 2026 and expires on 12 November 2027. It is restricted to Chat Completions requests and Decisions writes; all other API permissions are disabled. Replace the Worker secret before expiry. Organization data-sharing options were confirmed disabled at enablement.

Set these GitHub repository variables, which CI passes to both deployment rehearsal and production:

| Name | Production value |
| --- | --- |
| `LLM_MODEL` | `openai:gpt-6-luna` |
| `CONTACT_EMAIL` | `james@abstractmeld.com` |
| `DECISION_BACKEND` | `openai-decisions` |

The model remains configurable; changing it also requires updating the project's allowed models and reviewing cost and quality. Chat completions explicitly use standard pricing, disable stored completions, and cap generated tokens at 2,048 for reading and 4,096 for scoring a batch. Both model endpoints have a 30-second timeout and no automatic retries. A timed-out request may still be billed. An exhausted provider spend limit becomes a plain monthly-allowance message; static reviewed pages remain available.

Before first enablement, confirm the project cap, allowed model, disabled data sharing, secret, current privacy disclosure and one live lookup. To switch off new public searches, clear the GitHub `LLM_MODEL` variable and rerun the main workflow. Removing the Worker's `OPENAI_API_KEY` secret also immediately prevents paid calls. Never raise the spending limit automatically to recover from a budget refusal.

Production enablement was verified on 12 November 2026 after [deployment run 43317512661](https://github.com/jamespacileo/whatcameofit/actions/runs/43317512661) passed. The public index advertised the live endpoint and contained only the single human-reviewed claim. Synthetic non-medical text returned no treatment; a synthetic semaglutide lookup returned the explicitly named STEP 1 trial (NCT03548935) first. Both responses used `Cache-Control: no-store`. No article text or API credentials were retained in the verification record.

The existing local deploy script also accepts optional `LLM_BASE_URL` and `DECISIONS_MODEL`; the production workflow deliberately uses OpenAI's normal endpoint and the same allowed model for both calls.

## Renaming or retiring a topic after launch

A published topic address must keep working. To rename or retire a vertical:

1. In `pipeline/src/thenwhat/claims/verticals.py`, change or remove the vertical, and add its old slug to `RETIRED_VERTICALS` with the vertical that replaces it, for example `{"eyes-and-ears": "sight-and-hearing"}`. `make check` refuses a retired slug that is still configured, or one whose successor does not exist.
2. Move the claims filed under the old slug with `thenwhat claim edit SLUG --vertical NEW`.
3. Export again and build (`pnpm --dir site run build`). The build writes `site/dist/_redirects` with a permanent redirect from `/topic/OLD` to `/topic/NEW`. It fails, naming the slug, when `published-topics.json` lists a topic that is neither current nor retired.
4. Run `make publish-data`, commit both publication files, and push to `main`.

The initial publication history preserves all old topic addresses, including empty topics. `/topic/dental-regeneration` now redirects to `/topic/mouth-and-teeth`. The former transplant topic split across several organs, so its address redirects to the topic directory instead of one organ.


## Rollback

Revert the faulty source/data commit on `main` and push. GitHub tests and republishes the reverted version. For an immediate rollback, run `pnpm exec wrangler rollback` from `site/` after signing in, then revert the source commit so the next automatic deployment preserves the fix. Keep the previous committed public snapshot for data rollbacks. Do not delete the Worker to roll back.

## OpenAlex and ROR

`OPENALEX_API_KEY` is installed in the ignored root `.env`, `site/.dev.vars`, the GitHub repository's encrypted Actions secrets, and the deployed `thenwhat` Worker. `make lookup-dev` copies it into the local Worker settings. It is never a public build variable. Wrangler preserves the existing Worker secret across normal CI deployments; the deployment does not print or pass the key as an argument. ROR needs no key or registration while its client-ID registration is paused.

The public `/api/lookup` response adds optional `research` with papers, organisations and per-source availability. Both use the existing `LOOKUP_RESULTS` KV namespace with a separate metadata prefix and seven-day TTL. Two keyword queries at most, ten papers each, and three explicit organisation names at most; no pagination, full text, embeddings or extra OpenAI calls. Bibliographic relevance and organisation identity do not change claim status. Older extensions safely ignore the additional field; extension 0.9.0 shows it.

OpenAlex must remain a free account with no prepaid credit or automatic top-up. Each uncached charged request checks `/rate-limit`, the reported search price, <=$1 daily budget, $0.01 reserve and zero prepaid balance. Unknown limits or paid credit disable literature queries. The provider's account-wide cap handles concurrency; KV is not a hard money counter. 402/exhaustion pauses until UTC reset; 429 pauses per Retry-After (60 seconds to one day). Cached metadata remains usable. ROR is free, bounded and cached; provider 429 is respected. Missing keys or enrichment outages leave trial lookup available. See `docs/sources.md` for current source terms.

To disable paper enrichment, remove `OPENALEX_API_KEY` from the Worker (and local environment for local runs). Do not increase budgets to recover from a refusal. The unrelated private-pipeline research review workflow remains tracked in `openspec/changes/related-research/tasks.md`.

## Progressive extension lookups (Safari 0.9.3)

`/api/lookup` accepts `stream: true` for an opt-in `application/x-ndjson` response. Each line is a JSON event: `{type:"core", result, timings}` once all clinical search and scoring are complete, then `{type:"complete", result, timings}` with optional research enrichment. A failure is `{type:"error", error, status}`; a streaming response can therefore have HTTP 200 and still contain an explicit error event. Cache hits and preflight refusals may remain ordinary JSON. Existing JSON clients retain their complete response shape.

Timing events contain numeric durations/completion offsets only, with no article text or identifiers. Ordinary completed responses expose timing fields through `Server-Timing`. No request logging or telemetry service is introduced. Cache version 2 excludes older results and permits completed independently public non-treatment identifications; unfinished streams and answers with unchecked papers remain ineligible. The extension reuses complete local answers for unchanged content, keeps shared hits locally, and avoids automatic screenshots of substantial ordinary text articles while retaining image-dependent fallback and the explicit Screenshot action.

`read_ms`, `papers_ms`, `score_ms`, and `research_ms` measure each stage from its own start. `registry_ms` sums active registry calls, excluding time waiting in the lookup queue. Stages overlap, so their durations must not be added to estimate latency. `core_ms` and `total_ms` are elapsed milestones from lookup start, not stage durations.

## The store on D1 (preview)

The store is a D1 database, an R2 bucket and a Queue, reached only through the ingest service in `store/ingest/` (`store/ingest/README.md`). Nothing below touches the site. The repository carries the resources' names only. A database's id is written by `node store/ingest/scripts/preview-config.mjs` into `store/ingest/wrangler.preview.jsonc`, which is git-ignored, and is never printed.

### How the resources were created

Created by the operator on 17 November 2026 with Wrangler 4:

| Resource | Preview | Production | Jurisdiction |
| --- | --- | --- | --- |
| D1 database | `thenwhat-store-preview` | `thenwhat-store` | `eu`, set at creation and not changeable afterwards |
| R2 bucket | `thenwhat-payloads-preview` | `thenwhat-payloads` | `eu`, set at creation |
| Queue | `thenwhat-work-preview` | `thenwhat-work` | created without the flag (see below) |

The commands that create the preview's three, as Wrangler 4.161.0 takes them (the operator's own commands were not recorded here):

```bash
wrangler d1 create thenwhat-store-preview --jurisdiction eu
wrangler r2 bucket create thenwhat-payloads-preview --jurisdiction eu
wrangler queues create thenwhat-work-preview
```

**Queues and jurisdiction.** `wrangler queues create` has a `--jurisdiction` flag, but Cloudflare's documentation, read on 17 November 2026, lists no values for it and says nothing of the European Union for Queues. The two Queues were created without it. A message on the Queue names a step with work due and nothing else (no record, no address, no time), so no data of the tracker rests in a Queue. Whether to recreate them with the flag is the operator's decision once Cloudflare documents its values.

### The deployment check: read the jurisdiction back

Before any record is written to a database, read its jurisdiction and stop unless it is `eu`:

```bash
cd store/ingest && node scripts/preview-config.mjs
npx wrangler d1 info thenwhat-store-preview --json
```

The answer's `jurisdiction` must be `eu`. Read back on 17 November 2026 for `thenwhat-store-preview`: `eu`. Cloudflare's documentation does not promise that `d1 info` shows the field, so if a later Wrangler leaves it out, treat that as a failed check.

### Schema

```bash
cd store/ingest
npx wrangler d1 migrations apply STORE --remote --config wrangler.preview.jsonc
```

Applied to the preview on 17 November 2026: `0001_store_schema.sql` (which was `store/schema.sql`, byte for byte, that day; since then the schema is the sum of the migrations, and `0006` adds the tables of the progressive trial load) and `0002_ingest_service.sql`.

### Two tiers (decided by the operator on 17 November 2026)

The store is in two tiers. Which table is in which is stated in `store/store-tables.md`, not here.

- **Hot:** what the site's export, the lookup service and the extension read. It is loaded into D1.
- **Bulk:** registry trials, leads, shares, link tables, work entries, usage, measures and their payload rows. It ships as one SQLite file in R2 under `bulk/<build id>/` and is not loaded into D1.

`thenwhat store build` writes a hot file and a bulk file. The migrations still create every table in D1, so the bulk tables are there and empty. What that means for the ingest service today:

- None of its own routes reads a bulk table. `/work/*` reads `work_item`, `/slices/*` reads `work_slice`, and the audit-hold check reads `claim`.
- A record of a bulk kind that a merged run hands over is also kept in the service's `inbox`, for the daily job to fold into the bulk file and clear (`GET /inbox`, `POST /inbox/clear`). The migrations now include `0003_inbox.sql`, `0004_inbox_folded.sql` and `0005_inbox_fold.sql`: apply them before the service is deployed.
- The merge still writes whatever kind it is handed. A reader's lead or a found trial is added to D1's copy of the table and is not matched against the bulk file, so a lead the bulk file already has is added again in D1.
- A record whose parent is only in the bulk file is not resolved: a share, label or reading of a lead, or an article lead of a trial, that the run does not also carry. The run's counts then do not reconcile and the merge is undone. A run must carry such a parent itself until the merge is taught the tiers.

### Cut-over: one command

The cut-over is not done by hand. One script holds the order, for this machine, the preview and production (`store/ingest/scripts/cutover.mjs`). On 17 November 2026 the steps run by hand went out of order three times; the hand sequence that stood here is gone.

```bash
make store-rehearsal STORE_DIR=<a build's folder>                                  # this machine, nothing sent
make store-cutover ENV=preview STORE_DIR=<a build's folder> ARGS="--dry-run"       # the plan, nothing run
make store-cutover ENV=preview STORE_DIR=<a build's folder>
make store-cutover ENV=production STORE_DIR=<a build's folder> CONFIRM=thenwhat-store
```

A build's folder is what `thenwhat store build` leaves: `store.hot.sqlite`, `store.bulk.sqlite`, `payloads/hot`, `payloads/bulk`, and `checks.json` (made by the command when it is not there). The stages, in order; the first that fails stops the run and is named:

| | Stage | What it does |
| --- | --- | --- |
| 0 | privacy | `thenwhat store prove-no-people` on both files and both payload folders. If it fails or cannot be run, nothing is sent. |
| 1 | jurisdiction | The database's jurisdiction is read back and must be `eu`; the bucket must be found in `eu`. |
| 2 | config | The configuration for the environment, with the database's id looked up by name, in a git-ignored file. Production's is removed at the end. |
| 3 | migrations | All of `store/ingest/migrations/`. |
| 4 | empty | The store must hold no row. With `ARGS="--replace"` a preview store is emptied, or replaced when it holds over 200,000 rows. Production is never emptied: the command stops and prints the commands for the operator. |
| 5 | bookmark | D1's Time Travel bookmark, written under `~/Library/Application Support/thenwhat/store/bookmarks/`. |
| 6 | dump | The hot file as SQL (`dump-for-import.mjs`), and that SQL replayed strictly on this machine (`check-dump.mjs`). |
| 7 | import | The files, in order, counted against the manifest (`import-folder.mjs`). |
| 8 | checksum | Every hot table in D1 against the build's checks (`checksum-d1.mjs --checks`). No row is fetched back. |
| 9 | payloads | The payload objects of both tiers (`upload-payloads.mjs`), twenty read back. |
| 10 | bulk | The bulk file, compressed, in parts of 200 MB, its manifest last (`upload-bulk.mjs`). |
| 11 | verify | The bulk manifest read back and held to the file. On this machine the whole file comes back and is compared. |
| 12 | export | On this machine only: `thenwhat export-compare` of the hot file against the working database (`ARGS="--skip-export"` leaves it out). |

A rebuild may keep an unchanged bulk file. The hot file, and D1 after it, then carry the new build's id while the bulk file keeps the id of the build that made it; the bulk file is stored under its own id, and when the bucket's manifest for that id already describes the same file it is not sent again. Where the build left `<file>.watermarks.json`, the two files must agree with it or nothing is run.

Production needs both `ENV=production` and `CONFIRM=thenwhat-store`, and every script it calls is given `--production` explicitly. Everything the steps print goes, as it arrives and unfiltered, to `<build's folder>/cutover/<env>-<time>.log`; the terminal shows the same with ids masked. `result-<env>-<time>.json` beside it has each stage's seconds, the rows D1 says were written, and the build's id. The log can hold a database's id: it stays in the build's folder and is not committed.

If a stage fails after the import began, restore to the bookmark, or for the preview run again with `--replace`.

### Restore, in two tiers

- **Hot, within Time Travel's history:** restore D1 to a bookmark (below).
- **Hot, otherwise:** build the hot file again (from a Postgres dump or a kept file, below), then steps 2 and 3 into an emptied database.
- **Bulk:** fetch it by its build id. Each part and the whole file are checked against the manifest, and the file takes its name only when it is proved.
  ```bash
  node store/ingest/scripts/download-bulk.mjs <build id> <out.sqlite> --remote
  ```
- **Payload objects** are never overwritten, each being stored under its own checksum; upload the folder again and only the missing ones are sent (`--check-first` when the notes of the earlier upload are gone).

### The daily fold, in order

A lookup's bulk records wait in D1's inbox until they are safe in R2. The order is held by the service, not by care:

1. `thenwhat store fold-inbox <bulk.sqlite> --delta <file>` reads the inbox and merges it into the bulk file. It prints the last record folded.
2. `node store/ingest/scripts/upload-delta.mjs <file> --build <id> --through <seq> --remote` puts the delta beside its build and adds it to `bulk/<build id>/deltas.json`. It prints the object's key.
3. `POST /inbox/folded {object}` records the fold. The service looks for the object in the bucket and reads how far it folded from the build's `deltas.json`; it refuses without either.
4. `POST /inbox/clear {through}` (`thenwhat store clear-inbox`) is refused past the furthest fold recorded.

A restore of the bulk tier is `download-bulk.mjs`, then `download-deltas.mjs <build id> <folder>`, then `thenwhat store apply-delta` for each delta in the list's order.

The ingest service now refuses a registry record that still names a person, in a record or as a payload object, so the fault cannot return through it. The bulk load does not pass that door: a store file is only as clean as the build that made it.

### Which database a script acts on

`import-folder.mjs`, `checksum-d1.mjs` and `empty-store.mjs` act on the database named by the Wrangler configuration in use (`--config`, else the preview's) and print its name first. A name not ending in `-preview` is production: loading or checking it needs `--production <that name>`, and emptying it is refused whatever is passed. The bucket scripts write to the preview bucket unless `--remote --production <bucket>` names production's.

### Removing payload objects

When payload objects must go (on 17 November 2026: trial payloads were found to carry people's names, emails and phone numbers from the registry, so every object uploaded that day is removed and the build corrected):

```bash
node store/ingest/scripts/remove-payloads.mjs --all-noted --remote --verify-empty        # every object the upload noted
node store/ingest/scripts/remove-payloads.mjs --not-in <payload folder> --remote         # those a rebuilt folder no longer holds
node store/ingest/scripts/remove-payloads.mjs --bulk-build <build id> --remote --verify-empty
```

Four at a time, with a longer wait after a 429. It removes and checks only the objects the upload's notes name (`store/ingest/.upload-state/`), because Wrangler 4.161.0 cannot list a bucket's objects. For proof that nothing is left, search the prefixes `payload/` and `bulk/` in the dashboard (R2, the bucket, Objects); `wrangler r2 bucket info <bucket> --jurisdiction eu` gives the object count, some minutes late. The notes are on the machine that uploaded: run it there. The same objects in a database's Time Travel history and in any downloaded copy are not touched by this.

### Bulk load: what the steps do, and what was measured

The first load of the tracker does not go through the merge. The hot tier is built on a device as a SQLite file with `store/schema.sql`, written out as SQL, and loaded with Wrangler. The figures below are from loads of the whole store, before the tiers were decided.

1. Note the restore bookmark (below).
2. Write the SQL, in a folder of its own. It also writes `manifest.json`, each table's rows.
   ```bash
   node store/ingest/scripts/dump-for-import.mjs <store.sqlite> <folder>/store.sql --rows-a-file 500000
   ```
3. Try the dump on this machine first. It loads the files into a scratch SQLite file as D1 takes them, each statement on its own with foreign keys checked at once, and counts every table. Nothing is sent anywhere.
   ```bash
   node store/ingest/scripts/check-dump.mjs <folder>
   ```
4. Put the payload objects in the bucket, under the keys the build gave them (`payload/<sha256>`). It uses Wrangler's own login and makes no access key; it is resumable, and ends by reading 20 objects back and comparing each one's checksum with its key.
   ```bash
   node store/ingest/scripts/upload-payloads.mjs <payload folder> --remote
   ```
5. Load the folder. Files go in the order of their names; the first failure stops the load; each table is then counted against the manifest.
   ```bash
   node store/ingest/scripts/import-folder.mjs <folder> --remote
   ```
6. If the counts differ, or a file failed, restore to the bookmark (or empty the store) rather than loading again over what is there. A failure names the file's tables.

What the SQL must be, from Cloudflare's import documentation read on 17 November 2026 (`docs/sources.md`): no `BEGIN TRANSACTION` or `COMMIT`; each statement at most 100,000 bytes; a file at most 5 GiB. And from the schema: every `INSERT` names its columns, because a generated column (`review_rank`) cannot be written; the search tables are filled by the schema's triggers and are not in the dump; parents come before children, in tables and in rows, because D1 checks foreign keys statement by statement.

**The first real load failed on its second file** (17 November 2026, 2,704,375 rows in 11 files): `FOREIGN KEY constraint failed`. The first file, 557 MB, had loaded in 115 s with 749,396 rows written. The cause: three merged claims point at a claim with a higher id, so their rows came before the claim they point at, and the `PRAGMA defer_foreign_keys = true` at the head of the file did not hold on D1 as it does on the local engine. The dump no longer leans on that PRAGMA: tables are written parents first by the schema's foreign keys, and a table that points at itself (a merged claim) has its rows written parents first. `check-dump.mjs` fails on the old dump at the same place and passes the new one. The local engine cannot read a file over about 500 MB, so a local trial needs smaller files than a remote load does.

A row too long for one statement (an outlet's icon of 93,062 bytes is 186 KB as hex) is written in parts: an `INSERT` with the start of the long value, then `UPDATE`s that append the rest by primary key, a BLOB's cast back to BLOB. The dumper tries each such row on a scratch copy of its table first. The manifest counts rows, not statements. A dump that fails removes its files; `import-folder.mjs` loads nothing from a folder with no manifest, a `.partial` file, or files the manifest does not list.

**Tried on the preview on 17 November 2026**, with a made-up store of 49,999 records (`scripts/sample-store.mjs`): 66,687 table rows in 176 statements, 14.9 MB of SQL, loaded in 2.8 s (6 s with Wrangler's own start). D1 reported 135,572 changes and 250,037 rows written, and the database was 19.0 MB afterwards. Nothing failed.

- **D1 bills about 3.75 rows written for each table row** of this sample, because indexes and the search tables are written too. A load of 2 million table rows is then about 7.5 million rows written.
- **The plan.** The free plan allows 100,000 rows written a day and then refuses every query until midnight UTC. The trial wrote 250,037 in one day and a later write succeeded, which only the Workers Paid plan allows (50 million a month included). No Wrangler command shows the plan; the dashboard does, under Workers & Pages, Plans.
- **Not known:** Cloudflare's documentation does not say whether the database refuses other requests while a file is loading, nor whether a file that fails is undone. Load when nothing reads the store, and restore after a failure.

To clear trial rows from a small store (the schema and the record of migrations stay):

```bash
node store/ingest/scripts/empty-store.mjs --empty thenwhat-store-preview --remote
```

It takes only the preview database, by name; there is no such command for production. It deletes in batches of 20,000 rows, passes over tables the database does not have yet, and refuses a store of more than 200,000 rows.

### Resetting the preview store

A large store is not emptied: it is replaced. On 17 November 2026 one file of `DELETE`s against the fully loaded preview (2.7 million rows, 2.3 GB) failed after 60 s with "Upstream service unavailable [code: 7009]", and every deleted row would have been a billed write. Deleting the database and creating it again took 7 s and wrote nothing.

```bash
npx wrangler d1 delete thenwhat-store-preview
npx wrangler d1 create thenwhat-store-preview --jurisdiction eu
cd store/ingest && node scripts/preview-config.mjs
npx wrangler d1 info thenwhat-store-preview --json     # jurisdiction must read eu
npx wrangler d1 migrations apply STORE --remote --config wrangler.preview.jsonc
```

The new database has a new id, so `preview-config.mjs` must be run again, and anything bound to the old id (a deployed Worker) must be deployed again. Its Time Travel history starts empty. Preview only: production is never reset this way.

### Restore

D1 keeps the database's history for 30 days on the paid plan (7 on the free). A bookmark names a moment.

```bash
npx wrangler d1 time-travel info thenwhat-store-preview        # the bookmark now: note it before a load
npx wrangler d1 time-travel restore thenwhat-store-preview --bookmark <bookmark>
```

A restore overwrites the database in place and cancels requests in flight. It prints the bookmark of the moment before it, and restoring to that undoes it. At most 10 restores in 10 minutes for a database. R2 is not restored with it: payloads are stored under their checksums and are never overwritten, so an object a restored store no longer names is only unused. A restore of the preview has not been run yet (task 3.8).

### Restoring the store from a Postgres dump or a kept store file

When Time Travel cannot help (the history has run out, or the database is gone), the store is filled again by the same bulk path as the first fill, never row by row through the ingest service.

1. From a Postgres dump: restore it into a scratch Postgres database and point `DATABASE_URL` at it. From a kept store file, skip to step 3.
2. Build the store file. The database is only read; every record goes through `store/merge.sql`; each payload over the bound a row may hold (524,288 bytes; `store/schema.sql`, the CHECK on `payload.body`) is written once under `payload/<sha256>`; `<store.sqlite>.pushed.json` is written beside the file.
   ```bash
   uv run thenwhat store build <store.sqlite> --payloads <folder>
   ```
3. Write the SQL: rows only, parents first, no transactions or schema, statements under 90 KB, files cut at 50 MB, with `manifest.json`. The last three files rebuild the search tables.
   ```bash
   uv run thenwhat store dump <store.sqlite> <sql-folder> --payloads <folder>
   ```
4. Into an empty database with the migrations applied and its jurisdiction read back: upload the payload folder to R2 under the same keys, then load and count.
   ```bash
   node store/ingest/scripts/import-folder.mjs <sql-folder> --remote
   ```
   After a load by hand, `uv run thenwhat store check <manifest.json> <counts.json>` does the count.
5. Keep `<store.sqlite>.pushed.json` with the file: `thenwhat backfill push --state <it>` then hands over only what changed since the build.

Not tested: whether rebuilding `link_lead_fts` on D1 fits its 30 seconds for a query. The schema's triggers have already filled that table as the rows arrived, so if that file fails it can be left out; the load stops there, and the count is then run by hand.

### Deploying the ingest service

Decided by the operator on 17 November 2026: the ingest service is deployed on a `workers.dev` address and answers only to tokens. It is deployed by one command and no other way:

```bash
make store-deploy ENV=preview TOKENS=<file of token checksums> ARGS="--dry-run"    # the plan and the configuration, nothing run
STORE_TOKEN_OPERATOR=... make store-deploy ENV=preview TOKENS=<file of token checksums>
STORE_TOKEN_OPERATOR=... make store-deploy ENV=production CONFIRM=thenwhat-store-ingest TOKENS=<file of token checksums>
```

Set `STORE_TOKEN_OPERATOR` in the shell from the tokens' own file (`set -a; . <file>; set +a`), never on the command line. The stages, in order:

1. **config.** The configuration that is deployed is written from the committed `wrangler.jsonc`: the Worker's name for the environment (`thenwhat-store-ingest-preview`, `thenwhat-store-ingest`), the database with its id looked up by name, the bucket in `eu`, `workers_dev` true, `preview_urls` false, logs off, the two rate limits, and no Queue. The file is git-ignored and removed at the end.
2. **jurisdiction.** The database reads back `eu` and the bucket is found in `eu`, or nothing is deployed.
3. **migrations.** None may be left to apply.
4. **deploy.**
5. **secret.** `INGEST_TOKENS` is set by `wrangler secret put`, which reads the file on its standard input. The value is never an argument and never printed or logged; the script says only how many tokens the file lists and its size, and refuses a file that is not a list of checksums.
6. **smoke.** Every route answers 401 with no token and with a wrong one; the progress page answers only its empty shell; the operator's token gets 200 from `GET /progress`. Then the address is printed.

What a `workers.dev` address exposes. Anyone can reach it. Without a known token every route answers `401 {"error":"unauthorized"}` and nothing else, whatever was asked, so a caller learns only that a service is there; `GET /progress/page` answers a static page with no count in it. Cloudflare applies its Browser Integrity Check to `workers.dev` and nothing else that is ours to configure: a zone's WAF and rate-limit rules do not apply there. So the service limits itself with the platform's rate-limit bindings: 60 requests a minute from one address with no known token, 600 a minute a token, each counted separately in each Cloudflare location and approximately. An address is used as the counting key and is not stored or logged. Cloudflare Access can be put in front of a `workers.dev` address if a second lock is wanted; every writer would then send its headers too.

Queues. `wrangler queues create` has a `--jurisdiction` flag, but Cloudflare's documentation gives it no values and says nothing of where a Queue's data rests. The service's only use of a Queue is to wake a consumer with a step's name, and nothing consumes one yet, so the deployed configuration binds none and the service sends nothing. When a consumer exists, the binding returns and the jurisdiction question is settled then.

### Watching a backfill

A slice of trials is a record of the store, kind `trial_slice`, handed over and merged like any other: which group of trials it is, how many it holds, and a count and a time for each of five stages (record fetched, registry papers looked for, PubMed asked, in the store, page built). A set is a rule and the year it was chosen in; the pipeline hands every planned slice over at the start, so a set's totals are its slices'; the merge never lets a stage go back. `GET /progress` answers counts only, to the operator's and the daily job's tokens: each set with totals by stage and every slice, the last merged run of each writer, and the rows of each table. `<address>/progress/page` shows the same as bars and a grid of slices. The page itself holds nothing; it asks for a token once, keeps it for that browser tab only, and sends it as a header, never in an address. `node store/ingest/scripts/progress-preview.mjs` shows the page on this machine with made-up counts.

