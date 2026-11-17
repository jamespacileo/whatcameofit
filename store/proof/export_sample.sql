-- A sample of the working Postgres database in the store's natural-key form: one JSON
-- object a line, {kind, key, body}. Read-only: the session refuses any write.
--
-- It is also the migration's mapping in small: each SELECT says how a Postgres table
-- becomes a staged kind. The sample is every fifth claim with its records, about 5,000
-- trials, and the scored leads tied to those claims plus one in 200 of the rest.
--
-- Nothing here is article text. Titles are the ones already stored; payload bodies leave
-- Postgres only for registry listing records, which are public registry data.
--
-- Stand-ins, each marked STAND-IN below, for what the pipeline will compute in Python:
-- a source article's address key, and an event's content checksum.

SET default_transaction_read_only = on;
\set ON_ERROR_STOP on
\pset tuples_only on
\pset format unaligned

-- ---- payloads -----------------------------------------------------------------------
-- A trial's listing record is small and stays in the row; an event's goes to R2, so only
-- its checksum and size are exported.
SELECT DISTINCT ON (sha) json_build_object('kind', 'payload', 'key', sha, 'body', json_build_object(
         'sha256', sha, 'bytes', bytes,
         'body', CASE WHEN bytes <= 524288 THEN txt END,
         'r2_key', CASE WHEN bytes > 524288 THEN 'payload/' || sha END))
FROM (SELECT encode(sha256(convert_to(raw_payload::text, 'UTF8')), 'hex') AS sha,
             octet_length(raw_payload::text) AS bytes, raw_payload::text AS txt
      FROM registry_trial t
      WHERE t.id % 97 = 0
         OR t.external_id IN (SELECT e.external_id FROM evidence_event e WHERE e.claim_id % 5 = 0)) p;

SELECT DISTINCT ON (sha) json_build_object('kind', 'payload', 'key', sha, 'body', json_build_object(
         'sha256', sha, 'bytes', bytes, 'r2_key', 'payload/' || sha))
FROM (SELECT encode(sha256(convert_to(raw_payload::text, 'UTF8')), 'hex') AS sha,
             octet_length(raw_payload::text) AS bytes
      FROM evidence_event WHERE claim_id % 5 = 0
      UNION ALL
      SELECT encode(sha256(convert_to(s.payload::text, 'UTF8')), 'hex'), octet_length(s.payload::text)
      FROM entity_substance s JOIN entity e ON e.id = s.entity_id WHERE e.claim_id % 5 = 0) p
WHERE sha NOT IN (SELECT encode(sha256(convert_to(raw_payload::text, 'UTF8')), 'hex') FROM registry_trial
                  WHERE id % 97 = 0);

-- ---- claims -------------------------------------------------------------------------
SELECT json_build_object('kind', 'claim', 'key', c.slug, 'body', json_build_object(
         'slug', c.slug, 'headline', c.headline, 'summary', c.summary, 'vertical', c.vertical,
         'approach', c.approach, 'indication', c.indication, 'first_reported_date', c.first_reported_date,
         'evidence_stage', c.evidence_stage, 'current_status', c.current_status,
         'overlay_years', c.overlay_years, 'status_updated_at', c.status_updated_at,
         'origin', CASE WHEN EXISTS (SELECT 1 FROM link_lead l WHERE l.claim_id = c.id) THEN 'backfill' ELSE 'entry' END,
         'review_state', c.review_state, 'reviewed_at', c.reviewed_at, 'reviewed_by', c.reviewed_by,
         'awaiting_audit_at', c.awaiting_audit_at, 'created_at', c.created_at))
FROM claim c WHERE c.id % 5 = 0;

-- Archive state and published time are not a claim's own fields in the store: they are
-- actions, so the migration replays them as the operator's.
SELECT json_build_object('kind', 'action', 'key', 'publish|' || c.slug, 'body', json_build_object(
         'action', 'publish', 'slug', c.slug, 'at', c.published_at))
FROM claim c WHERE c.id % 5 = 0 AND c.published_at IS NOT NULL;

SELECT json_build_object('kind', 'action', 'key', 'archive|' || c.slug, 'body', json_build_object(
         'action', 'archive', 'slug', c.slug, 'reason', c.archive_reason, 'decided_by', 'human', 'at', c.archived_at))
FROM claim c WHERE c.id % 5 = 0 AND c.archived_at IS NOT NULL;

