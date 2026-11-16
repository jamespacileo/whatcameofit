-- The one merge path. Every writer's records enter the store by this list of statements and
-- no other: a device's backfill, the daily job, a reader's lookup, the store-side consumer,
-- the operator's audit, archive, merge and rename, the export's publication, the migration.
--
-- How it is run
--   * Sent as one D1 batch, in this order. A batch is one transaction: all of it or none.
--   * Only the first two statements take a parameter, ?1, the run. They put an accepted run
--     in `merging`; every later statement reads the `staged*` views, which are empty unless
--     the run is there. So a refused run, a run already merged and an unknown run all run
--     the whole list and change nothing.
--   * Nothing is read by the client between statements. A rule that branches is a WHERE.
--   * A record is named by natural key inside its JSON body (`s.body ->> 'slug'`). The body
--     of each kind is listed in store/README.md.
--   * A statement is split from the next by a line holding only `;`.
--
-- Above each statement: its conflict rule, in one sentence.

-- =========================================================================================
-- 0. Begin
-- =========================================================================================

-- A run whose step versions are older than the store accepts is refused, naming the step.
UPDATE run SET status = 'refused', refusal = (
    SELECT 'step ' || rs.step || ' is at version ' || rs.version || ', the store accepts ' || ss.version
    FROM run_step rs JOIN store_step ss ON ss.step = rs.step
    WHERE rs.run_id = run.id AND rs.version < ss.version LIMIT 1)
WHERE id = ?1 AND status = 'registered'
  AND EXISTS (SELECT 1 FROM run_step rs JOIN store_step ss ON ss.step = rs.step
              WHERE rs.run_id = run.id AND rs.version < ss.version)
;
-- Only a registered run is merged: one already merged, refused or unknown stages nothing.
INSERT INTO merging (id, run_id) SELECT 1, id FROM run WHERE id = ?1 AND status = 'registered'
;

-- =========================================================================================
-- 1. Payloads
-- =========================================================================================

-- A payload is kept once per checksum; one already held is left as it is.
INSERT INTO payload (sha256, bytes, body, r2_key, added_run)
SELECT s.body ->> 'sha256', s.body ->> 'bytes', s.body ->> 'body', s.body ->> 'r2_key', s.run_id
FROM staged s WHERE s.kind = 'payload'
ON CONFLICT (sha256) DO NOTHING
;

-- =========================================================================================
-- 2. Claims
-- =========================================================================================

-- A claim is added when no claim has its slug, now or formerly; on a claim already held,
-- only a decision that outranks the stored one is taken (a person's over an assistant's
-- over a rule's or the seed's; at equal rank the later), and nothing else is overwritten.
INSERT INTO claim (slug, headline, summary, vertical, approach, indication, first_reported_date,
                   evidence_stage, current_status, overlay_years, status_updated_at, origin,
                   review_state, reviewed_at, reviewed_by, awaiting_audit_at, created_at,
                   added_run, changed_run)
SELECT s.body ->> 'slug', s.body ->> 'headline', s.body ->> 'summary', s.body ->> 'vertical',
       s.body ->> 'approach', s.body ->> 'indication', s.body ->> 'first_reported_date',
       s.body ->> 'evidence_stage', coalesce(s.body ->> 'current_status', 'no_trial_found'),
       s.body ->> 'overlay_years', s.body ->> 'status_updated_at', s.body ->> 'origin',
       coalesce(s.body ->> 'review_state', 'pending'), s.body ->> 'reviewed_at', s.body ->> 'reviewed_by',
       s.body ->> 'awaiting_audit_at', s.body ->> 'created_at', s.run_id, s.run_id
FROM staged s
WHERE s.kind = 'claim'
  AND NOT EXISTS (SELECT 1 FROM claim_alias a WHERE a.slug = s.body ->> 'slug')
ON CONFLICT (slug) DO UPDATE SET
  review_state = excluded.review_state, reviewed_at = excluded.reviewed_at,
  reviewed_by = excluded.reviewed_by, changed_run = excluded.changed_run
WHERE excluded.review_state <> 'pending'
  AND (excluded.review_rank > claim.review_rank
       OR (excluded.review_rank = claim.review_rank AND excluded.reviewed_at > claim.reviewed_at))
;
-- The audit mark a run states is carried onto a claim already held, and no merge clears one.
UPDATE claim SET awaiting_audit_at = s.body ->> 'awaiting_audit_at', changed_run = s.run_id
FROM staged_of_claim s
WHERE s.kind = 'claim' AND claim.id = s.claim_id
  AND claim.awaiting_audit_at IS NULL AND claim.added_run <> s.run_id
  AND s.body ->> 'awaiting_audit_at' IS NOT NULL
;
-- A status is derived, not decided: the one derived later replaces the stored one.
UPDATE claim SET current_status = s.body ->> 'current_status', overlay_years = s.body ->> 'overlay_years',
                 evidence_stage = coalesce(s.body ->> 'evidence_stage', claim.evidence_stage),
                 status_updated_at = s.body ->> 'status_updated_at', changed_run = s.run_id
FROM staged_of_claim s
WHERE s.kind = 'claim' AND claim.id = s.claim_id AND claim.added_run <> s.run_id
  AND s.body ->> 'status_updated_at' > coalesce(claim.status_updated_at, '')
;
-- A source article is added when its claim has none at that address; one held is left.
INSERT INTO source_article (claim_id, url_key, url, outlet, title, published_date, content_hash,
                            archive_url, added_run)
SELECT s.claim_id, s.body ->> 'url_key', s.body ->> 'url', s.body ->> 'outlet', s.body ->> 'title',
       s.body ->> 'published_date', s.body ->> 'content_hash', s.body ->> 'archive_url', s.run_id
FROM staged_of_claim s WHERE s.kind = 'source_article'
ON CONFLICT (claim_id, url_key) DO NOTHING
;
-- A claim's first report is the earliest any writer knows of.
UPDATE claim SET first_reported_date = n.earliest
FROM (SELECT s.claim_id, min(s.body ->> 'published_date') AS earliest
      FROM staged_of_claim s WHERE s.kind = 'source_article' GROUP BY s.claim_id) n
WHERE claim.id = n.claim_id AND n.earliest < coalesce(claim.first_reported_date, '9999')
;
-- A promise is added when its article has none in those words; one held is left.
INSERT INTO promise (claim_id, source_article_id, description, parsed_date, added_run)
SELECT s.claim_id, s.source_article_id, s.body ->> 'description', s.body ->> 'parsed_date', s.run_id
FROM staged_of_article s WHERE s.kind = 'promise'
ON CONFLICT (source_article_id, description) DO NOTHING
;
-- A reported statement is added when its article has none with that text key; on one held,
-- only a decision that outranks the stored one is taken.
INSERT INTO reported_statement (claim_id, source_article_id, text, text_key, kind, firmness, speaker,
                                basis, confidence, decision_ref, article_read_at, review_state,
                                reviewed_at, reviewed_by, created_at, added_run, changed_run)
