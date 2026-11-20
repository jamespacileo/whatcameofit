# Deploying What came of it?

The public site is https://whatcameofit.com, served by the `thenwhat` Cloudflare Worker in the Palladio account. Source code is public at https://github.com/jamespacileo/whatcameofit. The pipeline, review database, local preview and provider keys stay on the private machine.

## The site is built from the bundle of pairs, and nothing publishes it but the cutover

Decided by the operator on 20 November 2026: claims are removed from the site (openspec `pairs-site`, task 3.4). The site's only input is a bundle of pairs. There is no claims export, no committed snapshot (`site/data/published-export.json` is gone) and no `Deploy production` job: a merge to `main` runs the checks, the build rehearsal and pull request previews, and publishes nothing. Production keeps serving its last deployment, the claims site, until the cutover ("Pair pages in production", below), which the operator starts.

What the commands do now:

```sh
make deploy-ci-check        # rehearses the public build from site/tests/bundle; no account, nothing published
make deploy-check           # rehearses from PAIRS_DATABASE's current bundle (thenwhat-store by default)
make deploy ARGS=--cutover  # publishes, once the operator has said the cutover can go ahead
```

A bundle folder alone (`PAIRS_BUNDLE`, no database) is only ever a dry run: `deploy.mjs` refuses to publish one. A pull request's preview is built from `site/tests/bundle` unless `PREVIEW_PAIRS_BUNDLE` names another folder; without the preview account's pairs database it holds the pages built ahead only.