-- STAND-IN: the address key is the pipeline's `address.key`; this is a rough copy of it.
SELECT DISTINCT ON (c.slug, url_key) json_build_object('kind', 'source_article', 'key', c.slug || '|' || url_key,
       'body', json_build_object('slug', c.slug, 'url_key', url_key, 'url', a.url, 'outlet', a.outlet,
         'title', a.title, 'published_date', a.published_date, 'content_hash', a.content_hash,
         'archive_url', a.archive_url))
FROM source_article a JOIN claim c ON c.id = a.claim_id,
     LATERAL (SELECT lower(regexp_replace(a.url, '^https?://(www\.)?|[?#].*$|/$', '', 'g')) AS url_key) k
WHERE c.id % 5 = 0;

SELECT DISTINCT ON (a.id, p.description) json_build_object('kind', 'promise',
       'key', c.slug || '|' || url_key || '|' || md5(p.description),
       'body', json_build_object('slug', c.slug, 'url_key', url_key, 'description', p.description,
                                 'parsed_date', p.parsed_date))
FROM promise p JOIN claim c ON c.id = p.claim_id JOIN source_article a ON a.id = p.source_article_id,
     LATERAL (SELECT lower(regexp_replace(a.url, '^https?://(www\.)?|[?#].*$|/$', '', 'g')) AS url_key) k
WHERE c.id % 5 = 0;

SELECT json_build_object('kind', 'reported_statement', 'key', c.slug || '|' || url_key || '|' || s.text_key,
       'body', json_build_object('slug', c.slug, 'url_key', url_key, 'text', s.text, 'text_key', s.text_key,
         'kind', s.kind, 'firmness', s.firmness, 'speaker', s.speaker, 'basis', s.basis,
         'confidence', s.confidence, 'decision_ref', 'statement:' || c.slug || '|' || url_key || '|' || s.text_key,
         'article_read_at', s.article_read_at, 'review_state', s.review_state,
         'reviewed_at', s.reviewed_at, 'reviewed_by', s.reviewed_by, 'created_at', s.created_at))
FROM reported_statement s JOIN claim c ON c.id = s.claim_id JOIN source_article a ON a.id = s.source_article_id,
     LATERAL (SELECT lower(regexp_replace(a.url, '^https?://(www\.)?|[?#].*$|/$', '', 'g')) AS url_key) k
WHERE c.id % 5 = 0;

-- ---- entities, matches, terms -------------------------------------------------------
SELECT DISTINCT ON (c.slug, e.type, e.name) json_build_object('kind', 'entity',
       'key', c.slug || '|' || e.type || '|' || e.name,
       'body', json_build_object('slug', c.slug, 'type', e.type, 'name', e.name,
         'synonyms', to_json(e.synonyms), 'search_phrases', to_json(e.search_phrases),
         'is_origin_paper', e.is_origin_paper::int, 'doi', e.doi,
         'named_by', (SELECT json_agg(v ORDER BY v) FROM unnest(e.named_by) v)))
FROM entity e JOIN claim c ON c.id = e.claim_id WHERE c.id % 5 = 0
ORDER BY c.slug, e.type, e.name, e.id;

SELECT json_build_object('kind', 'entity_match',
       'key', c.slug || '|' || e.type || '|' || e.name || '|' || m.source_name || '|' || m.external_id,
       'body', json_build_object('slug', c.slug, 'entity_type', e.type, 'entity_name', e.name,
         'source_name', m.source_name, 'external_id', m.external_id, 'score', m.score,
         'record_summary', m.record_summary, 'reasons', to_json(m.reasons),
         'review_state', m.review_state, 'reviewed_at', m.reviewed_at, 'reviewed_by', m.reviewed_by,
         'created_at', m.created_at))
FROM entity_match m JOIN entity e ON e.id = m.entity_id JOIN claim c ON c.id = e.claim_id
WHERE c.id % 5 = 0
  AND e.id = (SELECT min(e2.id) FROM entity e2 WHERE e2.claim_id = e.claim_id AND e2.type = e.type AND e2.name = e.name);

SELECT json_build_object('kind', 'claim_term',
       'key', c.slug || '|' || t.role || '|' || t.source_name || '|' || t.external_id,
       'body', json_build_object('slug', c.slug, 'role', t.role, 'source_name', t.source_name,
         'external_id', t.external_id, 'label', t.label, 'score', t.score, 'fit', t.fit, 'reasons', t.reasons,
         'review_state', t.review_state, 'reviewed_at', t.reviewed_at, 'reviewed_by', t.reviewed_by,
         'created_at', t.created_at))