SELECT s.claim_id, s.source_article_id, s.body ->> 'text', s.body ->> 'text_key', s.body ->> 'kind',
       s.body ->> 'firmness', s.body ->> 'speaker', s.body ->> 'basis', s.body ->> 'confidence',
       s.body ->> 'decision_ref', s.body ->> 'article_read_at',
       coalesce(s.body ->> 'review_state', 'pending'), s.body ->> 'reviewed_at', s.body ->> 'reviewed_by',
       s.body ->> 'created_at', s.run_id, s.run_id
FROM staged_of_article s WHERE s.kind = 'reported_statement'
ON CONFLICT (source_article_id, text_key) DO UPDATE SET
  review_state = excluded.review_state, reviewed_at = excluded.reviewed_at,
  reviewed_by = excluded.reviewed_by, changed_run = excluded.changed_run
WHERE excluded.review_state <> 'pending'
  AND (excluded.review_rank > reported_statement.review_rank
       OR (excluded.review_rank = reported_statement.review_rank
           AND excluded.reviewed_at > reported_statement.reviewed_at))
;

-- =========================================================================================
-- 3. Entities, matches and terms
-- =========================================================================================

-- An entity is added when its claim has none of that type and name; one held is left.
INSERT INTO entity (claim_id, type, name, synonyms, search_phrases, is_origin_paper, doi, named_by, added_run)
SELECT s.claim_id, s.body ->> 'type', s.body ->> 'name', coalesce(s.body -> 'synonyms', '[]'),
       coalesce(s.body -> 'search_phrases', '[]'), coalesce(s.body ->> 'is_origin_paper', 0),
       s.body ->> 'doi', coalesce(s.body -> 'named_by', '["article"]'), s.run_id
FROM staged_of_claim s WHERE s.kind = 'entity'
ON CONFLICT (claim_id, type, name) DO NOTHING
;
-- An entity is linked to an article that named it once.
INSERT INTO entity_article (entity_id, source_article_id)
SELECT s.entity_id, a.id
FROM staged_of_entity s
JOIN source_article a ON a.claim_id = s.claim_id AND a.url_key = s.body ->> 'url_key'
WHERE s.kind = 'entity_article'
ON CONFLICT DO NOTHING
;
-- A match is added when its entity has none for that record; on one held, a decision that
-- outranks the stored one is taken with its score and reasons, so a person's rejection
-- stands against any rule's approval.
INSERT INTO entity_match (entity_id, source_name, external_id, score, record_summary, record_facts,
                          reasons, review_state, reviewed_at, reviewed_by, created_at, added_run, changed_run)
SELECT s.entity_id, s.body ->> 'source_name', s.body ->> 'external_id', s.body ->> 'score',
       s.body ->> 'record_summary', s.body -> 'record_facts', coalesce(s.body -> 'reasons', '[]'),
       coalesce(s.body ->> 'review_state', 'pending'), s.body ->> 'reviewed_at', s.body ->> 'reviewed_by',
       s.body ->> 'created_at', s.run_id, s.run_id
FROM staged_of_entity s WHERE s.kind = 'entity_match'
ON CONFLICT (entity_id, source_name, external_id) DO UPDATE SET
  review_state = excluded.review_state, reviewed_at = excluded.reviewed_at,
  reviewed_by = excluded.reviewed_by, score = excluded.score, reasons = excluded.reasons,
  record_summary = coalesce(excluded.record_summary, entity_match.record_summary),
  record_facts = coalesce(excluded.record_facts, entity_match.record_facts),
  changed_run = excluded.changed_run
WHERE excluded.review_state <> 'pending'
  AND (excluded.review_rank > entity_match.review_rank
       OR (excluded.review_rank = entity_match.review_rank AND excluded.reviewed_at > entity_match.reviewed_at))
;
-- A claim's term is added when the claim has none for that role and record; on one held,
-- a decision that outranks the stored one is taken with its score and fit.
INSERT INTO claim_term (claim_id, role, source_name, external_id, label, score, fit, reasons,
                        review_state, reviewed_at, reviewed_by, created_at, added_run, changed_run)
SELECT s.claim_id, s.body ->> 'role', s.body ->> 'source_name', s.body ->> 'external_id',
       s.body ->> 'label', s.body ->> 'score', s.body ->> 'fit', coalesce(s.body -> 'reasons', '[]'),
       coalesce(s.body ->> 'review_state', 'pending'), s.body ->> 'reviewed_at', s.body ->> 'reviewed_by',
       s.body ->> 'created_at', s.run_id, s.run_id
FROM staged_of_claim s WHERE s.kind = 'claim_term'
ON CONFLICT (claim_id, role, source_name, external_id) DO UPDATE SET
  review_state = excluded.review_state, reviewed_at = excluded.reviewed_at,
  reviewed_by = excluded.reviewed_by, score = excluded.score, fit = excluded.fit,
  changed_run = excluded.changed_run
WHERE excluded.review_state <> 'pending'
  AND (excluded.review_rank > claim_term.review_rank
       OR (excluded.review_rank = claim_term.review_rank AND excluded.reviewed_at > claim_term.reviewed_at))
;
-- A source's record of a term, an organisation, a paper or a substance is kept once; the
-- one fetched later replaces the stored one.
INSERT INTO source_record (kind, source_name, external_id, url, pubmed_id, body, payload_sha256,
                           fetched_at, added_run, changed_run)
SELECT s.body ->> 'kind', s.body ->> 'source_name', s.body ->> 'external_id', s.body ->> 'url',
       s.body ->> 'pubmed_id', s.body -> 'body', s.body ->> 'payload_sha256', s.body ->> 'fetched_at',
       s.run_id, s.run_id
FROM staged s WHERE s.kind = 'source_record'
ON CONFLICT (kind, source_name, external_id) DO UPDATE SET
  url = excluded.url, pubmed_id = excluded.pubmed_id, body = excluded.body,
  payload_sha256 = excluded.payload_sha256, fetched_at = excluded.fetched_at,
  changed_run = excluded.changed_run
WHERE excluded.fetched_at > source_record.fetched_at
;
-- An intervention has one substance; the one fetched later replaces the stored one.
INSERT INTO entity_substance (entity_id, source_name, external_id, codes, fetched_at, added_run, changed_run)
SELECT s.entity_id, s.body ->> 'source_name', s.body ->> 'external_id', coalesce(s.body -> 'codes', '[]'),
       s.body ->> 'fetched_at', s.run_id, s.run_id
FROM staged_of_entity s WHERE s.kind = 'entity_substance'
ON CONFLICT (entity_id) DO UPDATE SET
  source_name = excluded.source_name, external_id = excluded.external_id, codes = excluded.codes,
  fetched_at = excluded.fetched_at, changed_run = excluded.changed_run
WHERE excluded.fetched_at > entity_substance.fetched_at
;

-- =========================================================================================
-- 4. Evidence
-- =========================================================================================

