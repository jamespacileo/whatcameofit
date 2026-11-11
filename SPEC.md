# Breakthrough follow-up tracker: initial spec

Working codename: `thenwhat` (placeholder; final name and domain not chosen).

## How to use this file

Save as `SPEC.md` in the project root, then start Claude Code with:

> Read SPEC.md. Do not write code yet. First reply with (1) questions on anything ambiguous, (2) a proposed repo layout, and (3) a task breakdown for Phase 1 only. After I approve, scaffold the repo and create a CLAUDE.md that records the conventions in section 9.

## 1. Problem

News regularly reports "miracle" medical breakthroughs: tooth and gum regrowth, hair regeneration, longevity, muscle repair, cancer cures. Most are never mentioned again. Some stall at funding after a proof of concept, some get follow-up papers, some reach clinical trials or approval. No public site tracks what happened afterwards.

## 2. Product

A public website where the unit is a **claim**, not an article. Each claim ("drug X regrows teeth in mice, human trials by 2025") has a living status page built from dated, sourced evidence in public registries.

Primary user actions:

1. Search or browse "what happened to X".
2. Paste a news article URL and get the status of the claim it describes.
3. Follow a claim and get an email when its status changes.

### Non-goals

- No medical advice and no treatment recommendations.
- No republishing of news article text. Link and summarise only.
- No user accounts in Phase 1 to 3 beyond email subscription.
- No editorial verdicts such as "abandoned" or "scam". Statuses are derived from evidence.

## 3. Data model

| Entity | Key fields |
|---|---|
| `claim` | id, slug, headline, summary, vertical, first_reported_date, promised_timeline (text + parsed date), current_status, status_updated_at |
| `source_article` | id, claim_id, url, outlet, title, published_date |
| `entity` | id, claim_id, type (intervention, paper, person, institution, company), name, synonyms[], external_ids (DOI, NCT, Companies House number, etc.) |
| `evidence_event` | id, claim_id, type, event_date, source_name, source_url, raw_payload, summary, confidence, reviewed (bool) |
| `subscription` | id, claim_id, email, confirmed, created_at |
| `decision_log` | id, step, input_ref, model, output, confidence, human_label (nullable) |

Evidence event types: `followup_paper`, `trial_registered`, `trial_status_change`, `trial_results_posted`, `grant_awarded`, `company_event`, `retraction`, `regulatory_decision`.

Claim statuses: `preclinical_only`, `trial_registered`, `phase_1`, `phase_2`, `phase_3`, `approved`, `failed`, `terminated`, `retracted`, `no_signal` (with years since last event).

**Status is derived by deterministic rules from evidence events.** No model decides status. Every status must be explainable by listing the events that produced it.

## 4. Public data sources

Verify current terms, auth and rate limits for each source before implementing its client. Each client lives in its own module behind a common interface, with response caching and polite rate limiting.

| Purpose | Source | Notes |
|---|---|---|
| Trials | ClinicalTrials.gov API v2 | No auth. Keep to about 3 requests per second or lower. |
| Trials (non-US) | ISRCTN, EU CTIS, WHO ICTRP | Phase 2 or later. |
| Papers, citations | Europe PMC, PubMed E-utilities | |
| Scholarly graph | OpenAlex | API key required since Feb 2026; free tier is $1 of usage per day; ID and DOI lookups are free. |
| Retractions, DOIs | Crossref | Includes Retraction Watch data. |
| Funding | NIH RePORTER, UKRI Gateway to Research | |
| Companies | Companies House API, SEC EDGAR | |
| Approvals | openFDA, EMA, MHRA | |
| New claims | EurekAlert and university press RSS, Google News RSS, GDELT | Phase 3. |

## 5. Pipeline

1. **Ingest** candidate articles (Phase 1: manual entry via CLI or CSV; Phase 3: feeds).
2. **Extract** claim, entities, DOI and promised timeline with a generative LLM. Output validated against a schema.
3. **Resolve entities** to external IDs. Compound names change over time (lab name, company code, INN), so store synonyms and keep every match reviewable.
4. **Poll** registries per claim on a schedule (weekly by default). Diff against stored state. Each change becomes an `evidence_event`.
5. **Derive status** with rules.
6. **Review queue**: any event below a confidence threshold, and every entity match, stays `reviewed = false` and is not published until approved.
7. **Publish** a static site build.
8. **Notify** subscribers of published status changes.

