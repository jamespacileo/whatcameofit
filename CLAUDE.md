# thenwhat

Public tracker of the evidence for medical claims. A **claim** covers one intervention or complete regimen for one indication and can be drafted from registry evidence before a news report exists. `thenwhat` is a codename. Brand strings live in one config file.

Folder: `products`. Workspace rules: `~/Projects/CLAUDE.md` (never create at root,
worktrees via `wt`, archive via quarantine).

- Run: `docker compose up --build -d`, then `docker compose run --rm pipeline thenwhat --help`
- Test: two sets. `make check-fast` after every edit (under a minute: ruff, ty, the pipeline's tests in parallel, the site's and extension's tests that build nothing). `make check-slow` before a push (about two minutes: every test that builds the site, the store's tests, the site and extension builds). `make check` is both, and is what CI runs. One area in full: `make check-pipeline`, `check-site`, `check-extension`, `check-store`.
- A site test that builds the site is named `*.build-test.mjs` and runs in the slow set; any other is `*.test.mjs`. A pipeline test that builds the site is marked `@pytest.mark.slow`. One pipeline test alone: `uv run --directory pipeline pytest tests/<file>::<test>`.
- New clone or worktree: `make setup` (Node 26 from `.node-version`, pnpm 10). pnpm links packages from its shared store, so nothing is downloaded twice. Never `npm install`: the lock files are `pnpm-lock.yaml`.

## Where things are defined

- `SPEC.md`: origin document and full product vision. Read-only history.
- `openspec/specs/`: current behavior. `openspec/changes/<change>/`: proposals, requirement deltas, design and task state. Record behavior changes in the active change; do not start a parallel PRD or task list.
- `GLOSSARY.md`: domain terms. Use them exactly in code, CLI output and site copy.
- `docs/adr/`: enduring architectural decisions. `docs/sources.md`: terms and rate limits per data source.
- `PRODUCT.md`: audience and product context, inferred from `SPEC.md` and not yet confirmed line by line. `DESIGN.md`: the site's visual system as built, in the "evidence digest" direction the operator chose.

## Conventions and guardrails

- Accuracy is the brand, and it is shown, not gated. Decided by the operator on 2026-11-13 (`docs/adr/0001-publish-by-rule-archive-to-remove.md`, change `auto-publish`): items are approved by deterministic rules and published without waiting for a person, every match the site shows carries its confidence score and reasons, and the operator removes a wrong item by archiving it. Live lookup answers are shown to the reader who asked, with scores, and are never worded as a status.
- Claim status is derived by deterministic rules from approved evidence events. With no trial found, the confirmed evidence stage decides between "preclinical only" and "no trial record found": a stage is confirmed by a person or, in the sure band, by rule. A reading in the lower band is shown with its score, marked low confidence, and never sets a status (`docs/adr/0004-two-confidence-bands-shown-not-reviewed.md`). No model decides status, and every status lists the events that produced it.
- No editorial verdicts. "No signal" is never worded as "dead" or "abandoned". One exception, decided by the operator on 2026-11-17 (`docs/adr/0010-a-records-mark-is-coloured-by-which-way-the-record-moved.md`): the small mark on a registry record is coloured by which way the record moved (begun or approved, halted or refused, or neither), by one tested rule. A completed trial and posted results are never coloured, and no status is.
- No medical advice. A registered trial is never presented as a treatment option.
- Store the raw API payload and fetch timestamp for every evidence event.
- Summarise and link to news articles. Never store or display article text, including in logs, caches and test fixtures.
- Subscriber emails are the only personal data, and none is collected before Phase 2. UK GDPR applies: double opt-in, one-click unsubscribe, deletion on request.
- Whether and how a news site is asked (robots.txt, rate limits, how the client presents itself) is the page reader's decision (`docs/adr/0006-whether-and-how-a-site-is-asked-is-the-page-readers-decision.md`); the pipeline acts on its answers and fetches no page another way. Registries and literature indexes are asked directly, within their published rate limits, with a contact User-Agent.
- Check a source's current terms, auth and rate limits before writing its client, and note them in `docs/sources.md`.
- Tests for status rules and each source client use recorded fixtures. No live network calls in tests or CI.
- No model IDs in code. Provider, model and prices come from environment variables.
- Secrets live in `.env`, which is never committed. Keep `.env.example` current.
- Nothing public is served from the home network. The pipeline and database stay private. One exception, decided by the operator on 2026-11-15 (`docs/adr/0005-the-page-reader-is-the-one-home-service-a-worker-may-ask.md`): the page reader runs at home and the lookup service may ask it through a tunnel closed to everyone else.
- Small commits with conventional commit messages. The README must get a clean clone running in under ten commands.