-- An event that says something else than the approved event stored under its key is kept
-- apart, whole, with the reason, once however many runs bring it.
INSERT INTO evidence_conflict (claim_id, dedupe_key, content_sha256, payload_sha256, fetched_at,
                               event, reason, run_id)
SELECT s.claim_id, e.dedupe_key, s.body ->> 'content_sha256', s.body ->> 'payload_sha256',
       s.body ->> 'fetched_at', s.body, 'differs from the approved event stored', s.run_id
FROM staged_of_claim s
JOIN evidence_event e ON e.claim_id = s.claim_id AND e.dedupe_key = s.body ->> 'dedupe_key'
WHERE s.kind = 'evidence_event' AND e.review_state = 'approved'
  AND e.content_sha256 <> s.body ->> 'content_sha256'
ON CONFLICT (claim_id, dedupe_key, content_sha256) DO NOTHING
;
-- A claim with evidence newly kept apart is held for audit, whoever wrote it.
UPDATE claim SET awaiting_audit_at = (SELECT registered_at FROM run JOIN merging ON run_id = run.id),
                 changed_run = (SELECT run_id FROM merging)
WHERE awaiting_audit_at IS NULL
  AND id IN (SELECT c.claim_id FROM evidence_conflict c JOIN merging m ON m.run_id = c.run_id)
;
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT DISTINCT c.claim_id, 'audit_hold', 'evidence that differs: ' || c.dedupe_key, 'rule', r.registered_at, r.id
FROM evidence_conflict c JOIN merging m ON m.run_id = c.run_id JOIN run r ON r.id = m.run_id
;
-- An event is added when its claim has none under that key; one held and still pending is
-- replaced by a fetch that is not older; one held and decided is left to the rules below.
INSERT INTO evidence_event (claim_id, dedupe_key, entity_match_id, type, event_date, date_basis,
                            source_name, source_url, external_id, trial_phases, trial_state,
                            regulatory_outcome, summary, confidence, content_sha256, payload_sha256,
                            fetched_at, review_state, reviewed_at, reviewed_by, created_at,
                            added_run, changed_run)
SELECT s.claim_id, s.body ->> 'dedupe_key',
       (SELECT m.id FROM entity_match m JOIN entity e ON e.id = m.entity_id
        WHERE e.claim_id = s.claim_id AND e.type = s.body ->> 'match_entity_type'
          AND e.name = s.body ->> 'match_entity_name'
          AND m.source_name = s.body ->> 'match_source_name' AND m.external_id = s.body ->> 'match_external_id'),
       s.body ->> 'type', s.body ->> 'event_date', s.body ->> 'date_basis', s.body ->> 'source_name',
       s.body ->> 'source_url', s.body ->> 'external_id', s.body -> 'trial_phases', s.body ->> 'trial_state',
       s.body ->> 'regulatory_outcome', s.body ->> 'summary', s.body ->> 'confidence',
       s.body ->> 'content_sha256', s.body ->> 'payload_sha256', s.body ->> 'fetched_at',
       coalesce(s.body ->> 'review_state', 'pending'), s.body ->> 'reviewed_at', s.body ->> 'reviewed_by',
       s.body ->> 'created_at', s.run_id, s.run_id
FROM staged_of_claim s WHERE s.kind = 'evidence_event'
ON CONFLICT (claim_id, dedupe_key) DO UPDATE SET
  entity_match_id = coalesce(excluded.entity_match_id, evidence_event.entity_match_id),
  type = excluded.type, event_date = excluded.event_date, date_basis = excluded.date_basis,
  source_url = excluded.source_url, trial_phases = excluded.trial_phases, trial_state = excluded.trial_state,
  regulatory_outcome = excluded.regulatory_outcome, summary = excluded.summary,
  confidence = excluded.confidence, content_sha256 = excluded.content_sha256,
  payload_sha256 = excluded.payload_sha256, fetched_at = excluded.fetched_at,
  review_state = excluded.review_state, reviewed_at = excluded.reviewed_at,
  reviewed_by = excluded.reviewed_by, changed_run = excluded.changed_run
WHERE evidence_event.review_state = 'pending' AND excluded.fetched_at >= evidence_event.fetched_at
;
-- On a decided event that says the same, a decision that outranks the stored one is taken.
UPDATE evidence_event SET review_state = s.body ->> 'review_state', reviewed_at = s.body ->> 'reviewed_at',
                          reviewed_by = s.body ->> 'reviewed_by', changed_run = s.run_id
FROM staged_of_claim s
WHERE s.kind = 'evidence_event' AND evidence_event.claim_id = s.claim_id
  AND evidence_event.dedupe_key = s.body ->> 'dedupe_key'
  AND evidence_event.content_sha256 = s.body ->> 'content_sha256'
  AND evidence_event.review_state <> 'pending' AND coalesce(s.body ->> 'review_state', 'pending') <> 'pending'
  AND CASE s.body ->> 'reviewed_by' WHEN 'human' THEN 3 WHEN 'assistant' THEN 2 ELSE 1 END
      > evidence_event.review_rank
;
-- A later fetch that says the same of a decided event becomes its payload: the record
-- fetched most recently is the one facts are read from.
UPDATE evidence_event SET payload_sha256 = s.body ->> 'payload_sha256', fetched_at = s.body ->> 'fetched_at',
                          changed_run = s.run_id
FROM staged_of_claim s
WHERE s.kind = 'evidence_event' AND evidence_event.claim_id = s.claim_id
  AND evidence_event.dedupe_key = s.body ->> 'dedupe_key'
  AND evidence_event.content_sha256 = s.body ->> 'content_sha256'
  AND s.body ->> 'fetched_at' > evidence_event.fetched_at
;
-- A failure flag is added when its claim has none for that trial; one held is left.
INSERT INTO failure_flag (claim_id, trial_external_id, evidence_event_id, source_url, created_at, added_run)
SELECT s.claim_id, s.body ->> 'trial_external_id', e.id, s.body ->> 'source_url', s.body ->> 'created_at', s.run_id
FROM staged_of_claim s
JOIN evidence_event e ON e.claim_id = s.claim_id AND e.dedupe_key = s.body ->> 'dedupe_key'
WHERE s.kind = 'failure_flag'
ON CONFLICT (claim_id, trial_external_id) DO NOTHING
;
-- A trial has one read; a later read replaces it and its readings.
INSERT INTO trial_read (source_name, trial_id, input_hash, instructions_version, provider, model,
                        refusals, readings, read_at, added_run, changed_run)
SELECT s.body ->> 'source_name', s.body ->> 'trial_id', s.body ->> 'input_hash',
       s.body ->> 'instructions_version', s.body ->> 'provider', s.body ->> 'model',
       coalesce(s.body -> 'refusals', '[]'), coalesce(s.body -> 'readings', '[]'), s.body ->> 'read_at',
       s.run_id, s.run_id
