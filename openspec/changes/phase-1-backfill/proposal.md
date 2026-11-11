# Proposal

## Why

News reports dental "regrowth" breakthroughs that are rarely followed up, and no public record shows what happened next. Phase 1 proves the core loop on a hand-curated backfill: news claim, sourced evidence, rule-derived status, human review, public page. Doing this before any automation fixes the accuracy rules while volumes are small enough to check every item by hand.

## What Changes

Greenfield. This change creates the first working version of the system (codename `thenwhat`).

- Claims, source articles and promised timelines entered by CLI or CSV. One claim is one intervention for one indication; each promise is its own record.
- LLM extraction of a draft claim from a news article, validated against a schema. Article text is used transiently and never stored.
- Clients for ClinicalTrials.gov, Europe PMC and Crossref behind one contract, with caching, rate limiting and a contact User-Agent.
- Entity resolution that proposes registry matches for a claim's interventions and papers. Every match needs human approval.
- Evidence events created by a one-shot fetch per claim from the dated fields of current registry records, plus manually entered events.
- Deterministic status rules: furthest standing trial stage, with `failed`, `terminated`, `approved`, `retracted`, and a no-signal overlay after 3 quiet years.
- Review CLI to approve or reject draft claims, matches and events. Review decisions become human labels.
- A `decide()` interface with an LLM backend and a decision log, used for two advisory steps (evidence stage, entity-match scoring).
- LLM provider and model from environment variables, with an enforced monthly spend ceiling.
- Static site built from a JSON export of approved data: claim pages, topic index, home with search, `/it-happened`, status card images, footer disclaimers.
- A reviewed backfill of 25 to 40 dental regeneration claims first reported from 2015 to 2020.

Agreed departures from `SPEC.md`:

- First vertical widened from "tooth and gum regrowth" to dental regeneration (enamel, dentine, periodontal, whole tooth). Target lowered from 50–100 to 25–40 claims.
- `promised_timeline` on the claim becomes separate promise records.
- `reviewed` boolean becomes a review state (pending, approved, rejected). Entity matches get their own reviewable records. Evidence events gain a fetch timestamp, a link to the match that produced them, and a deduplication key.
- `no_signal` is an overlay on a stage status, not a status that replaces it.
- The status card shows the promised date, not a "days overdue" count.

Not in this change (later phases): scheduled polling and diffing, reconstruction of trial status history, email subscriptions and the follow button, RSS feed, feed ingestion and triage, paste-a-URL lookup, the remaining source clients, public deployment, decision-model backends B and C.

## Capabilities

### New Capabilities

- `claims`: Claim identity, slugs, source articles, promised timelines, verticals, and manual or CSV entry.
- `claim-extraction`: Turning a news article into a draft claim with an LLM, without retaining article text.
- `source-clients`: Uniform, cached, rate-limited access to trial, literature and DOI registries.
- `entity-resolution`: Entities, synonyms, and human-confirmed matches to registry identifiers.
- `evidence-events`: Dated, sourced facts about a claim, how they are created from registry records, and how duplicates are prevented.
- `status-derivation`: The rules that turn approved evidence events into a claim status and its explanation.
- `review`: Review states, the review queue, approval and rejection, failure flags, and human labels.
- `decision-steps`: The single interface for bounded classification choices, its logging, and which steps use it.
- `llm-usage`: Configuration of the language model provider, usage ledger, and monthly spend ceiling.
- `site-publishing`: The export of approved data and the static public site built from it.

### Modified Capabilities

None. No specs exist yet.

## Impact

- **Code**: new repository with a Python pipeline and CLI, Postgres schema and migrations, an Astro site, and Docker Compose for local use.
- **External services**: ClinicalTrials.gov API v2, Europe PMC, Crossref, the Internet Archive availability lookup, and the Anthropic API (default provider; any provider can be configured).
- **Cost**: LLM spend capped at about £10 per month.
- **Data**: no personal data is collected in this change. Registry payloads keep their own licence terms; project code is MIT and the published dataset is CC BY 4.0.
- **Operations**: runs locally only. Nothing is deployed publicly.
- **People**: the backfill needs operator time to enter and review 25 to 40 claims.
