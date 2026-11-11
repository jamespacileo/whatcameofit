# Design

## Context

Greenfield. See `proposal.md` for motivation and scope, and `SPEC.md` for the full product vision.

Constraints that shape the approach:

- One operator enters and reviews everything. Review effort is the scarce resource.
- The pipeline and database run on a Mac mini at home. Nothing public is served from there, and Phase 1 deploys nothing.
- Status must be explainable from stored events, so events must carry everything the rules need (trial identifier, phase, state).
- CI makes no live network calls, so every external dependency (registries, article fetch, language model) needs a recorded or faked form.
- Later phases add polling, diffing and other decision backends. Phase 1 should not block them, and should not build them.

## Goals / Non-Goals

**Goals:**

- One seeded claim travels from article URL to built page with every step replayable offline.
- Status rules live in one pure module with no I/O, tested against every scenario in `specs/status-derivation`.
- Each external source sits behind one contract, so later clients (ISRCTN, openFDA, OpenAlex) are additions, not rewrites.
- The export file is the only interface between pipeline and site.

**Non-Goals:**

- Snapshot storage and a diff engine (Phase 2).
- An evaluation or calibration tool for decisions. Phase 1 only collects labels.
- A web interface for review. The CLI is enough for one operator.
- A `subscription` table. No personal data store is created before Phase 2 needs it.
- Public deployment, analytics, RSS.

## Decisions

### D1. One repository, two packages

```
thenwhat/
├── SPEC.md  CLAUDE.md  README.md  GLOSSARY.md  LICENSE  LICENSE-DATA
├── .env.example  compose.yaml
├── openspec/
├── docs/adr/  docs/sources.md
├── pipeline/
│   ├── pyproject.toml  Dockerfile  alembic.ini
│   ├── migrations/
│   ├── src/thenwhat/
│   │   ├── cli/        # claim, article, extract, entity, resolve, fetch, event, review, export
│   │   ├── db/         # models, session
│   │   ├── claims/     # slugs, promise parsing, CSV import
│   │   ├── sources/    # base contract, cache, rate limit; one module per registry
│   │   ├── llm/        # provider config, usage ledger, ceiling
│   │   ├── extract/    # article retrieval, extraction schema and agent
│   │   ├── decide/     # decide(), backends, decision log
│   │   ├── resolve/    # candidate matches
│   │   ├── events/     # record → evidence events, follow-up rule, dedupe
│   │   ├── status/     # pure rules
│   │   ├── review/     # queue, decisions, failure flags, labels
│   │   └── export/     # approved-only JSON
│   └── tests/fixtures/ # recorded registry and model responses
├── site/               # Astro; reads site/data/export.json (gitignored)
└── data/seed/          # claims CSV, seeded example
```

Alternative considered: separate repositories for pipeline and site. Rejected because the export schema changes with both sides and one operator maintains both.

### D2. Stack

Python 3.12 with `uv`; Typer and Rich for the CLI; SQLAlchemy 2 with Alembic; httpx; Pydantic for all schemas; pydantic-ai for model calls; ruff, ty and pytest. Postgres 16. Astro with Pagefind for search and build-time status card images. Docker Compose.

- SQLAlchemy and Alembic over plain SQL files: migrations are generated from models and downgrade paths come for free. Cost is one more abstraction.
- Postgres over SQLite: Phase 2 runs scheduled writers next to interactive review, and JSONB suits raw payloads.
- pydantic-ai over a provider SDK: the provider and model are one configuration string, which satisfies "no model IDs hardcoded" without an adapter layer of our own.
- Pagefind over a search service: the site stays fully static.

### D3. Schema