FROM staged s WHERE s.kind = 'trial_read'
ON CONFLICT (source_name, trial_id) DO UPDATE SET
  input_hash = excluded.input_hash, instructions_version = excluded.instructions_version,
  provider = excluded.provider, model = excluded.model, refusals = excluded.refusals,
  readings = excluded.readings, read_at = excluded.read_at, changed_run = excluded.changed_run
WHERE excluded.read_at > trial_read.read_at
;

-- =========================================================================================
-- 5. The registry corpus
-- =========================================================================================

-- A trial is added when the registry's number is new; one held is replaced, whole, only by
-- a later fetch whose payload differs.
INSERT INTO registry_trial (registry_name, external_id, title, conditions, interventions,
                            intervention_names, phases, overall_status, start_date, sponsor_class,
                            search_name, search_indication, payload_sha256, fetched_at, checked_at,
                            added_run, changed_run)
SELECT s.body ->> 'registry_name', s.body ->> 'external_id', s.body ->> 'title',
       coalesce(s.body -> 'conditions', '[]'), coalesce(s.body -> 'interventions', '[]'),
       coalesce(s.body ->> 'intervention_names', ''), coalesce(s.body -> 'phases', '[]'),
       s.body ->> 'overall_status', s.body ->> 'start_date', s.body ->> 'sponsor_class',
       s.body ->> 'search_name', s.body ->> 'search_indication', s.body ->> 'payload_sha256',
       s.body ->> 'fetched_at', s.body ->> 'fetched_at', s.run_id, s.run_id
FROM staged s WHERE s.kind = 'registry_trial'
ON CONFLICT (registry_name, external_id) DO UPDATE SET
  title = excluded.title, conditions = excluded.conditions, interventions = excluded.interventions,
  intervention_names = excluded.intervention_names, phases = excluded.phases,
  overall_status = excluded.overall_status, start_date = excluded.start_date,
  sponsor_class = excluded.sponsor_class, search_name = excluded.search_name,
  search_indication = excluded.search_indication, payload_sha256 = excluded.payload_sha256,
  fetched_at = excluded.fetched_at, changed_run = excluded.changed_run
WHERE excluded.fetched_at > registry_trial.fetched_at
  AND excluded.payload_sha256 <> registry_trial.payload_sha256
;
-- A trial was last checked at the latest fetch any writer made of it, changed or not.
UPDATE registry_trial SET checked_at = s.body ->> 'fetched_at'
FROM staged s
WHERE s.kind = 'registry_trial' AND registry_trial.registry_name = s.body ->> 'registry_name'
  AND registry_trial.external_id = s.body ->> 'external_id'
  AND s.body ->> 'fetched_at' > registry_trial.checked_at
;
-- A state is written to a trial's history when it is not the last state seen.
INSERT INTO registry_trial_status (trial_id, seen_at, overall_status, run_id)
SELECT t.id, t.fetched_at, t.overall_status, t.changed_run
FROM registry_trial t JOIN merging m ON m.run_id = t.changed_run
WHERE coalesce(t.overall_status, '') IS NOT coalesce(
        (SELECT h.overall_status FROM registry_trial_status h
         WHERE h.trial_id = t.id ORDER BY h.seen_at DESC LIMIT 1), '')
   OR NOT EXISTS (SELECT 1 FROM registry_trial_status h WHERE h.trial_id = t.id)
ON CONFLICT DO NOTHING
;
-- A condition's load is remembered at the latest time it completed.
INSERT INTO registry_load (registry_name, condition, loaded_from, completed_at, changed_run)
SELECT s.body ->> 'registry_name', s.body ->> 'condition', s.body ->> 'loaded_from',
       s.body ->> 'completed_at', s.run_id
FROM staged s WHERE s.kind = 'registry_load'
ON CONFLICT (registry_name, condition) DO UPDATE SET
  loaded_from = excluded.loaded_from, completed_at = excluded.completed_at, changed_run = excluded.changed_run
WHERE excluded.completed_at > registry_load.completed_at
;
-- An article lead is added when its trial has none at that address; one held is left.
INSERT INTO article_lead (registry_trial_id, url_key, url, outlet, title, published_date, outlet_kind,
                          source_name, search_query, fetched_at, added_run)
SELECT s.trial_id, s.body ->> 'url_key', s.body ->> 'url', s.body ->> 'outlet', s.body ->> 'title',
       s.body ->> 'published_date', s.body ->> 'outlet_kind', s.body ->> 'source_name',
       s.body ->> 'search_query', s.body ->> 'fetched_at', s.run_id
FROM staged_of_trial s WHERE s.kind = 'article_lead'
ON CONFLICT (registry_trial_id, url_key) DO NOTHING
;

-- =========================================================================================
-- 6. Link leads
-- =========================================================================================

-- A lead is added when its address key is new; on one held, a score is taken only from a
-- higher triage version, so no device's older scoring replaces a newer one.
INSERT INTO link_lead (url_key, url_key_version, url, outlet, outlet_kind, title, first_shared_at,
                       origin, names_topic, screen_outcome, triage_score, triage_version,
                       read_outcome, read_detail, added_run, changed_run)
SELECT s.body ->> 'url_key', s.body ->> 'url_key_version', s.body ->> 'url', s.body ->> 'outlet',
       s.body ->> 'outlet_kind', s.body ->> 'title', s.body ->> 'first_shared_at', s.body ->> 'origin',
       coalesce(s.body ->> 'names_topic', 0), s.body ->> 'screen_outcome', s.body ->> 'triage_score',
       s.body ->> 'triage_version', s.body ->> 'read_outcome', s.body ->> 'read_detail', s.run_id, s.run_id
FROM staged s WHERE s.kind = 'link_lead'
ON CONFLICT (url_key) DO UPDATE SET
  triage_score = excluded.triage_score, triage_version = excluded.triage_version,
  changed_run = excluded.changed_run
WHERE excluded.triage_version > coalesce(link_lead.triage_version, 0)
;
-- A lead's first sharing is the earliest any writer knows of.
UPDATE link_lead SET first_shared_at = s.body ->> 'first_shared_at'
FROM staged s
WHERE s.kind = 'link_lead' AND link_lead.url_key = s.body ->> 'url_key'
  AND s.body ->> 'first_shared_at' < link_lead.first_shared_at
;
-- A lead is read once: a read outcome is taken only where the store has none.
UPDATE link_lead SET read_outcome = s.body ->> 'read_outcome', read_detail = s.body ->> 'read_detail',
                     changed_run = s.run_id
FROM staged s
WHERE s.kind = 'link_lead' AND link_lead.url_key = s.body ->> 'url_key'
  AND link_lead.read_outcome IS NULL AND s.body ->> 'read_outcome' IS NOT NULL
;
-- A lead is tied to the claim and source article its read gave, once, and stays tied.
UPDATE link_lead SET claim_id = k.claim_id, changed_run = s.run_id,
                     source_article_id = (SELECT a.id FROM source_article a
                                          WHERE a.claim_id = k.claim_id AND a.url_key = link_lead.url_key)
