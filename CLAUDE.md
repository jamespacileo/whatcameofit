# thenwhat

Public tracker of what happened to reported medical breakthroughs. The unit is a **claim** (one intervention for one indication), not an article. `thenwhat` is a codename; brand strings live in one config file.

Folder: `products`. Workspace rules: `~/Projects/CLAUDE.md` (never create at root,
worktrees via `wt`, archive via quarantine).

- Run: `docker compose up --build -d`, then `docker compose run --rm pipeline thenwhat --help`
- Test: `make check` (ruff, ty, pytest, site build)

## Where things are defined

- `SPEC.md`: origin document and full product vision. Read-only history.
- `openspec/specs/`: current behavior. `openspec/changes/<change>/`: proposals, requirement deltas, design and task state. Record behavior changes in the active change; do not start a parallel PRD or task list.
- `GLOSSARY.md`: domain terms. Use them exactly in code, CLI output and site copy.
- `docs/adr/`: enduring architectural decisions. `docs/sources.md`: terms and rate limits per data source.

## Conventions and guardrails

- Accuracy is the brand. Nothing reaches the public site unless it is approved in review.
- Claim status is derived by deterministic rules from approved evidence events. No model decides status, and every status lists the events that produced it.
- No editorial verdicts. "No signal" is never worded as "dead" or "abandoned".
- No medical advice. A registered trial is never presented as a treatment option.
- Store the raw API payload and fetch timestamp for every evidence event.
- Summarise and link to news articles. Never store or display article text, including in logs, caches and test fixtures.
- Subscriber emails are the only personal data, and none is collected before Phase 2. UK GDPR applies: double opt-in, one-click unsubscribe, deletion on request.
- Respect robots.txt and published rate limits. Identify the client with a contact User-Agent.
- Check a source's current terms, auth and rate limits before writing its client, and note them in `docs/sources.md`.
- Tests for status rules and each source client use recorded fixtures. No live network calls in tests or CI.
- No model IDs in code. Provider, model and prices come from environment variables.
- Secrets live in `.env`, which is never committed. Keep `.env.example` current.
- Nothing public is served from the home network. The pipeline and database stay private.
- Small commits with conventional commit messages. The README must get a clean clone running in under ten commands.

## Layout

- `pipeline/`: Python 3.12, managed with `uv`. Typer CLI in `src/thenwhat/cli`, one package per pipeline step. `status/` is pure: no database, network or clock.
- `site/`: Astro static site. Its only input is the pipeline's JSON export at `site/data/export.json`.
- `data/seed/`: claims CSV and the seeded example claim.