| Table | Key columns |
|---|---|
| `claim` | id, slug, headline, summary, vertical, first_reported_date, evidence_stage (nullable), current_status, overlay_years (nullable), status_updated_at, published_at (nullable), review columns |
| `source_article` | id, claim_id, url, outlet, title, published_date, content_hash, archive_url; unique (claim_id, url) |
| `promise` | id, claim_id, source_article_id, description, parsed_date (nullable) |
| `entity` | id, claim_id, type, name, synonyms[], is_origin_paper |
| `entity_match` | id, entity_id, source_name, external_id, score, review columns; unique (entity_id, source_name, external_id) |
| `evidence_event` | id, claim_id, entity_match_id (nullable), type, event_date, date_basis, source_name, source_url, external_id, trial_phases[] (nullable), trial_state (nullable), summary, confidence, raw_payload (JSONB), fetched_at, dedupe_key (unique per claim), review columns |
| `failure_flag` | id, claim_id, trial_external_id, evidence_event_id, source_url, created_at |
| `decision_log` | id, step, input_ref, backend, model, options, output, confidence, error, human_label (nullable), created_at |
| `llm_usage` | id, purpose, model, input_tokens, output_tokens, cost_usd, created_at |
| `http_cache` | request_key, source_name, payload, fetched_at, expires_at |

"Review columns" are `review_state` (pending, approved, rejected), `reviewed_at`, `reviewed_by` (human, rule).

Entities stay per claim, as in `SPEC.md`. A shared entity table with a join would avoid repeating a company across claims, but it adds merge decisions that Phase 1 does not need.

### D4. Operator flow

```
claim add / import-csv ─▶ extract ─▶ review (draft claim, evidence stage)
        ─▶ resolve ─▶ review (matches) ─▶ fetch ─▶ review (events, failure flags)
        ─▶ status derived on every review decision ─▶ export ─▶ site build
```

Each arrow is a separate CLI command, so every step can be re-run on its own. `fetch` and `resolve` are idempotent.

### D5. Trial events from one record

Phase 1 reads the current ClinicalTrials.gov record once and builds up to four events from its dated fields. Field names below are expected and must be confirmed when fixtures are recorded.

| Event | State | Date taken from | Condition |
|---|---|---|---|
| trial registered | | first-posted date | always |
| trial status change | started | start date | start date is actual, not estimated |
| trial status change | completed, terminated, withdrawn, suspended | completion date if actual, else last-update date | overall status is one of these |
| trial results posted | | results first-posted date | record has results |

`date_basis` stores which field was used and is shown on the claim page when it is the last-update date, since that date is an approximation.

Alternative considered: rebuild every past status from the registry's record history. Deferred; it needs an endpoint whose terms are unchecked and Phase 2 diffing gives the same result going forward.

### D6. Deduplication key

`dedupe_key` is `source_name | external_id | type | state`, with the state empty for types that have none. The state is included so that the started and completed events of one trial can coexist, and so that Phase 2 can add later status changes. Manual events use the source URL as `external_id` when no registry identifier exists.

This refines the key agreed earlier (source, external identifier, type), which would have allowed only one status change per trial.

### D7. Confidence and rule approval

- Trial events built from a human-approved match: confidence 1.0, approved by rule. The human already confirmed the trial belongs to the claim, and the event is a direct reading of a registry field.
- Retraction events for the origin paper: confidence 1.0, approved by rule, for the same reason.
- Follow-up paper events: 0.9 when the paper shares an author and names the intervention, 0.6 when only one holds. Always pending.
- Manual events: confidence 1.0, always pending.
- Threshold: `REVIEW_CONFIDENCE_THRESHOLD`, default 0.95. Setting it above 1 sends every event to human review.

Alternative considered: human approval of every event. Rejected for trial events because it doubles the operator's work without adding a check the match approval has not already made. Any rule approval can still be reversed in review.

### D8. Status rules as a pure function

`derive(events, flags, first_reported_date, as_of) -> (status, overlay_years, explaining_event_ids)`. No database or clock access inside. Written test-first from the scenarios in `specs/status-derivation`, one test per scenario. Precedence: retracted, then approved, then the stage/failed/terminated/preclinical ladder, then the overlay.

The overlay depends on the as-of date, so the export recomputes it at export time. Stored status changes only when the result differs.

### D9. Decisions

`decide(step, state, options)` calls the configured backend and always writes one `decision_log` row. Backend A asks the language model for a choice and a probability per option through constrained output. These probabilities are self-reported, not calibrated; the log marks the backend so Phase 4 can calibrate against human labels. Backends B and C are not built. The interface carries nothing specific to any vendor.

### D10. Language model budget

