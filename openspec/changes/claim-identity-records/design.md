# Design

## Context

See `proposal.md` for why. What exists that this rests on, read from `main` on 2026-11-18:

- `claim.indication` is text. `entity` rows belong to one claim, and one intervention entity per claim is enforced by `uq_entity_intervention_per_claim` (Postgres in `db/models.py`, and the same in `store/schema.sql` for D1).
- `entity_match` names a trial by `source_name` and `external_id` only. `registry_trial` is a separate table keyed the same way, with `raw_payload` holding the whole registry record, `derivedSection` included.
- `claim_term` holds a claim's MeSH condition and intervention terms with a `fit` of exact, broader or kind (`knowledge-cards`). `clinical/categories.py` `trial_terms` reads a trial's condition descriptors from the payload. `clinical/vocabulary.py` holds descriptors with their tree numbers. `events/trial_facts.py` reads arm types.
- `entity_substance` holds the one substance a substance registry lists an intervention under, with its codes.
- The D1 store (`cloudflare-source-of-truth`, about half done) mirrors the Postgres tables and merges every writer's records on natural keys. Its `claim` table already has an `origin` column that allows `registry`.
- Production holds real claims, so the initial migration is no longer regenerated (CLAUDE.md).

## Goals / Non-Goals

**Goals:**

- A claim's identity is two foreign keys, enforced by the store.
- Grouping a trial into a claim is a lookup on keys the trial already carries, by rule.
- Every existing claim keeps working through the move, with or without records.
- Postgres and D1 get the same shape in the same pull request, so neither store falls behind.

**Non-Goals:**

- A combination of agents as one intervention record.
- Records for papers, people, institutions or companies.
- Any wording on the site. The export carries keys; the site shows the indication label it shows today.

## Decisions

### 1. The condition key is the registry's own descriptor, at the level the registry files the trial

A claim's condition record is the descriptor its approved exact condition term names. A trial's conditions are the descriptors the registry lists in `conditionBrowseModule`, excluding ancestors the registry adds as browse leaves. The population a trial enrols within that descriptor (a marker, a stage, a line of treatment) is shown on the trial's row of the claim and is not part of the claim's identity.

This is the reading the operator was asked to confirm on 2026-11-18: that a trial in HER2-positive metastatic breast cancer belongs to the claim for its drug and breast neoplasms. MeSH itself has narrower descriptors for some populations (for example triple negative breast neoplasms); when the registry files a trial under one, the trial's key is that narrower descriptor and it groups there.

*Instead of* the eligibility criteria as part of the key: that is what the detailed review of `registry-drafted-claims` tested, and it made almost every trial its own claim. *Instead of* the search indication words: they drop the very words that tell populations apart and were never meant as a key.

A claim for a broader descriptor does not take trials filed under a narrower one by key alone. Preparation still finds them by name and scores them for the claim's indication, as today. Whether coverage should count a trial under an ancestor's claim is left to the coverage report's reasons, not the key.

### 2. The intervention key prefers a substance identifier, then a descriptor, then the name

A substance registry's identifier is the most exact key for a drug and is already stored (`entity_substance`). A MeSH intervention descriptor is next. A name compared ignoring case and spacing is last, for a new code with neither. When a better key is found for a record keyed on a name, the key is added to the same record; two records that turn out to be one are merged by the existing `claim merge` path extended to intervention records.

*Instead of* one entity per claim, kept as today: synonyms would keep being added to one claim's entity and missed by the others, and the duplicate check would keep comparing strings.

### 3. A trial's tested intervention is what its experimental arm adds

The added agent is the set of interventions an experimental arm lists minus those any placebo, sham, active comparator or no-intervention arm lists. Exactly one added agent is recorded. None or several, or a trial with no arms, records nothing and a reason. This replaces `name_under_test`, which takes the first named intervention and so picks a chemotherapy backbone in many combination trials, for grouping only; the news search keeps using `search_name`.

### 4. The new keys sit beside the old fields until every claim has them

`claim.condition_id` and `claim.intervention_id` are nullable at first. The unique index on the pair is partial: both set, and the claim not merged. The string and synonym duplicate check stays for claims with no condition record. `indication` stays as the label. Nothing is dropped in this change.

### 5. A claim's match points to the stored trial

`entity_match.registry_trial_id` is a nullable key, filled when the trial is stored and by a backfill for existing matches. The text identifiers stay, because a match can name a trial the corpus does not hold.

### 6. One shape, two stores

Each schema step lands as an Alembic migration and as a D1 migration under `store/ingest/migrations/` with `store/schema.sql` updated, and the merge's natural keys gain the two records (condition by descriptor, intervention by its key). The existing comparison of the two stores' exports covers it.

## Risks / Trade-offs

- [Many trials have no single added agent] → Counted per reason in task 2.4 before any grouping uses the keys. If the share is large, combinations become their own change; they are listed, not guessed.
- [Existing claims without an approved exact condition term] → They keep the text rule and are listed by `thenwhat coverage`. `knowledge-cards` approval by rule fills most; the rest are the operator's.
- [Two existing claims turn out to share a pair] → The backfill reports them and does not set the second claim's keys; each is merged with `thenwhat claim merge` before the unique index is added.
- [A synonym now reaches every claim of a drug] → Intended. The search is still within each claim's indication, and every claim it touches is marked due for a search.
- [D1 and Postgres drift] → Same pull request for both; the export comparison fails if they differ.

## Migration Plan

1. Add the tables and nullable columns in both stores. No behaviour changes.
2. Work out every stored trial's coded terms from payloads already held. No requests.
3. Backfill intervention records from entities and their substances, merging same-key entities; backfill condition records from approved exact condition terms; report collisions.
4. Merge the reported duplicates, then add the partial unique index.
5. Switch the duplicate check, `entity rename` and synonym reads to the records.
6. Rollback: every step before 5 is additive and can be reverted by dropping the new columns and tables; step 5 is a code change behind the same pull request.