### Decision-model integration (Phase 4, design for it now)

Bounded classification steps go through one `decide(step, state, options) -> {choice, probabilities, confidence}` interface so the backend can be swapped:

- Backend A (default): generative LLM with constrained output.
- Backend B: hosted decision model (TypeSafe Jev).
- Backend C: self-hosted small model with a trained option head and temperature scaling (the "build your own decision model" approach).

Steps using `decide`: triage (is this a breakthrough claim), vertical, evidence stage (in vitro, animal, early human, late human), event typing, entity-match gate, review routing.

Log every call to `decision_log`. Human review writes `human_label`, which becomes the calibration and evaluation set. Evaluate against human labels, never against another model's output. Entity matching always keeps a human check.

Not using `decide`: extraction, summaries, status derivation.

## 6. Site

Static site, rebuilt after each publish.

- `/` : one input box (search or paste a news URL), plus recent status changes.
- `/{claim-slug}` : status, promised-versus-actual timeline, evidence events with sources, follow button. Slugs are short and guessable, for example `/tooth-regrowth-usag1`.
- `/topic/{vertical}` : index per vertical.
- `/it-happened` : claims that reached approval.
- `/feed.xml` : status changes.
- Open Graph status card image per claim: headline, date announced, promised timeline, current status, days overdue.
- Footer on every page: not medical advice; a registered trial is not a treatment option; data sources and last-checked date.

Later (not Phase 1): reply bot, browser extension, forecasts, outlet track records, embeddable widget, public API.

## 7. Stack and hosting

Proposed defaults; challenge them if there is a better fit.

- Python 3.12 managed with `uv` for pipeline and CLI.
- Postgres 16. Migrations checked in.
- Astro for the static site, reading a JSON export from the pipeline.
- Docker Compose for local and production.
- Scheduling: cron inside Compose (n8n is available on the host if useful).
- LLM provider and model set by environment variables. No model IDs hardcoded.
- Secrets via `.env`, never committed. Provide `.env.example`.

Hosting split:

- **Pipeline and database**: Mac mini M4 at home (reachable over Tailscale). Batch work that tolerates downtime.
- **Public site**: static output pushed to a CDN or small VPS. Nothing public is served from the home connection.

## 8. Phases

### Phase 1: hand-curated backfill (target 2 to 3 weeks)

- First vertical: **tooth and gum regrowth** (assumed default; confirm before starting).
- Repo scaffold, schema, migrations, CLI to add a claim and its source articles.
- LLM extraction with schema validation.
- ClinicalTrials.gov, Europe PMC and Crossref clients.
- Status rules with unit tests.
- Review CLI (approve or reject events and matches).
- Static site with claim pages, topic index and status cards.
- 50 to 100 claims from 2015 to 2020 entered and reviewed.

Acceptance: `docker compose up` gives a working pipeline and a locally built site; every published status lists its evidence with source links; rule tests pass; a seeded example claim round-trips from article URL to published page.

### Phase 2: automated tracking

Scheduled polling, diffing, event creation, review queue, email subscriptions with double opt-in, RSS feed, remaining source clients.

### Phase 3: automated ingestion

Feed ingestion, triage, deduplication against existing claims, paste-a-URL lookup.

### Phase 4: decision models and growth features

Swap bounded steps to a decision-model backend once a few hundred human labels exist. Add reply bot, extension, forecasts, widget.

## 9. Conventions and guardrails

- Accuracy is the brand. Nothing reaches the public site without `reviewed = true`.
- "No signal" is never worded as "dead" or "abandoned".
- Store the raw API payload and fetch timestamp for every evidence event.
- Summarise and link to news articles; never store or display full article text.
- Subscriber emails are the only personal data. UK GDPR applies: double opt-in, one-click unsubscribe, deletion on request.
- Respect robots.txt and published rate limits. Identify the client with a contact User-Agent.
- Tests for status rules and each source client (recorded fixtures, no live calls in CI).
- Small commits, conventional commit messages, a README that explains setup in under ten commands.

## 10. Open questions

1. Final name and domain.
2. Confirm the first vertical.
3. Public site host: CDN or VPS.
4. Email provider for alerts.
5. LLM provider and budget ceiling per month.
6. Licence for the code and for the published dataset.
