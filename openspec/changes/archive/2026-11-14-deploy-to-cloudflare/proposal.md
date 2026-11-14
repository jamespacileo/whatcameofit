# Proposal

## Why

The site can be built for the public, but nothing in the repository publishes it, and nothing stops the wrong build from being published. The local preview holds 84 claims decided by the assistant; uploading that build by mistake would put unreviewed statuses in front of readers. The operator has registered a domain with Cloudflare and asked for the deployment to be set up (2026-11-12).

## What Changes

- A Cloudflare Workers configuration that serves the built site as static files at the site's own domain only.
- One command that checks, builds and publishes, and one that does everything except publish.
- The command refuses a preview export, an export with a claim not checked by a person, an empty export, and an address that is missing, local, not HTTPS or not the bare site address.
- The command writes its own normal export from the pipeline, so a local preview setting cannot leak into a deployment.
- An operator guide, `docs/deploy.md`.

Nothing is deployed by this change. The domain's name is not recorded; it is given as `SITE_URL` when the command is run.

## Capabilities

### New Capabilities

- `deployment`: what may be published and what stops a deployment.

### Modified Capabilities

None.

## Impact

- New: `site/wrangler.jsonc`, `site/scripts/deploy.mjs`, `site/scripts/deploy-checks.mjs`, `site/tests/deploy.test.mjs`, `docs/deploy.md`, three Makefile targets.
- Needs Wrangler on the operator's machine. It is not added as a dependency.
- Hosting on Cloudflare means the host counts requests. The method page's "What is counted" section must be made true before the first deploy; that wording is the operator's.