FROM staged s JOIN claim_key k ON k.slug = s.body ->> 'claim_slug'
WHERE s.kind = 'link_lead' AND link_lead.url_key = s.body ->> 'url_key' AND link_lead.claim_id IS NULL
;
-- A share is kept once per lead, place and time; a reader's asking, once per lead and day.
INSERT INTO link_share (link_lead_id, platform, community, shared_at, score, item_number, added_run)
SELECT s.link_lead_id, s.body ->> 'platform', s.body ->> 'community', s.body ->> 'shared_at',
       coalesce(s.body ->> 'score', 0), s.body ->> 'item_number', s.run_id
FROM staged_of_lead s WHERE s.kind = 'link_share'
ON CONFLICT DO NOTHING
;
-- A record screening found for a lead is kept once per reason.
INSERT INTO link_lead_link (link_lead_id, record_kind, record_key, reason, added_run)
SELECT s.link_lead_id, s.body ->> 'record_kind', s.body ->> 'record_key', s.body ->> 'reason', s.run_id
FROM staged_of_lead s WHERE s.kind = 'link_lead_link'
ON CONFLICT DO NOTHING
;
-- A reader's label of a headline is kept once per reader kind; the later label wins.
INSERT INTO link_lead_label (link_lead_id, labelled_by, label, labelled_at, changed_run)
SELECT s.link_lead_id, s.body ->> 'labelled_by', s.body ->> 'label', s.body ->> 'labelled_at', s.run_id
FROM staged_of_lead s WHERE s.kind = 'link_lead_label'
ON CONFLICT (link_lead_id, labelled_by) DO UPDATE SET
  label = excluded.label, labelled_at = excluded.labelled_at, changed_run = excluded.changed_run
WHERE excluded.labelled_at > link_lead_label.labelled_at
;
-- A lookup's reading of an article is kept once per lead; one from a higher read version
-- replaces it, and none is ever a claim.
INSERT INTO lead_reading (link_lead_id, intervention, indication, confidence, reasons, trials,
                          read_version, read_on, added_run, changed_run)
SELECT s.link_lead_id, s.body ->> 'intervention', s.body ->> 'indication', s.body ->> 'confidence',
       coalesce(s.body -> 'reasons', '[]'), coalesce(s.body -> 'trials', '[]'),
       s.body ->> 'read_version', s.body ->> 'read_on', s.run_id, s.run_id
FROM staged_of_lead s WHERE s.kind = 'lead_reading'
ON CONFLICT (link_lead_id) DO UPDATE SET
  intervention = excluded.intervention, indication = excluded.indication,
  confidence = excluded.confidence, reasons = excluded.reasons, trials = excluded.trials,
  read_version = excluded.read_version, read_on = excluded.read_on, changed_run = excluded.changed_run
WHERE excluded.read_version > lead_reading.read_version
;
-- A domain on no outlet list is counted by day and nothing of the address is kept.
INSERT INTO unlisted_domain_count (domain, day, asked)
SELECT s.body ->> 'domain', s.body ->> 'day', s.body ->> 'asked'
FROM staged s WHERE s.kind = 'unlisted_domain'
ON CONFLICT (domain, day) DO UPDATE SET asked = asked + excluded.asked
;

-- =========================================================================================
-- 7. Decisions, spend, measurements, ledger, slices
-- =========================================================================================

-- A decision has no natural key: it is kept once per run and place in the run.
INSERT INTO decision_log (run_id, seq, step, input_ref, backend, model, options, output, confidence,
                          error, human_label, created_at)
SELECT s.run_id, s.body ->> 'seq', s.body ->> 'step', s.body ->> 'input_ref', s.body ->> 'backend',
       s.body ->> 'model', coalesce(s.body -> 'options', '[]'), s.body -> 'output', s.body ->> 'confidence',
       s.body ->> 'error', s.body ->> 'human_label', s.body ->> 'created_at'
FROM staged s WHERE s.kind = 'decision'
ON CONFLICT DO NOTHING
;
-- Spend is kept once per run and place in the run, under the run's writer.
INSERT INTO llm_usage (run_id, seq, purpose, model, input_tokens, output_tokens, cost_usd, created_at)
SELECT s.run_id, s.body ->> 'seq', s.body ->> 'purpose', s.body ->> 'model', s.body ->> 'input_tokens',
       s.body ->> 'output_tokens', s.body ->> 'cost_usd', s.body ->> 'created_at'
FROM staged s WHERE s.kind = 'usage'
ON CONFLICT DO NOTHING
;
-- A day's totals for a step and writer are added to what the store holds for that day.
INSERT INTO measure_daily (day, step, step_version, writer, outcome, spans, records, reused, ran_seconds,
                           waited_seconds, waited_by_cause, requests_by_source, tokens_in, tokens_out,
                           cost_usd, inner_cost_usd, rows_written)
SELECT s.body ->> 'day', s.body ->> 'step', s.body ->> 'step_version', s.body ->> 'writer',
       s.body ->> 'outcome', s.body ->> 'spans', s.body ->> 'records', s.body ->> 'reused',
       s.body ->> 'ran_seconds', s.body ->> 'waited_seconds', coalesce(s.body -> 'waited_by_cause', '{}'),
       coalesce(s.body -> 'requests_by_source', '{}'), s.body ->> 'tokens_in', s.body ->> 'tokens_out',
       s.body ->> 'cost_usd', s.body ->> 'inner_cost_usd', s.body ->> 'rows_written'
FROM staged s WHERE s.kind = 'measure_daily'
ON CONFLICT (day, step, step_version, writer, outcome) DO UPDATE SET
  spans = spans + excluded.spans, records = records + excluded.records, reused = reused + excluded.reused,
  ran_seconds = ran_seconds + excluded.ran_seconds, waited_seconds = waited_seconds + excluded.waited_seconds,
  tokens_in = tokens_in + excluded.tokens_in, tokens_out = tokens_out + excluded.tokens_out,
  cost_usd = cost_usd + excluded.cost_usd, inner_cost_usd = inner_cost_usd + excluded.inner_cost_usd,
  rows_written = rows_written + excluded.rows_written
;
-- What a claim took is added to what the store holds for it.
INSERT INTO measure_claim (claim_id, first_seen_at, last_step_at, spans, ran_seconds, waited_seconds, cost_usd)
SELECT s.claim_id, s.body ->> 'first_seen_at', s.body ->> 'last_step_at', s.body ->> 'spans',
       s.body ->> 'ran_seconds', s.body ->> 'waited_seconds', s.body ->> 'cost_usd'
FROM staged_of_claim s WHERE s.kind = 'measure_claim'
ON CONFLICT (claim_id) DO UPDATE SET
  first_seen_at = min(first_seen_at, excluded.first_seen_at),
  last_step_at = max(last_step_at, excluded.last_step_at), spans = spans + excluded.spans,
  ran_seconds = ran_seconds + excluded.ran_seconds, waited_seconds = waited_seconds + excluded.waited_seconds,
  cost_usd = cost_usd + excluded.cost_usd
