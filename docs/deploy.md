# Deploying What came of it?

The public site is https://whatcameofit.com, served by the `thenwhat` Cloudflare Worker in the Palladio account. Source code is public at https://github.com/jamespacileo/whatcameofit. The pipeline, review database, local preview and provider keys stay on the private machine.

## Normal publishing workflow

Changes to `main` run the complete test suite and a public deployment rehearsal in GitHub Actions. Only after those pass does GitHub deploy production and check the live home, method, sitemap and claim pages. Pull requests run the checks without deployment credentials and do not create public previews. The Actions page also offers a manual run for `main`.

To publish newly reviewed claims, finish the human review locally and run:

```sh
docker compose exec -T pipeline thenwhat icons
make publish-data
git diff -- site/data/published-export.json
```

The icons command saves logos for newly encountered publishers. Use `thenwhat icons --retry-missing`
inside the pipeline container to retry publishers that previously returned no usable image.
Unavailable icons use a letter tile; pages never fetch logos from third-party hosts.

The site build regenerates browser, launcher and share-brand assets from the canonical SVGs.
Brand URLs include an artwork revision so returning readers receive updated icons.

Commit `site/data/published-export.json` and `site/data/published-topics.json` with the intended changes, then push to `main` (or merge a reviewed pull request). This snapshot is the only data GitHub publishes. Since the auto-publish decision (ADR 0001, 13 November 2026) it holds every approved, unarchived claim, whoever decided it; each says whether a person checked it. Assistant decisions are never converted to human approvals. Take a claim down with `thenwhat archive <slug> --reason`, then run `make publish-data` again. Staging preserves the topic history so future builds cannot silently break a published topic address.

Staging first asks the running pipeline for a normal export with preview mode disabled. It validates the export and replaces the snapshot atomically. Invalid JSON, a preview, an empty export, or an unchecked claim leaves the previous snapshot unchanged. GitHub cannot reach the local database; database changes alone therefore never publish anything.

## GitHub configuration

The repository uses a `production` environment restricted to `main`. Production deployments are serialized; a superseded revision is skipped when it reaches the deployment queue. GitHub Actions are pinned to reviewed commit revisions; Wrangler is pinned in `site/package-lock.json` and installed with `npm ci`. Main requires the `Tests and build` check and disallows force pushes and deletion; repository administrators retain GitHub's standard bypass.

Set these repository values in Settings → Secrets and variables → Actions:

| Kind | Name | Value |
| --- | --- | --- |
| Secret | `CLOUDFLARE_API_TOKEN` | The dedicated production deployment token; never commit it |
| Variable | `CLOUDFLARE_ACCOUNT_ID` | `ee6dc8763af66b85cf2333e1ea5a4d9f` |
| Variable | `SUGGEST_URL` | `mailto:suggest@whatcameofit.com` once forwarding is active |
| Variable | `CORRECTIONS_URL` | `mailto:corrections@whatcameofit.com` once forwarding is active |

The token permits Workers Scripts editing in Palladio, Workers Routes editing for `whatcameofit.com`, and Zone read for that domain. It expires on 12 November 2027; replace the encrypted GitHub secret before then. It has no billing, database, model-provider, or email permissions.

Cloudflare's [GitHub Actions guide](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/) documents deployment credentials. Keep deployment credentials out of pull requests and workflow logs.

## Local checks and emergency deployment

Wrangler is a project dependency; a global install is unnecessary.

```sh
make check
make deploy-ci-check # rehearses the committed snapshot; needs no private database
make deploy-ci       # publishes that snapshot; needs Cloudflare authentication
```

For local authentication, run `npx --prefix site wrangler login` and verify with `npx --prefix site wrangler whoami` before deployment. `make deploy-check` and `make deploy` remain available: both first export directly from the running local pipeline. `SITE_URL` defaults to https://whatcameofit.com and can be overridden explicitly.

Never run raw `wrangler deploy`: it bypasses the public-data checks and could publish an old preview build. All supported deploy targets validate the export, build it afresh as a public site, and check its sitemap and preview flag before invoking Wrangler.

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
3. Export again and build (`npm --prefix site run build`). The build writes `site/dist/_redirects` with a permanent redirect from `/topic/OLD` to `/topic/NEW`. It fails, naming the slug, when `published-topics.json` lists a topic that is neither current nor retired.
4. Run `make publish-data`, commit both publication files, and push to `main`.

The initial publication history preserves all old topic addresses, including empty topics. `/topic/dental-regeneration` now redirects to `/topic/mouth-and-teeth`. The former transplant topic split across several organs, so its address redirects to the topic directory instead of one organ.


## Rollback

Revert the faulty source/data commit on `main` and push. GitHub tests and republishes the reverted version. For an immediate rollback, run `npx wrangler rollback` from `site/` after signing in, then revert the source commit so the next automatic deployment preserves the fix. Keep the previous committed public snapshot for data rollbacks. Do not delete the Worker to roll back.

## OpenAlex and ROR

`OPENALEX_API_KEY` is installed in the ignored root `.env`, `site/.dev.vars`, the GitHub repository's encrypted Actions secrets, and the deployed `thenwhat` Worker. `make lookup-dev` copies it into the local Worker settings. It is never a public build variable. Wrangler preserves the existing Worker secret across normal CI deployments; the deployment does not print or pass the key as an argument. ROR needs no key or registration while its client-ID registration is paused.

The public `/api/lookup` response adds optional `research` with papers, organisations and per-source availability. Both use the existing `LOOKUP_RESULTS` KV namespace with a separate metadata prefix and seven-day TTL. Two keyword queries at most, ten papers each, and three explicit organisation names at most; no pagination, full text, embeddings or extra OpenAI calls. Bibliographic relevance and organisation identity do not change claim status. Older extensions safely ignore the additional field; extension 0.9.0 shows it.

OpenAlex must remain a free account with no prepaid credit or automatic top-up. Each uncached charged request checks `/rate-limit`, the reported search price, <=$1 daily budget, $0.01 reserve and zero prepaid balance. Unknown limits or paid credit disable literature queries. The provider's account-wide cap handles concurrency; KV is not a hard money counter. 402/exhaustion pauses until UTC reset; 429 pauses per Retry-After (60 seconds to one day). Cached metadata remains usable. ROR is free, bounded and cached; provider 429 is respected. Missing keys or enrichment outages leave trial lookup available. See `docs/sources.md` for current source terms.

To disable paper enrichment, remove `OPENALEX_API_KEY` from the Worker (and local environment for local runs). Do not increase budgets to recover from a refusal. The unrelated private-pipeline research review workflow remains tracked in `openspec/changes/related-research/tasks.md`.
