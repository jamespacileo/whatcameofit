# thenwhat

Public tracker of the evidence for medical treatments. The site follows each coded treatment-condition **pair** through the public trial registries. The pairs are made by the separate data lab (`thenwhat-lab`), which hands the site one bundle of page files. `thenwhat` is a codename. Brand strings live in one config file.

Folder: `products`. Workspace rules: `~/Projects/CLAUDE.md` (never create at root,
worktrees via `wt`, archive via quarantine).

- Run: `make setup`, then `make site-build` (the tests' small bundle) or `make lookup-dev` (the site with its registry search, at localhost:8787).
- Test: two sets. `make check-fast` after every edit (under a minute: the site's, extension's and scripts' tests that build nothing). `make check-slow` before a push (every test that builds the site, the store's tests, the site and extension builds). `make check` is both, and is what CI runs. One area in full: `make check-site`, `check-extension`, `check-store`.
- A site test that builds the site is named `*.build-test.mjs` and runs in the slow set; any other is `*.test.mjs`.
- New clone or worktree: `make setup` (Node 26 from `.node-version`, pnpm 10). pnpm links packages from its shared store, so nothing is downloaded twice. Never `npm install`: the lock files are `pnpm-lock.yaml`.

## Where things are defined

- `SPEC.md`: origin document and full product vision. Read-only history.
- `openspec/specs/`: current behavior. `openspec/changes/<change>/`: proposals, requirement deltas, design and task state. Record behavior changes in the active change (`pairs-site` for the site); do not start a parallel PRD or task list.
- `GLOSSARY.md`: domain terms. Use them exactly in code and site copy.
- `docs/adr/`: enduring architectural decisions. `docs/sources.md`: terms and rate limits per data source.
- `PRODUCT.md`: audience and product context, inferred from `SPEC.md` and not yet confirmed line by line. `DESIGN.md`: the site's visual system as built, in the "evidence digest" direction the operator chose.

## Conventions and guardrails

- Claims were removed on 2026-11-20 (the operator's decision): the site, its tests and its copy know only pairs. The old claim addresses answer from `site/data/retired-addresses.json`: a 301 to the one published pair that lists the claim's slug, otherwise 410 Gone.
- A merge to `main` publishes nothing. Production is published only by `make deploy ARGS=--cutover`, on the operator's go-ahead (`docs/deploy.md`).
- Accuracy is the brand, and it is shown, not gated (`docs/adr/0001-publish-by-rule-archive-to-remove.md`): items are approved by deterministic rules, every match the site shows carries its confidence score and reasons, and the operator removes a wrong item by archiving it. Live lookup answers are shown to the reader who asked, with scores, and are never worded as a status.
- A status is derived by deterministic rules from approved registry records. No model decides status, and every status lists the records that produced it.
- No editorial verdicts. "No signal" is never worded as "dead" or "abandoned". One exception (`docs/adr/0010-a-records-mark-is-coloured-by-which-way-the-record-moved.md`): the small mark on a registry record is coloured by which way the record moved, by one tested rule. A completed trial and posted results are never coloured, and no status is.
- No medical advice. A registered trial is never presented as a treatment option.
- The site owns all wording; the bundle carries codes. A code with no wording, and a status label with verdict wording, fail the site build.
- Summarise and link to news articles. Never store or display article text, including in logs, caches and test fixtures.
- Subscriber emails are the only personal data, and none is collected before Phase 2. UK GDPR applies: double opt-in, one-click unsubscribe, deletion on request.
- Whether and how a news site is asked is the page reader's decision (`docs/adr/0006-whether-and-how-a-site-is-asked-is-the-page-readers-decision.md`). Registries and literature indexes are asked directly, within their published rate limits, with a contact User-Agent.
- Check a source's current terms, auth and rate limits before writing its client, and note them in `docs/sources.md`.
- Tests use recorded fixtures. No live network calls in tests or CI.
- No model IDs in code. Provider, model and prices come from environment variables.
- Secrets live in `.env`, which is never committed. Keep `.env.example` current.
- Nothing public is served from the home network. One exception (`docs/adr/0005-the-page-reader-is-the-one-home-service-a-worker-may-ask.md`): the page reader runs at home and the lookup service may ask it through a tunnel closed to everyone else.
- Small commits with conventional commit messages. The README must get a clean clone running in under ten commands.
- After changing `site/tests/bundle`, write its manifest again: `rm site/tests/bundle/manifest.json && node store/ingest/scripts/bundle-manifest.mjs site/tests/bundle`.

## Layout

- `site/`: Astro site and its Worker. Its only input is a bundle of pairs, the folder `PAIRS_BUNDLE` names (`site/tests/bundle` in tests), or the D1 database `PAIRS_DATABASE` names for a deploy (openspec `pairs-site`). Published to Cloudflare only through `make deploy` (`docs/deploy.md`), never `wrangler deploy` alone. Each pull request also gets its own copy on a `thenwhat-pr-<number>` Worker, through `make pr-preview` only.
- `store/`: the D1 store's migrations and the scripts that load a bundle of pairs into it and read one back, including the bundle manifest the site checks (`store/README.md`). No Worker is deployed from it.
- `extension/`: browser extension for Chrome and Safari, plain JavaScript. Its inputs are the site's `lookup.json` and, only when a reader asks for a registry search of the open page, the site's lookup service. The keys of `lookup.json` (including `claims`) stay as the released extension reads them until a new release reads others. It shares the site's address comparison, page reader and answer wording (copied at build) and holds no status wording of its own. Screenshots stay out of storage; only independently public structured answers may enter the shared 24-hour cache.