;
-- A ledger entry is kept once per record, step and version; the later attempt replaces it.
INSERT INTO work_entry (record_kind, record_key, step, step_version, outcome, attempts, requests_used,
                        fingerprint, stale, error, last_attempt_at, changed_run)
SELECT s.body ->> 'record_kind', s.body ->> 'record_key', s.body ->> 'step', s.body ->> 'step_version',
       s.body ->> 'outcome', s.body ->> 'attempts', s.body ->> 'requests_used', s.body ->> 'fingerprint',
       coalesce(s.body ->> 'stale', 0), s.body ->> 'error', s.body ->> 'last_attempt_at', s.run_id
FROM staged s WHERE s.kind = 'work_entry'
ON CONFLICT (record_kind, record_key, step, step_version) DO UPDATE SET
  outcome = excluded.outcome, attempts = excluded.attempts, requests_used = excluded.requests_used,
  fingerprint = excluded.fingerprint, stale = excluded.stale, error = excluded.error,
  last_attempt_at = excluded.last_attempt_at, changed_run = excluded.changed_run
WHERE excluded.last_attempt_at > work_entry.last_attempt_at
;
-- An outlet's icon is kept once per domain; the one fetched later replaces it.
INSERT INTO outlet_icon (domain, icon_url, media_type, content, fetched_at, changed_run)
SELECT s.body ->> 'domain', s.body ->> 'icon_url', s.body ->> 'media_type',
       unhex(s.body ->> 'content_hex'), s.body ->> 'fetched_at', s.run_id
FROM staged s WHERE s.kind = 'outlet_icon'
ON CONFLICT (domain) DO UPDATE SET
  icon_url = excluded.icon_url, media_type = excluded.media_type, content = excluded.content,
  fetched_at = excluded.fetched_at, changed_run = excluded.changed_run
WHERE excluded.fetched_at > outlet_icon.fetched_at
;
-- A slice a run finished is marked done whoever held it, and noted when its device did not.
INSERT INTO work_slice (platform, community, month, done_run, unheld)
SELECT s.body ->> 'platform', s.body ->> 'community', s.body ->> 'month', s.run_id, 1
FROM staged s WHERE s.kind = 'work_slice'
ON CONFLICT (platform, community, month) DO UPDATE SET
  done_run = excluded.done_run,
  unheld = coalesce(work_slice.device, '') IS NOT (SELECT coalesce(r.device, '') FROM run r WHERE r.id = excluded.done_run)
WHERE work_slice.done_run IS NULL
;

-- =========================================================================================
-- 8. The operator's actions, and the export's publication
--
-- Each is a staged record of kind `action` naming its claim by slug. Each action is two
-- statements or more: the first writes it to `claim_action` only where it will take
-- effect, the rest apply it. An action that would change nothing is counted as matched.
-- =========================================================================================

-- A claim is released from audit only while none of its evidence is still kept apart.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT s.claim_id, 'audit_clear', s.body ->> 'detail', s.body ->> 'decided_by', s.body ->> 'at', s.run_id
FROM staged_of_claim s JOIN claim c ON c.id = s.claim_id
WHERE s.kind = 'action' AND s.body ->> 'action' = 'audit_clear' AND c.awaiting_audit_at IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM evidence_conflict x WHERE x.claim_id = c.id AND x.state = 'open')
;
UPDATE claim SET awaiting_audit_at = NULL, changed_run = (SELECT run_id FROM merging)
WHERE id IN (SELECT a.claim_id FROM claim_action a JOIN merging m ON m.run_id = a.run_id
             WHERE a.action = 'audit_clear')
;
-- A claim not archived is archived with its reason; an archived one keeps its first reason.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT s.claim_id, 'archive', s.body ->> 'reason', s.body ->> 'decided_by', s.body ->> 'at', s.run_id
FROM staged_of_claim s JOIN claim c ON c.id = s.claim_id
WHERE s.kind = 'action' AND s.body ->> 'action' = 'archive' AND c.archived_at IS NULL
;
UPDATE claim SET archived_at = a.at, archive_reason = a.detail, changed_run = a.run_id
FROM claim_action a JOIN merging m ON m.run_id = a.run_id
WHERE a.action = 'archive' AND claim.id = a.claim_id
;
-- Only a person's action brings an archived claim back, and never one merged into another.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT s.claim_id, 'unarchive', s.body ->> 'detail', s.body ->> 'decided_by', s.body ->> 'at', s.run_id
FROM staged_of_claim s JOIN claim c ON c.id = s.claim_id
WHERE s.kind = 'action' AND s.body ->> 'action' = 'unarchive'
  AND c.archived_at IS NOT NULL AND c.merged_into IS NULL
;
UPDATE claim SET archived_at = NULL, archive_reason = NULL, changed_run = (SELECT run_id FROM merging)
WHERE id IN (SELECT a.claim_id FROM claim_action a JOIN merging m ON m.run_id = a.run_id
             WHERE a.action = 'unarchive')
;
-- A renamed claim keeps answering to its old slug; a new slug another claim holds fails
-- the batch, and nothing is renamed.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT c.id, 'rename', c.slug || ' -> ' || (s.body ->> 'new_slug'), s.body ->> 'decided_by', s.body ->> 'at', s.run_id
FROM staged s JOIN claim c ON c.slug = s.body ->> 'slug'
WHERE s.kind = 'action' AND s.body ->> 'action' = 'rename' AND c.slug <> s.body ->> 'new_slug'
;
DELETE FROM claim_alias
WHERE (slug, claim_id) IN (SELECT s.body ->> 'new_slug', c.id FROM staged s JOIN claim c ON c.slug = s.body ->> 'slug'
                           WHERE s.kind = 'action' AND s.body ->> 'action' = 'rename')