FROM claim_term t JOIN claim c ON c.id = t.claim_id WHERE c.id % 5 = 0;

SELECT json_build_object('kind', 'source_record', 'key', 'term|' || r.source_name || '|' || r.external_id,
       'body', json_build_object('kind', 'term', 'source_name', r.source_name, 'external_id', r.external_id,
                                 'url', r.url, 'body', r.payload, 'fetched_at', r.fetched_at))
FROM term_record r
WHERE (r.source_name, r.external_id) IN (SELECT source_name, external_id FROM claim_term WHERE claim_id % 5 = 0);

SELECT json_build_object('kind', 'source_record', 'key', 'paper|' || r.source_name || '|' || r.identifier,
       'body', json_build_object('kind', 'paper', 'source_name', r.source_name, 'external_id', r.identifier,
                                 'pubmed_id', r.pubmed_id, 'body', r.payload, 'fetched_at', r.fetched_at))
FROM paper_record r WHERE r.id % 5 = 0;

SELECT json_build_object('kind', 'source_record', 'key', 'substance|' || s.source_name || '|' || s.external_id,
       'body', json_build_object('kind', 'substance', 'source_name', s.source_name, 'external_id', s.external_id,
         'url', s.url, 'payload_sha256', encode(sha256(convert_to(s.payload::text, 'UTF8')), 'hex'),
         'fetched_at', s.fetched_at))
FROM (SELECT DISTINCT ON (s.source_name, s.external_id) s.* FROM entity_substance s
      JOIN entity e ON e.id = s.entity_id WHERE e.claim_id % 5 = 0) s;

SELECT json_build_object('kind', 'entity_substance', 'key', c.slug || '|' || e.name,
       'body', json_build_object('slug', c.slug, 'entity_type', e.type, 'entity_name', e.name,
         'source_name', s.source_name, 'external_id', s.external_id, 'codes', to_json(s.codes),
         'fetched_at', s.fetched_at))
FROM entity_substance s JOIN entity e ON e.id = s.entity_id JOIN claim c ON c.id = e.claim_id
WHERE c.id % 5 = 0;

-- ---- evidence -----------------------------------------------------------------------
-- STAND-IN: the content checksum is of the fields a status is derived from.
SELECT json_build_object('kind', 'evidence_event', 'key', c.slug || '|' || e.dedupe_key,
       'body', json_build_object('slug', c.slug, 'dedupe_key', e.dedupe_key, 'type', e.type,
         'event_date', e.event_date, 'date_basis', e.date_basis, 'source_name', e.source_name,
         'source_url', e.source_url, 'external_id', e.external_id, 'trial_phases', to_json(e.trial_phases),
         'trial_state', e.trial_state, 'regulatory_outcome', e.regulatory_outcome, 'summary', e.summary,
         'confidence', e.confidence,
         'content_sha256', md5(concat_ws('|', e.type, e.event_date, e.trial_state, e.trial_phases::text,
                                         e.regulatory_outcome, e.external_id)),
         'payload_sha256', encode(sha256(convert_to(e.raw_payload::text, 'UTF8')), 'hex'),
         'fetched_at', e.fetched_at, 'review_state', e.review_state, 'reviewed_at', e.reviewed_at,
         'reviewed_by', e.reviewed_by, 'created_at', e.created_at))
FROM evidence_event e JOIN claim c ON c.id = e.claim_id WHERE c.id % 5 = 0;

SELECT json_build_object('kind', 'trial_read', 'key', r.source_name || '|' || r.trial_id,
       'body', json_build_object('source_name', r.source_name, 'trial_id', r.trial_id,
         'input_hash', r.input_hash, 'instructions_version', r.instructions_version,
         'provider', r.provider, 'model', r.model, 'refusals', r.refusals, 'read_at', r.read_at,
         'readings', coalesce((SELECT json_agg(json_build_object('outcome', g.outcome, 'kind', g.kind,
                       'field', g.field, 'words', g.words, 'number', g.number, 'unit', g.unit, 'code', g.code,
                       'confidence', g.confidence, 'decided_by', g.decided_by) ORDER BY g.outcome, g.kind)
                     FROM reading g WHERE g.trial_read_id = r.id), '[]'::json)))
FROM trial_read r WHERE r.id % 5 = 0;