Providers bill in US dollars, so the ceiling is `LLM_MONTHLY_BUDGET_USD` (example value 13, about £10). Cost per call is computed from token counts and two configured prices (`LLM_INPUT_USD_PER_MTOK`, `LLM_OUTPUT_USD_PER_MTOK`), because the model is not known to the code. The check runs before each call against the ledger sum for the calendar month, so overshoot is bounded by one call.

### D11. Source access and fixtures

All clients share one base that applies cache, rate limit, User-Agent and retry. The cache lives in Postgres (`http_cache`) so cached payloads survive container rebuilds. Tests replace the HTTP transport with recorded responses in `tests/fixtures/`, and a test-suite guard fails any test that opens a real socket.

Before each client is written, its current terms, authentication and rate limit are checked and noted in `docs/sources.md`.

### D12. Article retrieval

Order: robots.txt check, live fetch, Internet Archive availability lookup, then a request for pasted text. Text is kept in memory only, hashed, passed to extraction and dropped. It is never written to the database, cache, logs or fixtures; test fixtures use synthetic articles written for the purpose.

### D13. Event summaries are templates

Summaries for registry events are built from templates ("Phase 2 trial NCT… registered"), and paper events use the paper's title. No language model writes event summaries in Phase 1. This keeps them free, deterministic and safe to approve by rule.

### D14. Export contract

`export` writes one JSON file with a schema version, a generated-at time, the last-checked time, and approved claims with their promises, source articles, approved events and status explanation. A JSON Schema for it is checked in and validated on both sides: the pipeline validates before writing, the site validates before building.

### D15. Site

Astro static build. Routes: `/`, `/[slug]`, `/topic/[vertical]`, `/it-happened`, and a not-found page. Pagefind indexes headlines, summaries and entity synonyms. Status card images are rendered at build time, one per claim. A build-time check fails the build if a status label or overlay string contains verdict wording. Brand strings sit in one configuration file because the name is a placeholder.

Visual design follows the global workflow: an Impeccable design pass produces `PRODUCT.md` and `DESIGN.md` before page components are built.

### D16. Compose

Three services: `db` (Postgres 16), `pipeline` (runs migrations on start, then idles for `docker compose run pipeline thenwhat …`), `site` (builds from the export and serves a local preview). `docker compose up` on a clean checkout loads the seeded example so the preview is never empty.

### D17. Assumptions made without asking

Each is small and reversible. Say so if any is wrong.

- A trial registered under two phases counts as the lower one, so the site never overstates progress.
- CSV import is all-or-nothing.
- Operators can enter events by hand. Needed for approvals, company events and trials in registries that have no client yet.
- The evidence stage at announcement is stored on the claim once confirmed.
- Rule approval applies to trial and origin-retraction events only (D7).

## Risks / Trade-offs

- [Trials outside ClinicalTrials.gov are invisible to fetch. Japanese and EU dental trials may be listed only in jRCT, ISRCTN or CTIS, and this may include the seeded USAG-1 example] → Manual trial events with a registry link (see `specs/evidence-events`). Check where the seed trial is registered before building the round-trip test. Non-US clients arrive in Phase 2.
- [Dental materials are often regulated as devices, and device trials have no phase, so such claims stay at "trial registered" even after a trial completes] → The claim page always shows the events themselves. Revisit the stage ladder if more than a few backfill claims are affected.
- [Event dates taken from the last-update field are approximate] → `date_basis` is stored and shown.
- [Extraction may invent an entity or a DOI] → Drafts are pending until approved; a DOI is checked against the DOI registry during resolution.
- [Self-reported probabilities from the language model are not calibrated] → They only order the queue. Nothing is approved on them.
- [Review workload for 25 to 40 claims is unknown] → Rule approval for trial events; follow-up papers limited by the citation rule; measure after the first five claims and adjust the target.
- [Registry API terms or shapes may differ from what is expected here] → Terms check and fixture recording come before each client.
- [Summaries could drift close to article wording] → Length limit, own-words instruction, human approval of every draft.

## Open Questions

None of these changes the specs or tasks.

- Final name and domain. Needed before public launch.
- Email provider. Needed in Phase 2.
- Documentation for the hosted decision model named in `SPEC.md` as Backend B. Needed before Phase 4.