;
INSERT INTO claim_alias (slug, claim_id, added_run)
SELECT c.slug, c.id, s.run_id
FROM staged s JOIN claim c ON c.slug = s.body ->> 'slug'
WHERE s.kind = 'action' AND s.body ->> 'action' = 'rename' AND c.slug <> s.body ->> 'new_slug'
;
UPDATE claim SET slug = s.body ->> 'new_slug', changed_run = s.run_id
FROM staged s
WHERE s.kind = 'action' AND s.body ->> 'action' = 'rename' AND claim.slug = s.body ->> 'slug'
;
-- A claim merged into another gives it its articles, their promises and statements and
-- its leads, and is archived pointing at it; its own entities, matches and events stay
-- with it, and the claim that stays keeps every decision made on it.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT g.gone_id, 'merge', 'into ' || g.kept_slug, g.body ->> 'decided_by', g.body ->> 'at', g.run_id
FROM staged_claim_merge g
;
-- An article both claims hold stays with the claim that goes; every other moves.
UPDATE OR IGNORE source_article
SET claim_id = (SELECT g.kept_id FROM staged_claim_merge g WHERE g.gone_id = source_article.claim_id)
WHERE claim_id IN (SELECT gone_id FROM staged_claim_merge)
;
UPDATE promise SET claim_id = (SELECT a.claim_id FROM source_article a WHERE a.id = promise.source_article_id)
WHERE claim_id IN (SELECT gone_id FROM staged_claim_merge)
;
UPDATE reported_statement
SET claim_id = (SELECT a.claim_id FROM source_article a WHERE a.id = reported_statement.source_article_id)
WHERE claim_id IN (SELECT gone_id FROM staged_claim_merge)
;
UPDATE link_lead SET claim_id = (SELECT g.kept_id FROM staged_claim_merge g WHERE g.gone_id = link_lead.claim_id)
WHERE claim_id IN (SELECT gone_id FROM staged_claim_merge)
;
UPDATE claim_alias SET claim_id = (SELECT g.kept_id FROM staged_claim_merge g WHERE g.gone_id = claim_alias.claim_id)
WHERE claim_id IN (SELECT gone_id FROM staged_claim_merge)
;
-- The claim that stays is first reported when either was, and is due to be prepared again.
UPDATE claim SET first_reported_date = n.earliest, changed_run = n.run_id
FROM (SELECT g.kept_id, g.run_id, min(c.first_reported_date) AS earliest
      FROM staged_claim_merge g JOIN claim c ON c.id = g.gone_id GROUP BY g.kept_id) n
WHERE claim.id = n.kept_id AND n.earliest < coalesce(claim.first_reported_date, '9999')
;
INSERT INTO work_item (record_kind, record_key, step, due_since)
SELECT DISTINCT 'claim', g.kept_slug, 'prepare', g.body ->> 'at' FROM staged_claim_merge g
WHERE true
ON CONFLICT (record_kind, record_key, step) DO UPDATE SET state = 'due', attempts = 0, error = NULL,
                                                         due_since = excluded.due_since
;
-- Last, because the view above stops seeing a claim once it is marked merged.
UPDATE claim SET merged_into = a.kept_id, archived_at = coalesce(claim.archived_at, a.at),
                 archive_reason = coalesce(claim.archive_reason, 'merged ' || a.detail), changed_run = a.run_id
FROM (SELECT x.claim_id, x.at, x.detail, x.run_id, k.claim_id AS kept_id
      FROM claim_action x JOIN merging m ON m.run_id = x.run_id
      JOIN claim_key k ON k.slug = substr(x.detail, 6)
      WHERE x.action = 'merge') a
WHERE claim.id = a.claim_id OR claim.merged_into = a.claim_id
;
-- Evidence kept apart is accepted in place of the stored event, or dismissed, by a named
-- decider; either way it is no longer open and the claim may then be cleared.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT s.claim_id, s.body ->> 'action', x.dedupe_key, s.body ->> 'decided_by', s.body ->> 'at', s.run_id
FROM staged_of_claim s
JOIN evidence_conflict x ON x.claim_id = s.claim_id AND x.dedupe_key = s.body ->> 'dedupe_key'
                        AND x.content_sha256 = s.body ->> 'content_sha256' AND x.state = 'open'
WHERE s.kind = 'action' AND s.body ->> 'action' IN ('conflict_accept', 'conflict_dismiss')
;
UPDATE evidence_event SET
  type = x.event ->> 'type', event_date = x.event ->> 'event_date', date_basis = x.event ->> 'date_basis',
  source_url = x.event ->> 'source_url', trial_phases = x.event -> 'trial_phases',
  trial_state = x.event ->> 'trial_state', regulatory_outcome = x.event ->> 'regulatory_outcome',
  summary = x.event ->> 'summary', confidence = x.event ->> 'confidence',
  content_sha256 = x.content_sha256, payload_sha256 = x.payload_sha256, fetched_at = x.fetched_at,
  review_state = 'approved', reviewed_at = a.at, reviewed_by = a.decided_by, changed_run = a.run_id
FROM claim_action a JOIN merging m ON m.run_id = a.run_id
JOIN evidence_conflict x ON x.claim_id = a.claim_id AND x.dedupe_key = a.detail AND x.state = 'open'
WHERE a.action = 'conflict_accept' AND evidence_event.claim_id = x.claim_id
  AND evidence_event.dedupe_key = x.dedupe_key
;
UPDATE evidence_conflict SET state = CASE a.action WHEN 'conflict_accept' THEN 'accepted' ELSE 'dismissed' END,
                             resolved_run = a.run_id
FROM claim_action a JOIN merging m ON m.run_id = a.run_id
WHERE a.action IN ('conflict_accept', 'conflict_dismiss') AND evidence_conflict.state = 'open'
  AND evidence_conflict.claim_id = a.claim_id AND evidence_conflict.dedupe_key = a.detail
;
-- A published time is set once, on an approved claim that is neither held nor archived,
-- and no merge changes it afterwards.
INSERT INTO claim_action (claim_id, action, detail, decided_by, at, run_id)
SELECT s.claim_id, 'publish', NULL, 'rule', s.body ->> 'at', s.run_id
FROM staged_of_claim s JOIN claim c ON c.id = s.claim_id
WHERE s.kind = 'action' AND s.body ->> 'action' = 'publish' AND c.published_at IS NULL
  AND c.review_state = 'approved' AND c.archived_at IS NULL AND c.awaiting_audit_at IS NULL
;
UPDATE claim SET published_at = a.at, changed_run = a.run_id
FROM claim_action a JOIN merging m ON m.run_id = a.run_id
WHERE a.action = 'publish' AND claim.id = a.claim_id
;

-- =========================================================================================
-- 9. What the merge leaves due, and the claim search index
-- =========================================================================================

-- A reader's lead the run added is due for processing, once.
INSERT INTO work_item (record_kind, record_key, step, due_since)
SELECT 'link_lead', l.url_key, 'lead_process', r.registered_at
FROM link_lead l JOIN merging m ON m.run_id = l.added_run JOIN run r ON r.id = m.run_id
WHERE l.origin = 'reader'
ON CONFLICT DO NOTHING
;
-- A pending claim the run added is due to be prepared, once.
INSERT INTO work_item (record_kind, record_key, step, due_since)
SELECT 'claim', c.slug, 'prepare', r.registered_at
FROM claim c JOIN merging m ON m.run_id = c.added_run JOIN run r ON r.id = m.run_id
WHERE c.review_state = 'pending' AND c.archived_at IS NULL
ON CONFLICT DO NOTHING
;
-- The search words of each claim the run brought a claim, an entity or an action for are
-- written again from what the store now holds.
DELETE FROM claim_fts
WHERE rowid IN (SELECT claim_id FROM staged_of_claim WHERE kind IN ('claim', 'entity', 'action'))
;
INSERT INTO claim_fts (rowid, headline, indication, names)
SELECT c.id, c.headline, c.indication,
       (SELECT group_concat(e.name || ' ' || (SELECT coalesce(group_concat(j.value, ' '), '') FROM json_each(e.synonyms) j), ' ')
        FROM entity e WHERE e.claim_id = c.id AND e.type = 'intervention')