-- ---- the registry corpus ------------------------------------------------------------
SELECT json_build_object('kind', 'registry_trial', 'key', t.registry_name || '|' || t.external_id,
       'body', json_build_object('registry_name', t.registry_name, 'external_id', t.external_id,
         'title', t.title, 'conditions', to_json(t.conditions), 'interventions', t.interventions,
         'intervention_names', coalesce((SELECT string_agg(concat_ws('; ', i ->> 'name',
                 (SELECT string_agg(o, '; ') FROM jsonb_array_elements_text(
                    CASE WHEN jsonb_typeof(i -> 'other_names') = 'array' THEN i -> 'other_names' ELSE '[]' END) o)), '; ')
               FROM jsonb_array_elements(t.interventions) i), ''),
         'phases', to_json(t.phases), 'overall_status', t.overall_status, 'start_date', t.start_date,
         'sponsor_class', t.sponsor_class, 'search_name', t.search_name,
         'search_indication', t.search_indication,
         'start_date_type', t.start_date_type, 'last_update_posted', t.last_update_posted, 'study_first_posted', t.study_first_posted, 'primary_completion_date', t.primary_completion_date, 'primary_completion_date_type', t.primary_completion_date_type, 'completion_date', t.completion_date, 'completion_date_type', t.completion_date_type, 'results_first_posted', t.results_first_posted, 'acronym', t.acronym, 'lead_sponsor_name', t.lead_sponsor_name,
         'has_results', t.has_results::int,
         'payload_sha256', encode(sha256(convert_to(t.raw_payload::text, 'UTF8')), 'hex'),
         'fetched_at', t.fetched_at))
FROM registry_trial t
WHERE t.id % 97 = 0
   OR t.external_id IN (SELECT e.external_id FROM evidence_event e WHERE e.claim_id % 5 = 0);

SELECT json_build_object('kind', 'work_entry', 'key', 'registry_trial|' || t.registry_name || '|' || t.external_id || '|' || w.step || '|' || w.step_version,
       'body', json_build_object('record_kind', 'registry_trial',
         'record_key', t.registry_name || '|' || t.external_id, 'step', w.step, 'step_version', w.step_version,
         'outcome', w.outcome, 'attempts', w.attempts, 'requests_used', w.requests_used,
         'fingerprint', w.fingerprint, 'stale', w.stale::int, 'error', w.error,
         'last_attempt_at', w.last_attempt_at))
FROM work_entry w JOIN registry_trial t ON t.id = w.record_id
WHERE w.record_kind = 'registry_trial' AND t.id % 97 = 0;

-- ---- link leads: listed outlets only, and only those scored, read, labelled or tied --
SELECT json_build_object('kind', 'link_lead', 'key', l.url_key, 'body', json_build_object(
         'url_key', l.url_key, 'url_key_version', l.url_key_version, 'url', l.url, 'outlet', l.outlet,
         'outlet_kind', l.outlet_kind, 'title', l.title, 'first_shared_at', l.first_shared_at,
         'origin', 'file', 'screen_outcome', l.screen_outcome, 'triage_score', l.triage_score,
         'triage_version', l.triage_version, 'read_outcome', l.read_outcome, 'read_detail', l.read_detail,
         'claim_slug', (SELECT c.slug FROM claim c WHERE c.id = l.claim_id AND c.id % 5 = 0)))
FROM link_lead l
WHERE l.outlet_kind <> 'unknown' AND l.screen_outcome IS DISTINCT FROM 'unlisted_outlet'
  AND ((l.claim_id IS NOT NULL AND l.claim_id % 5 = 0)
       OR (l.id % 200 = 0 AND l.claim_id IS NULL AND (l.triage_score IS NOT NULL OR l.read_outcome IS NOT NULL)));

SELECT json_build_object('kind', 'link_share',
       'key', l.url_key || '|' || s.platform || '|' || s.community || '|' || s.shared_at,
       'body', json_build_object('lead_url_key', l.url_key, 'platform', s.platform, 'community', s.community,
         'shared_at', s.shared_at, 'score', s.score, 'item_number', s.item_number))
FROM link_share s JOIN link_lead l ON l.id = s.link_lead_id
WHERE l.outlet_kind <> 'unknown' AND l.screen_outcome IS DISTINCT FROM 'unlisted_outlet'
  AND ((l.claim_id IS NOT NULL AND l.claim_id % 5 = 0)
       OR (l.id % 200 = 0 AND l.claim_id IS NULL AND (l.triage_score IS NOT NULL OR l.read_outcome IS NOT NULL)));