Addresses the site served while it tracked claims are frozen in `site/data/retired-addresses.json`. The build writes what each answers to `dist/gone.json`, and the Worker answers from it: a claim that one published pair lists (the bundle's `claim_slugs`, or `origin.claim_slug` in a bundle made before that field) leads to the pair with a 301, with its embed, cards, oEmbed and data record; every other claim address answers 410 Gone, as does `/data/claims.json`. No file is built for any of them.

The sections "Normal publishing workflow", "Local checks and emergency deployment" and the split release below describe publishing from the claims snapshot as it was. They are kept for the record until this file is rewritten for the cutover, and their commands (`make publish-data`, `make deploy-ci`, `SITE_FILES_BUCKET`) no longer exist.

## Normal publishing workflow

GitHub Actions runs the pipeline, store, site build, and release checks in parallel. The required `Tests and build` check passes when all suites pass. A newer push cancels outstanding checks for the same pull request. Use `make check` to run the checks locally and `make deploy-ci-check` to rehearse the public build.

For a new run on a same-repository PR, CI can reuse an earlier pass on that PR if the checked merge tree, release settings, runner image and UTC date match. The required check links to the earlier run and its extension artifact. Changed inputs, forks, manual reruns and pushes to `main` run the suites.

On `main`, the release job archives the rehearsed site for three days. Production downloads the archive from that workflow run, verifies its SHA-256 checksum and commit, and publishes it. It then checks the live commit, a stylesheet, the Worker, the published snapshot and public pages. It retries transient failures and stale responses while the release propagates. If the archive has expired, use **Run workflow** on `main` to build a fresh one.

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

Commit `site/data/published-export.json`, `site/data/published-topics.json` and `site/data/published-trials-listing.json` (the trial listing, staged by the same command; see `docs/trial-records.md`; about 29 MB for the rolling set of some 100,000 trials) with the intended changes, then push to `main` (or merge a reviewed pull request). This snapshot is the only data GitHub publishes. Since the auto-publish decision (ADR 0001, 13 November 2026) it holds every approved, unarchived claim, whoever decided it; each says whether a person checked it. Assistant decisions are never converted to human approvals. Take a claim down with `thenwhat archive <slug> --reason`, then run `make publish-data` again. Staging preserves the topic history so future builds cannot silently break a published topic address.

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

Previews use a separate Cloudflare account with its own `workers.dev` subdomain and an API token that can create, update and delete Workers only in that account. Set `CLOUDFLARE_PREVIEW_ACCOUNT_ID` as a repository variable and `CLOUDFLARE_PREVIEW_API_TOKEN` as a secret in the GitHub `preview` environment. Allow same-repository pull request runs to use that environment. Preview jobs are skipped until the account variable is set.

When switching accounts, existing preview URLs and Workers remain in the old account. Remove those Workers there and rerun the preview workflow for any open PRs that still need a link.

To publish or remove one by hand:

```sh
PR_NUMBER=12 make pr-preview-check   # builds and rehearses; publishes nothing
PR_NUMBER=12 make pr-preview
PR_NUMBER=12 make pr-preview-state   # says whether the published copy is already this commit's
pnpm --dir site exec wrangler delete --name thenwhat-pr-12 --config site/wrangler.preview.jsonc
```

`pnpm --dir site exec wrangler deployments list --name thenwhat-pr-12` shows what a preview is serving. A Worker named `thenwhat-pr-*` whose pull request is closed is a leftover and can be deleted.

### Pair pages in a preview

Decided by the operator on 20 November 2026 (openspec `pairs-site`, task 4.5): a preview shows the pair pages, including those made on request, from a D1 database of the preview account's own. Previews run in a separate Cloudflare account, and a Worker cannot be given a database of another account, so the store's databases (`thenwhat-store-preview`, `thenwhat-store`) are never reached from a preview.

| Resource | Account | Jurisdiction |
| --- | --- | --- |
| D1 database `thenwhat-pairs-pr-preview` | the preview account (`CLOUDFLARE_PREVIEW_ACCOUNT_ID`) | `eu`, set at creation |

What a preview does (`site/scripts/pairs-preview.mjs`, called by `pr-preview.mjs`):

1. Reads `thenwhat-pairs-pr-preview` with `wrangler d1 info`. When the token cannot read it, it does not exist, or its jurisdiction is not `eu`, the log says `Pair pages left out of this copy: <why>` and the copy is the claims site as before. Nothing else changes.
2. Applies `store/ingest/migrations` to it and loads the bundle (`site/tests/bundle`, or the folder `PREVIEW_PAIRS_BUNDLE` names) with the store's own loader statements, unless that version is already current there. The log says `Pair pages: bundle <version> loaded into thenwhat-pairs-pr-preview` or `already current in`.
3. Builds the copy with `PAIRS_BUNDLE` set to that bundle, and deploys it with `worker/with-pairs.mjs` and the database bound as `PAIRS`, in a configuration written for the run. `wrangler.preview.jsonc` itself holds no database id. A preview never reads production's `wrangler.jsonc`: `pairsConfig` refuses any configuration but a preview's. Only `make deploy` builds from it ("Pair pages in production", below).

The previews' database keeps the last ten bundle versions loaded (`PREVIEW_KEPT_VERSIONS` in `pairs-preview.mjs`), where the store keeps the current version and the one before for a rollback. A preview reads its pages made on request and its open-data records at the version its build recorded, for as long as it is up, and a preview's version changes only when a pull request changes its bundle. Only an open pull request whose bundle is older than ten later distinct bundles loses its version; its pages made on request then answer not found until the preview is published again. A push that changes nothing the site is made from does not do that, because the workflow sees the copy is already this commit's and skips the build: run **Pull request preview** again with a change to the site, or run `PR_NUMBER=<number> make pr-preview` from that pull request's checkout with the preview account's token, which loads the bundle again. `PREVIEW_PAIRS_KEEP` sets a smaller count (at least 2) if the preview account's database is on the Free plan's 500 MB. Previews of the committed small bundle share one version.

To turn it on, the operator, once:

1. Create the database in the preview account, signed in to that account (`wrangler login` as a user of it), then read its jurisdiction back:
   ```bash
   cd store/ingest
   CLOUDFLARE_ACCOUNT_ID=<the preview account's id> npx wrangler d1 create thenwhat-pairs-pr-preview --jurisdiction eu
   CLOUDFLARE_ACCOUNT_ID=<the preview account's id> npx wrangler d1 info thenwhat-pairs-pr-preview --json   # jurisdiction must read eu
   ```
   The migrations and the small bundle are applied by the next preview; nothing else needs loading by hand.
2. Give the preview token D1 access: in the preview account's dashboard, edit the API token stored as `CLOUDFLARE_PREVIEW_API_TOKEN` in the GitHub `preview` environment and add **Account, D1, Edit**, for the preview account only. No new secret or variable is needed: the database is found by its name.
3. Run **Pull request preview** again on an open pull request and look for the `Pair pages:` line in its log.

### Pair pages in production: rehearse, publish, roll back

openspec `pairs-site`, task 4.4. A deployment with pair pages reads its bundle from the store's D1 database, never from a folder in the repository. `site/scripts/deploy.mjs`, given `PAIRS_DATABASE`:

1. Reads the database back with `wrangler d1 info` and stops unless its jurisdiction is `eu`.
2. Reads its current bundle version (`pair_bundle.current`), or the version `PAIRS_VERSION` names, and exports it to a folder of the run with `store/ingest/scripts/export-pairs.mjs`'s `exportBundle`. The export works the version out again from the files it wrote and stops unless it matches. A version with no pair page stops the deployment.
3. Builds the site with `PAIRS_BUNDLE` set to that folder. The build checks every file against its schema and every code against the site's wording (`site/src/lib/pair-wording.ts`), and stops on either.
4. Checks that the build recorded the same version in `/pair-shell`, the frame the Worker fills for pages made on request.
5. Deploys `worker/with-pairs.mjs` with the database bound as `PAIRS`, in a configuration written for the run from `wrangler.jsonc`. `wrangler.jsonc` itself is unchanged.

The log says `Pair pages: bundle <version>, <n> pairs, from <database>`.

**Rehearse** (reads production's database, writes nothing anywhere):

```sh
pnpm --dir site exec wrangler login        # the production account
make deploy-pairs-check                     # PAIRS_DATABASE defaults to thenwhat-store
```

On this machine without Cloudflare, `site/tests/pairs-deploy.build-test.mjs` runs the same dry run against D1's local engine (`PAIRS_LOCAL_STATE=<folder>`, accepted only with `--dry-run`).

**Publish** only at the cutover, after the operator says it can go ahead (task 5.2). Without `--cutover`, deploy.mjs refuses to publish with pair pages before building anything:

```sh
PAIRS_DATABASE=thenwhat-store node site/scripts/deploy.mjs --cutover
```

A checked CI build (`--reuse-build`) holds no bundle, so it is refused with `PAIRS_DATABASE`.

**Roll back**, from quickest to fullest:

- The deployment before: `pnpm --dir site exec wrangler rollback <last-good-version-id>`, as for any release (below). A rollback to a version from before the cutover serves the claims site again.
- The bundle before, on the current code: the store keeps the current version and the one before (design decision 4), so deploy that version by name, leaving D1 as it is: `PAIRS_VERSION=<version before> ... node site/scripts/deploy.mjs --cutover`. Read the versions with `SELECT version, current, loaded_at FROM pair_bundle`.
- The claims site: `make deploy-ci` of the commit before the cutover, which still reads the committed claims export (design decision 10).

## GitHub configuration

Restrict the GitHub `production` environment to `main`. Store `CLOUDFLARE_PRODUCTION_API_TOKEN` as an environment secret there before merging the workflow. Remove the old `CLOUDFLARE_API_TOKEN` repository secret during the cutover so branch workflows lose access to it. Main requires the `Tests and build` check and disallows force pushes and deletion. Repository administrators retain GitHub's standard bypass.

Production deployments are serialized. A superseded revision is skipped when it reaches the queue. Actions are pinned to commit SHAs, and Wrangler is pinned in `site/package.json` and installed using `site/pnpm-lock.yaml`.

If you enable `EXPORT_FROM_STORE`, restrict the `store-rehearsal` environment to `main` and set its `CLOUDFLARE_STORE_READ_API_TOKEN` secret with read access to the configured D1 database and R2 bucket. Remove the old `STORE_READ_API_TOKEN` repository secret if present.

Set these repository values in Settings → Secrets and variables → Actions:

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `CLOUDFLARE_ACCOUNT_ID` | Production Cloudflare account |
| Variable | `CLOUDFLARE_PREVIEW_ACCOUNT_ID` | Separate Cloudflare account for preview Workers |
| Variable | `SUGGEST_URL` | `mailto:suggest@whatcameofit.com` once forwarding is active |
| Variable | `CORRECTIONS_URL` | `mailto:corrections@whatcameofit.com` once forwarding is active |
| Variable | `CHROME_STORE_URL` | The extension's Chrome Web Store listing, once it is published there |
| Variable | `SAFARI_STORE_URL` | The extension's Mac App Store listing, once it is published there |

Scope the production token to Workers deployment in Palladio, with Workers Routes editing and Zone read for `whatcameofit.com`. The existing token expires on 12 November 2027.

Cloudflare's [GitHub Actions guide](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/) documents deployment credentials. Keep deployment credentials out of workflow logs, and out of any run a fork's pull request starts.

## Local checks and emergency deployment

Wrangler is a project dependency; a global install is unnecessary.

```sh
make check
make deploy-ci-check # rehearses the committed snapshot; needs no private database
make deploy-ci       # publishes that snapshot; needs Cloudflare authentication
```

For local authentication, run `pnpm --dir site exec wrangler login` and verify with `pnpm --dir site exec wrangler whoami` before deployment. `make deploy-check` and `make deploy` remain available: both first export directly from the running local pipeline. `SITE_URL` defaults to https://whatcameofit.com and can be overridden explicitly.

Publish through `make deploy-ci` so the export, sitemap and public-build checks run before Wrangler. A local invocation builds the site afresh. GitHub Actions uses the checked archive from the current run.

If a production smoke check fails after publishing, inspect the failed path and the active version in Cloudflare. To restore the last good release, choose its version ID from the deployment history and roll back to it:

```sh
pnpm --dir site exec wrangler deployments list
pnpm --dir site exec wrangler rollback <last-good-version-id>
```

Verify the home page, stylesheet and `/build-revision.txt` after rollback. An older release may predate the revision file.

## Domain and contact settings

`site/public/_headers` sets the response headers Cloudflare sends with every page and file: no content-type sniffing, a limited referrer, and HTTPS only for a year. It sets nothing that forbids framing, because the embed is made to be framed.

### How long a browser keeps a built file

Files under `/_astro/` are named by their content, and `_headers` sends them with `Cache-Control: public, max-age=0, stale-while-revalidate=31536000`. A browser uses its copy at once, asks again behind the page, and keeps the newer answer for the next page. It was `public, max-age=31536000, immutable` until 2026-11-17, and must not go back to that, or to any long `max-age`. `site/tests/headers.test.mjs` holds every rule in the file to it.

The reason is how a missing file is answered. Built files skip the Worker (`run_worker_first` in `site/wrangler.jsonc` lists `!/_astro/*`), so a request for one that is not there is answered by Cloudflare's file serving with the site's "not found" page and status 404. A rule in `_headers` is matched by the address alone, so that 404 carries the `/_astro/*` rule's `Cache-Control` too. Nothing in `_headers` can tell a file from a 404.

A file can be missing for a moment at every deploy. Cloudflare calls it version skew: while a new version is reaching its locations, one location can send the new page and another, still on the old version, be asked for the new page's stylesheet, which the old version does not have. On 2026-11-17, straight after a deploy, a browser got exactly that:

| Asked for | Answer | `Cache-Control` | `Content-Type` |
| --- | --- | --- | --- |
| `/_astro/global.<hash>.css`, seconds after the deploy | 404, the "not found" page | `public, max-age=31536000, immutable` | `text/html` |
| the same address, minutes later, past the browser's store | 200 | `public, max-age=31536000, immutable` | `text/css` |
| any made-up `/_astro/…` address | 404 | `public, max-age=31536000, immutable` | `text/html` |

The browser kept the 404 as it was told to, refused it as a stylesheet (`X-Content-Type-Options: nosniff`), and drew every page unstyled on every reload until that one address was fetched afresh by hand. It would have done so for a year.

With the header as it is now, checked on `wrangler dev` (2026-11-17): a real file and a missing one both carry the new header; a browser that has kept a 404 for an address gets the 404 once more from its store when the file exists, asks again behind that, and has the file from the next request on. A reader caught by a deploy can see one or two unstyled pages, not a year of them.

What this does not close is the moment itself: the first page loaded during a deploy's spread can still be unstyled. One `wrangler deploy` cannot order its way out of that, since the page and its files belong to one version and the spread is Cloudflare's. Two things would narrow it, neither done here: keeping the previous build's `/_astro/` files in each new build, so a page from the version before still finds its files, and a response header rule on the zone that marks a 404 under `/_astro/` as `no-store`, which is set in Cloudflare's dashboard and not in this repository. Sending built files through the Worker would let it set the header by status, at the cost of a Worker request for every file of every page.

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

To disable paper enrichment, remove `OPENALEX_API_KEY` from the Worker (and local environment for local runs). Do not increase budgets to recover from a refusal. The unrelated private-pipeline research review workflow remains tracked in `openspec/changes/archive/2026-11-18-related-research/tasks.md`.

## Progressive extension lookups (Safari 0.9.3)

`/api/lookup` accepts `stream: true` for an opt-in `application/x-ndjson` response. Each line is a JSON event: `{type:"core", result, timings}` once all clinical search and scoring are complete, then `{type:"complete", result, timings}` with optional research enrichment. A failure is `{type:"error", error, status}`; a streaming response can therefore have HTTP 200 and still contain an explicit error event. Cache hits and preflight refusals may remain ordinary JSON. Existing JSON clients retain their complete response shape.

Timing events contain numeric durations/completion offsets only, with no article text or identifiers. Ordinary completed responses expose timing fields through `Server-Timing`. No request logging or telemetry service is introduced. Cache version 2 excludes older results and permits completed independently public non-treatment identifications; unfinished streams and answers with unchecked papers remain ineligible. The extension reuses complete local answers for unchanged content, keeps shared hits locally, and avoids automatic screenshots of substantial ordinary text articles while retaining image-dependent fallback and the explicit Screenshot action.

`read_ms`, `papers_ms`, `score_ms`, and `research_ms` measure each stage from its own start. `registry_ms` sums active registry calls, excluding time waiting in the lookup queue. Stages overlap, so their durations must not be added to estimate latency. `core_ms` and `total_ms` are elapsed milestones from lookup start, not stage durations.

## The store on D1

The store holds the bundles of pairs the site is built from: its migrations and the scripts that load and read back a bundle are in `store/ingest/` (`store/README.md`). The ingest service, the two tiers, the cut-over from Postgres, the daily fold and the payload bucket described here until 2026-11-20 belonged to the claims store, removed with claims that day; their text stays in git history. The tables migrations 0001 to 0010 made are dropped at the cutover, on the operator's word.

## Removing saved copies from KV

When saved entries in `LOOKUP_RESULTS` must go before they lapse (as on 2026-11-17, when copies of registry records that named people were purged), list the keys under each prefix and delete them in bulk, then list again and repeat until a listing comes back empty. KV's key listing lags behind its writes and deletes: that purge took three passes to remove 5,091 keys, and one pass alone left keys behind. Deploy the Worker that no longer writes such entries first, or they are written again.