FROM claim c
WHERE c.id IN (SELECT claim_id FROM staged_of_claim WHERE kind IN ('claim', 'entity', 'action'))
;

-- =========================================================================================
-- 10. Report, reconcile, finish
-- =========================================================================================

-- The report: for each kind, the records whose parents were found, those the run added,
-- and those in conflict. A record whose parent was not found is in no count. (Written as
-- several statements: D1 allows few terms in one compound SELECT.)
INSERT INTO merge_report (run_id, kind, resolved, added)
SELECT run_id, kind, count(*), 0 FROM staged
WHERE kind IN ('payload', 'claim', 'source_record', 'trial_read', 'registry_trial', 'registry_load',
               'link_lead', 'unlisted_domain', 'decision', 'usage', 'measure_daily', 'work_entry',
               'outlet_icon', 'work_slice')
GROUP BY kind
;
INSERT INTO merge_report (run_id, kind, resolved, added)
SELECT run_id, kind, count(*), 0 FROM staged_of_claim
WHERE kind IN ('source_article', 'entity', 'claim_term', 'evidence_event', 'failure_flag', 'measure_claim', 'action')
GROUP BY kind
;
INSERT INTO merge_report (run_id, kind, resolved, added)
SELECT run_id, kind, count(*), 0 FROM staged_of_article
WHERE kind IN ('promise', 'reported_statement') GROUP BY kind
;
INSERT INTO merge_report (run_id, kind, resolved, added)
SELECT run_id, kind, count(*), 0 FROM staged_of_entity
WHERE kind IN ('entity_match', 'entity_substance', 'entity_article') GROUP BY kind
;
INSERT INTO merge_report (run_id, kind, resolved, added)
SELECT run_id, kind, count(*), 0 FROM staged_of_lead
WHERE kind IN ('link_share', 'link_lead_link', 'link_lead_label', 'lead_reading') GROUP BY kind
;
INSERT INTO merge_report (run_id, kind, resolved, added)
SELECT run_id, kind, count(*), 0 FROM staged_of_trial WHERE kind = 'article_lead' GROUP BY kind
;
-- Added is what carries this run as the run that added it; kinds that are replaced in
-- place or summed (a label, a ledger entry, a day's totals) are reported as matched.
UPDATE merge_report SET added = min(resolved, CASE kind
  WHEN 'payload'            THEN (SELECT count(*) FROM payload            WHERE added_run = merge_report.run_id)
  WHEN 'claim'              THEN (SELECT count(*) FROM claim              WHERE added_run = merge_report.run_id)
  WHEN 'source_article'     THEN (SELECT count(*) FROM source_article     WHERE added_run = merge_report.run_id)
  WHEN 'promise'            THEN (SELECT count(*) FROM promise            WHERE added_run = merge_report.run_id)
  WHEN 'reported_statement' THEN (SELECT count(*) FROM reported_statement WHERE added_run = merge_report.run_id)
  WHEN 'entity'             THEN (SELECT count(*) FROM entity             WHERE added_run = merge_report.run_id)
  WHEN 'entity_match'       THEN (SELECT count(*) FROM entity_match       WHERE added_run = merge_report.run_id)
  WHEN 'entity_substance'   THEN (SELECT count(*) FROM entity_substance   WHERE added_run = merge_report.run_id)
  WHEN 'claim_term'         THEN (SELECT count(*) FROM claim_term         WHERE added_run = merge_report.run_id)
  WHEN 'source_record'      THEN (SELECT count(*) FROM source_record      WHERE added_run = merge_report.run_id)
  WHEN 'evidence_event'     THEN (SELECT count(*) FROM evidence_event     WHERE added_run = merge_report.run_id)
  WHEN 'failure_flag'       THEN (SELECT count(*) FROM failure_flag       WHERE added_run = merge_report.run_id)
  WHEN 'trial_read'         THEN (SELECT count(*) FROM trial_read         WHERE added_run = merge_report.run_id)
  WHEN 'registry_trial'     THEN (SELECT count(*) FROM registry_trial     WHERE added_run = merge_report.run_id)
  WHEN 'article_lead'       THEN (SELECT count(*) FROM article_lead       WHERE added_run = merge_report.run_id)
  WHEN 'link_lead'          THEN (SELECT count(*) FROM link_lead          WHERE added_run = merge_report.run_id)
  WHEN 'link_share'         THEN (SELECT count(*) FROM link_share         WHERE added_run = merge_report.run_id)
  WHEN 'link_lead_link'     THEN (SELECT count(*) FROM link_lead_link     WHERE added_run = merge_report.run_id)
  WHEN 'lead_reading'       THEN (SELECT count(*) FROM lead_reading       WHERE added_run = merge_report.run_id)
  WHEN 'decision'           THEN (SELECT count(*) FROM decision_log       WHERE run_id = merge_report.run_id)
  WHEN 'usage'              THEN (SELECT count(*) FROM llm_usage          WHERE run_id = merge_report.run_id)
  WHEN 'action'             THEN (SELECT count(*) FROM claim_action       WHERE run_id = merge_report.run_id AND action <> 'audit_hold')
  ELSE 0 END)
WHERE run_id = (SELECT run_id FROM merging)
;
UPDATE merge_report SET
  conflicts = (SELECT count(*) FROM staged_of_claim s
               JOIN evidence_event e ON e.claim_id = s.claim_id AND e.dedupe_key = s.body ->> 'dedupe_key'
               WHERE s.kind = 'evidence_event' AND e.review_state = 'approved'
                 AND e.content_sha256 <> s.body ->> 'content_sha256')
WHERE run_id = (SELECT run_id FROM merging) AND kind = 'evidence_event'
;
-- A run whose records were not all found, or do not number what it stated, is undone: the
-- row below fails its CHECK, and with it the whole batch.
INSERT INTO merge_guard (run_id, reconciled)
SELECT m.run_id,
       NOT EXISTS (SELECT 1 FROM run_stated t
                   LEFT JOIN merge_report r ON r.run_id = t.run_id AND r.kind = t.kind
                   WHERE t.run_id = m.run_id AND t.records <> coalesce(r.resolved, 0))
   AND (SELECT count(*) FROM staged) = (SELECT coalesce(sum(records), 0) FROM run_stated WHERE run_id = m.run_id)
FROM merging m
;
DELETE FROM stg WHERE run_id = (SELECT run_id FROM merging)
;
-- A merged run says when; a reader's lookup says only the day.
UPDATE run SET status = 'merged',
               merged_at = CASE writer WHEN 'lookup' THEN date('now') ELSE strftime('%Y-%m-%dT%H:%M:%SZ', 'now') END
WHERE id = (SELECT run_id FROM merging)
;
DELETE FROM merging
;
