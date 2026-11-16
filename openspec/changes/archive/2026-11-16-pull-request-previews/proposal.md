# Pull request previews

## Why

A change to the site can only be looked at on the machine that made it until it is merged and deployed to production. The operator's other Cloudflare projects publish a copy of each pull request automatically, replace it on every push and remove it when the pull request closes, and that made review quick. On 2026-11-16 the operator asked for the same here.

The `deployment` capability forbids it twice: pull requests "SHALL NOT receive the Cloudflare secret or publish previews", and a deployment "SHALL NOT create any other public address for the site". This change reverses the first for pull requests from this repository's own branches and narrows the second to production.

## What Changes

- **Each pull request gets its own Worker**, `thenwhat-pr-<number>`, at a workers.dev address. Published on open, replaced on push, deleted on merge or close. A comment on the pull request carries the address.
- **A preview is not the site.** It is sent with `noindex`, is built for the production address so its canonical links name the real site, and has no custom domain.
- **A preview cannot spend or store.** No model settings or keys, no saved-results namespace, so the registry search answers "not set up".
- **Production is unchanged.** It still has no workers.dev address and no per-version addresses, and is still deployed only from `main` after the checks.
- **BREAKING** for `deployment`: a pull request's run from a branch of this repository reads the Cloudflare token. A fork's does not.

Not in this change: a separate Cloudflare token for previews; previews of the registry search; previews for forks.

## Capabilities

### Modified Capabilities

- `deployment`: pull requests publish a preview; the one-address rule applies to production.