-- ---- spend and decisions, a slice of each ---------------------------------------------
SELECT json_build_object('kind', 'usage', 'key', u.id::text, 'body', json_build_object(
         'seq', u.id, 'purpose', u.purpose, 'model', u.model, 'input_tokens', u.input_tokens,
         'output_tokens', u.output_tokens, 'cost_usd', u.cost_usd, 'created_at', u.created_at))
FROM llm_usage u WHERE u.id % 20 = 0;

-- A decision's reference is rewritten from a row id to a natural key. Only claim
-- references are rewritten here; the migration does the same for each kind of reference.
SELECT json_build_object('kind', 'decision', 'key', d.id::text, 'body', json_build_object(
         'seq', d.id, 'step', d.step, 'input_ref', 'claim:' || c.slug, 'backend', d.backend,
         'model', d.model, 'options', d.options, 'output', d.output, 'confidence', d.confidence,
         'error', d.error, 'human_label', d.human_label, 'created_at', d.created_at))
FROM decision_log d JOIN claim c ON d.input_ref = 'claim:' || c.id
WHERE c.id % 5 = 0;

-- ---- what the whole database holds, for the projection --------------------------------
SELECT json_build_object('kind', '_full', 'key', k, 'body', json_build_object('rows', n))
FROM (VALUES
  ('claim', (SELECT count(*) FROM claim)),
  ('source_article', (SELECT count(*) FROM source_article)),
  ('promise', (SELECT count(*) FROM promise)),
  ('reported_statement', (SELECT count(*) FROM reported_statement)),
  ('entity', (SELECT count(*) FROM entity)),
  ('entity_match', (SELECT count(*) FROM entity_match)),
  ('claim_term', (SELECT count(*) FROM claim_term)),
  ('source_record', (SELECT count(*) FROM term_record) + (SELECT count(*) FROM organisation_record)
                    + (SELECT count(*) FROM paper_record) + (SELECT count(DISTINCT (source_name, external_id)) FROM entity_substance)),
  ('entity_substance', (SELECT count(*) FROM entity_substance)),
  ('evidence_event', (SELECT count(*) FROM evidence_event)),
  ('trial_read', (SELECT count(*) FROM trial_read)),
  ('registry_trial', (SELECT count(*) FROM registry_trial)),
  ('registry_trial_fts', (SELECT count(*) FROM registry_trial)),
  ('registry_trial_status', (SELECT count(*) FROM registry_trial)),
  ('article_lead', (SELECT count(*) FROM article_lead)),
  ('work_entry', (SELECT count(*) FROM work_entry WHERE record_kind <> 'link_lead')),
  ('link_lead', (SELECT count(*) FROM link_lead WHERE outlet_kind <> 'unknown'
                   AND (triage_score IS NOT NULL OR read_outcome IS NOT NULL OR claim_id IS NOT NULL))),
  ('link_lead_fts', (SELECT count(*) FROM link_lead WHERE outlet_kind <> 'unknown'
                   AND (triage_score IS NOT NULL OR read_outcome IS NOT NULL OR claim_id IS NOT NULL))),
  ('link_share', (SELECT count(*) FROM link_share s JOIN link_lead l ON l.id = s.link_lead_id
                   WHERE l.outlet_kind <> 'unknown' AND (l.triage_score IS NOT NULL OR l.read_outcome IS NOT NULL OR l.claim_id IS NOT NULL))),
  ('llm_usage', (SELECT count(*) FROM llm_usage)),
  ('decision_log', (SELECT count(*) FROM decision_log WHERE step <> 'lead_triage')),
  ('decision_log_with_triage', (SELECT count(*) FROM decision_log)),
  ('payload_inline', (SELECT count(DISTINCT md5(raw_payload::text)) FROM registry_trial)),
  ('payload_r2', (SELECT count(DISTINCT md5(raw_payload::text)) FROM evidence_event)),
  ('payload_r2_bytes', (SELECT sum(n) FROM (SELECT max(octet_length(raw_payload::text)) n FROM evidence_event
                                            GROUP BY md5(raw_payload::text)) x)),
  ('largest_trial_payload', (SELECT max(octet_length(raw_payload::text)) FROM registry_trial)),
  ('postgres_bytes', (SELECT pg_database_size(current_database())))
) v (k, n);
