# Deploying What came of it?

The public site is https://whatcameofit.com, served by the `thenwhat` Cloudflare Worker in the Palladio account. Source code is public at https://github.com/jamespacileo/whatcameofit. The pipeline, review database, local preview and provider keys stay on the private machine.

## Normal publishing workflow

Changes to `main` run the complete test suite and a public deployment rehearsal in GitHub Actions. Only after those pass does GitHub deploy production and check the live home, method, sitemap and claim pages. Pull requests run the checks without deployment credentials and do not create public previews. The Actions page also offers a manual run for `main`.

To publish newly reviewed claims, finish the human review locally and run:

```sh
make publish-data
git diff -- site/data/published-export.json
```

Commit `site/data/published-export.json` with the intended changes, then push to `main` (or merge a reviewed pull request). This snapshot is the only data GitHub publishes. It contains one human-reviewed claim at initial setup. Assistant decisions are not converted to human approvals by staging or deployment.

Staging first asks the running pipeline for a normal export with preview mode disabled. It validates the export and replaces the snapshot atomically. Invalid JSON, a preview, an empty export, or an unchecked claim leaves the previous snapshot unchanged. GitHub cannot reach the local database; database changes alone therefore never publish anything.

## GitHub configuration

The repository uses a `production` environment restricted to `main`. Production deployments are serialized. GitHub Actions are pinned to reviewed commit revisions; Wrangler is pinned in `site/package-lock.json` and installed with `npm ci`.

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

Cloudflare owns the apex custom-domain attachment and certificate. Enable Always Use HTTPS. Configure `www` as a proxied DNS record with a permanent redirect to `https://whatcameofit.com`, preserving paths and query strings. Do not enable an additional Cloudflare Git build pipeline alongside GitHub Actions, which would cause competing deployments.

`suggest@whatcameofit.com` and `corrections@whatcameofit.com` forward to the verified operator inbox. Configure their GitHub variables only after Email Routing reports active rules. Forwarding receives mail; it does not provide an outgoing mailbox.

No added reader analytics are installed. Cloudflare retains operational request/error counts independently of Worker logging; [Cloudflare metrics documentation](https://developers.cloudflare.com/workers/observability/metrics-and-analytics/) explains those counts. The method page states this, and Worker observability remains disabled.

## Optional registry search

Automatic deployments currently leave paid model search disabled. It needs an explicit choice of model and budget before enabling. Store `OPENAI_API_KEY` only as a Cloudflare Worker secret; never put it in source or public GitHub variables. The existing local deploy script accepts `LLM_MODEL`, `CONTACT_EMAIL`, and optional `LLM_BASE_URL`, `DECISION_BACKEND` and `DECISIONS_MODEL`. Configure the same settings deliberately in the production workflow before relying on them; otherwise the next CI deployment disables the search UI again.

## Renaming or retiring a topic after launch

A published topic address must keep working. To rename or retire a vertical:

1. In `pipeline/src/thenwhat/claims/verticals.py`, change or remove the vertical, and add its old slug to `RETIRED_VERTICALS` with the vertical that replaces it, for example `{"eyes-and-ears": "sight-and-hearing"}`. `make check` refuses a retired slug that is still configured, or one whose successor does not exist.
2. Move the claims filed under the old slug with `thenwhat claim edit SLUG --vertical NEW`.
3. Export again and build (`npm --prefix site run build`). The build writes `site/dist/_redirects` with a permanent redirect from `/topic/OLD` to `/topic/NEW`. It fails, naming the slug, when `published-topics.json` lists a topic that is neither current nor retired.
4. Deploy with `make deploy`.

Before launch there is no `published-topics.json`, so slugs can change with no redirect.


## Rollback

Revert the faulty source/data commit on `main` and push. GitHub tests and republishes the reverted version. For an immediate rollback, run `npx wrangler rollback` from `site/` after signing in, then revert the source commit so the next automatic deployment preserves the fix. Keep the previous committed public snapshot for data rollbacks. Do not delete the Worker to roll back.