## Working rules learned so far

- Tests sit at agreed seams: functions that take a session (against the real test database), pure functions, and one success plus one refusal per CLI command. Internal helpers get no tests of their own.
- The initial migration has been regenerated in place while nothing is deployed. Once any database holds real claims, add new migrations instead.
- The site owns all wording; the export carries codes. A status label with verdict wording fails the site build.
- After changing the export's shape, regenerate `site/export.schema.json`. After changing the seed, regenerate `site/data/seed-export.json`. Tests fail until both match.
- Registry fixtures are recorded with a generic client name and have abstracts replaced. Article fixtures are always synthetic.
- Seed decisions use the `seed` decider. Never record a model's or a script's decision as `human`.
- An intervention is entered by its name alone: no maker, mechanism or brackets. The registry search sends the name as written, and a description ("the drug") is not a name.
- A trial matches a claim only when it tests the intervention for the claim's indication. Never approve by score alone, by hand or by rule, a candidate marked as scored without the indication.
- Prepare many claims with `thenwhat prepare`, not one command per step per claim.
- A claim that a link lead's read drafts stays pending until `thenwhat prepare --pending` has searched its registries, then is approved by rule. Run it after every read run and before any export.
- A claim `prepare` approves for a read is held awaiting audit, and no export publishes it until `thenwhat audit clear` releases it (`docs/adr/0007-a-read-batch-waits-for-its-audit.md`). The audit archives what is wrong and clears the rest.
- Run registry claim batches explicitly. Preview `thenwhat draft-from-registry` and apply the reviewed plan, then run `thenwhat prepare --pending`, audit the batch, release it and export. The daily run starts no registry drafting, batch audit, release or export. See `docs/backfill-loop.md` and the `registry-drafted-claims` change.
- Two claims for one intervention and indication are merged with `thenwhat claim merge`, never fixed by archiving one. A wrong intervention name is corrected with `thenwhat entity rename`, not `claim edit`: it checks the entry rules and marks the registry search due. After either, run `thenwhat prepare --due` before the export (change `claim-merge-and-rename`).
- A review decision you make yourself is recorded with `--as-assistant`. The claim is published like any other, and the export marks it `checked_by_person: false`.

## Layout

- `pipeline/`: Python 3.12, managed with `uv`. Typer CLI in `src/thenwhat/cli`, one package per pipeline step. `status/` is pure: no database, network or clock.
- `site/`: Astro static site. Its only input is the pipeline's JSON export at `site/data/export.json`. Published to Cloudflare only through `make deploy` (`docs/deploy.md`), never `wrangler deploy` alone. Each pull request also gets its own copy on a `thenwhat-pr-<number>` Worker, through `make pr-preview` only.
- `extension/`: browser extension for Chrome and Safari, plain JavaScript. Its inputs are the site's `lookup.json` and, only when a reader asks for a registry search of the open page, the site's lookup service. It shares the site's address comparison, page reader and answer wording (copied at build), holds no status wording of its own, and may send a cleaned source URL plus a bounded visible screenshot when readable content is insufficient. Screenshots stay out of storage; only independently public structured answers may enter the shared 24-hour cache. Its permissions are the site's host and `t.co`, whose links it opens to learn where a post on X leads, plus `alarms` and `notifications` for the twice-daily check of followed claims and the reader's reminders.
- `video/`: Remotion project for explainer videos (`video/README.md`). The records a video shows are copied from the published export into `src/remotion/scenes/claim-data.ts`; the site's guardrails on headlines, verdicts and medical advice hold there too. Narration audio and rendered video are not committed, except the 1080p file and poster the method page shows, in `site/public/video/`.
- `data/seed/`: claims CSV and the seeded example claim.
