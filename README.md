# thenwhat

<img src="site/public/mark.svg" width="56" height="56" alt="The site's mark: a magnifying glass over a capsule in two halves">

News reports medical "breakthroughs" that are rarely mentioned again. thenwhat follows each coded treatment and condition, a **pair**, through the public trial registries: each pair gets a status derived by fixed rules from dated, sourced registry records. Every status lists the records that produced it, and a wrong item is removed by archiving it.

`thenwhat` is the repository codename for [What came of it?](https://whatcameofit.com). The public site runs on Cloudflare. The pairs are made by the separate data lab, which hands the site one bundle of page files. GitHub tests each proposed change and publishes a preview of it for its pull request. A merge to `main` publishes nothing: production is published only by `make deploy ARGS=--cutover` ([docs/deploy.md](docs/deploy.md)).

## Setup

Needs Node 26 (`.node-version`), [pnpm](https://pnpm.io/) 10 and make.

```sh
git clone <repository-url> thenwhat
cd thenwhat
make setup        # once per clone or worktree
make site-build   # builds the site from the tests' small bundle
```

`PAIRS_BUNDLE` names another bundle folder: `PAIRS_BUNDLE=/path/to/bundle make site-build`.

To run the site with its registry search on this machine, at <http://localhost:8787>:

```sh
cp .env.example .env   # fill in the model and registry settings
make lookup-dev
```

## Development

```sh
make check-fast   # after an edit: under a minute
make check        # the fast and slow checks CI runs
```

`make check-fast` is everything that builds nothing: the site's `tests/*.test.mjs`, the extension's source tests and the scripts' tests. `make check-slow` runs the tests that build the site (`tests/*.build-test.mjs` and the browser journeys), the store's tests, the site build and the packaged extension tests. CI runs the same checks in parallel. For work in one area, `make check-site`, `make check-extension` and `make check-store` each run that area in full.

The browser tests run against one built and indexed fixture. Run them on their own with `make site-search-test`. On an existing checkout, `make site-search-browser` installs the Chromium version they use; `make setup` does this for new checkouts.

## Repository

| Path | Contents |
|---|---|
| `site/` | Astro site and its Cloudflare Worker, built from a bundle of pairs |
| `store/` | The D1 store and its ingest service |
| `extension/` | Browser extension for Chrome and Safari |
| `video/` | Remotion project for explainer videos |
| `scripts/` | Setup and CI timing scripts |
| `openspec/` | Specifications and the active changes |
| `docs/` | Architecture decisions, deployment and data source notes |
| `SPEC.md` | Original product specification (history) |
| `GLOSSARY.md` | Domain terms |

## Disclaimer

thenwhat gives no medical advice. A registered clinical trial is not a treatment option.

## Licence

Code: MIT, see `LICENSE`. Published dataset: CC BY 4.0, see `LICENSE-DATA`.
