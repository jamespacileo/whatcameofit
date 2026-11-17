-- The report without the merge: what store/merge.sql would report for a run, counted and
-- not tried. A D1 batch cannot be undone on request, so `--report-only` cannot run the
-- merge and take it back.
--
-- Sent as one batch, in this order, with the run as ?1. The first statement puts the run
-- in `merging` so the `staged` and `preview_*` views see it, the last takes it out again,
-- and nothing in between writes. Each SELECT in between gives rows of
-- (kind, resolved, added, conflicts), the columns of `merge_report`; the ingest service
-- puts them together. Afterwards `discard_run` (store/ingest.sql) drops the run and what
-- it staged, so the store is as it was.
--
-- It must say what the merge then says. store/proof/proof.py holds it to that: before
-- every merge the proof runs, it takes this report and compares it with the merge's own.
--
-- Where it cannot be exact, by design: a run that names one claim by two slugs, a present
-- and a former one, for the same record; and an action that depends on another action of
-- the same run other than a clear before a publication. Neither is something a writer
-- sends today.

-- A run that would be refused, or is not registered, previews nothing.
INSERT INTO merging (id, run_id)
SELECT 1, id FROM run
WHERE id = ?1 AND status = 'registered'
  AND NOT EXISTS (SELECT 1 FROM run_step rs JOIN store_step ss ON ss.step = rs.step
                  WHERE rs.run_id = run.id AND rs.version < ss.version)
;
-- Why it would be refused, when it would be.
SELECT r.status,
       (SELECT 'step ' || rs.step || ' is at version ' || rs.version || ', the store accepts ' || ss.version
        FROM run_step rs JOIN store_step ss ON ss.step = rs.step
        WHERE rs.run_id = r.id AND rs.version < ss.version LIMIT 1) AS refusal
FROM run r WHERE r.id = ?1
;
-- Records with no parent: added when the store has none under their key.
SELECT s.kind, count(*) AS resolved, 0 AS conflicts, sum(CASE s.kind
  WHEN 'payload'        THEN NOT EXISTS (SELECT 1 FROM payload p WHERE p.sha256 = s.body ->> 'sha256')
  WHEN 'claim'          THEN NOT EXISTS (SELECT 1 FROM claim_key k WHERE k.slug = s.body ->> 'slug')
  WHEN 'source_record'  THEN NOT EXISTS (SELECT 1 FROM source_record r WHERE r.kind = s.body ->> 'kind'
                               AND r.source_name = s.body ->> 'source_name' AND r.external_id = s.body ->> 'external_id')
  WHEN 'trial_read'     THEN NOT EXISTS (SELECT 1 FROM trial_read r WHERE r.source_name = s.body ->> 'source_name'
                               AND r.trial_id = s.body ->> 'trial_id')
  WHEN 'registry_trial' THEN NOT EXISTS (SELECT 1 FROM registry_trial t WHERE t.registry_name = s.body ->> 'registry_name'
                               AND t.external_id = s.body ->> 'external_id')
  WHEN 'link_lead'      THEN NOT EXISTS (SELECT 1 FROM link_lead l WHERE l.url_key = s.body ->> 'url_key')
  WHEN 'decision'       THEN 1
  WHEN 'usage'          THEN 1
  ELSE 0 END) AS added
FROM staged s
WHERE s.kind IN ('payload', 'claim', 'source_record', 'trial_read', 'registry_trial', 'registry_load',
                 'link_lead', 'unlisted_domain', 'decision', 'usage', 'measure_daily', 'work_entry',
                 'outlet_icon', 'work_slice')
GROUP BY s.kind
;
-- Records of a claim. An event is a conflict when the approved one stored says otherwise.
SELECT s.kind, count(*) AS resolved,
  sum(s.kind = 'evidence_event' AND EXISTS (SELECT 1 FROM preview_conflict x WHERE x.key = s.key)) AS conflicts,
  sum(CASE s.kind
  WHEN 'source_article' THEN NOT EXISTS (SELECT 1 FROM source_article a WHERE a.claim_id = s.claim_id
                               AND a.url_key = s.body ->> 'url_key')
  WHEN 'entity'         THEN NOT EXISTS (SELECT 1 FROM entity e WHERE e.claim_id = s.claim_id
                               AND e.type = s.body ->> 'type' AND e.name = s.body ->> 'name')
  WHEN 'claim_term'     THEN NOT EXISTS (SELECT 1 FROM claim_term t WHERE t.claim_id = s.claim_id
                               AND t.role = s.body ->> 'role' AND t.source_name = s.body ->> 'source_name'
                               AND t.external_id = s.body ->> 'external_id')
  WHEN 'evidence_event' THEN NOT EXISTS (SELECT 1 FROM evidence_event e WHERE e.claim_id = s.claim_id
                               AND e.dedupe_key = s.body ->> 'dedupe_key')
  WHEN 'failure_flag'   THEN NOT EXISTS (SELECT 1 FROM failure_flag f WHERE f.claim_id = s.claim_id
                               AND f.trial_external_id = s.body ->> 'trial_external_id')
  ELSE 0 END) AS added
FROM preview_of_claim s
WHERE s.kind IN ('source_article', 'entity', 'claim_term', 'evidence_event', 'failure_flag', 'measure_claim')
GROUP BY s.kind
;
-- Actions: added when the action would take effect, by the rule above its statements in
-- store/merge.sql, in the order the merge reaches them.
SELECT 'action' AS kind, count(*) AS resolved, 0 AS conflicts, sum(CASE a.action
  WHEN 'audit_clear' THEN a.held AND NOT a.conflicted
  WHEN 'publish'     THEN NOT a.published AND a.approved AND NOT a.archived
                          AND (NOT a.held OR (NOT a.conflicted AND EXISTS (
                                 SELECT 1 FROM stg c WHERE c.run_id = a.run_id AND c.kind = 'action'
                                   AND c.body ->> 'action' = 'audit_clear' AND c.body ->> 'slug' = a.body ->> 'slug')))
  WHEN 'archive'     THEN NOT a.archived
  WHEN 'unarchive'   THEN a.archived AND NOT a.merged
  WHEN 'rename'      THEN ((a.own_id IS NOT NULL AND a.own_merged_into IS NULL) OR a.claim_id IS NULL)
                          AND (a.body ->> 'slug' <> a.body ->> 'new_slug' OR a.body ->> 'new_name' IS NOT NULL)
  WHEN 'merge'       THEN ((a.own_id IS NOT NULL AND a.own_merged_into IS NULL) OR a.claim_id IS NULL)
                          AND EXISTS (SELECT 1 FROM claim_key k WHERE k.slug = a.body ->> 'into_slug'
                                        AND k.claim_id IS NOT a.own_id)
  ELSE EXISTS (SELECT 1 FROM evidence_conflict x WHERE x.claim_id = a.claim_id AND x.state = 'open'
                 AND x.dedupe_key = a.body ->> 'dedupe_key' AND x.content_sha256 = a.body ->> 'content_sha256')
  END) AS added
FROM preview_action a
HAVING count(*) > 0
;
-- Records of a source article.
SELECT s.kind, count(*) AS resolved, 0 AS conflicts, sum(CASE s.kind
  WHEN 'promise' THEN NOT EXISTS (SELECT 1 FROM promise p WHERE p.source_article_id = s.source_article_id
                        AND p.description = s.body ->> 'description')
  ELSE NOT EXISTS (SELECT 1 FROM reported_statement r WHERE r.source_article_id = s.source_article_id
                        AND r.text_key = s.body ->> 'text_key') END) AS added
FROM preview_of_article s
WHERE s.kind IN ('promise', 'reported_statement')
GROUP BY s.kind
;
-- Records of an entity.
SELECT s.kind, count(*) AS resolved, 0 AS conflicts, sum(CASE s.kind
  WHEN 'entity_match'     THEN NOT EXISTS (SELECT 1 FROM entity_match m WHERE m.entity_id = s.entity_id
                                 AND m.source_name = s.body ->> 'source_name' AND m.external_id = s.body ->> 'external_id')
  WHEN 'entity_substance' THEN NOT EXISTS (SELECT 1 FROM entity_substance x WHERE x.entity_id = s.entity_id)
  ELSE 0 END) AS added
FROM preview_of_entity s
WHERE s.kind IN ('entity_match', 'entity_substance', 'entity_article')
GROUP BY s.kind
;
-- Records of a link lead.
SELECT s.kind, count(*) AS resolved, 0 AS conflicts, sum(CASE s.kind
  WHEN 'link_share'     THEN NOT EXISTS (SELECT 1 FROM link_share x WHERE x.link_lead_id = s.link_lead_id
                               AND x.platform = s.body ->> 'platform' AND x.community = s.body ->> 'community'
                               AND x.shared_at = s.body ->> 'shared_at')
  WHEN 'link_lead_link' THEN NOT EXISTS (SELECT 1 FROM link_lead_link x WHERE x.link_lead_id = s.link_lead_id
                               AND x.record_kind = s.body ->> 'record_kind' AND x.record_key = s.body ->> 'record_key'
                               AND x.reason = s.body ->> 'reason')
  WHEN 'lead_reading'   THEN NOT EXISTS (SELECT 1 FROM lead_reading x WHERE x.link_lead_id = s.link_lead_id)
  ELSE 0 END) AS added
FROM preview_of_lead s
WHERE s.kind IN ('link_share', 'link_lead_link', 'link_lead_label', 'lead_reading')
GROUP BY s.kind
;
-- Records of a trial.
SELECT s.kind, count(*) AS resolved, 0 AS conflicts,
       sum(NOT EXISTS (SELECT 1 FROM article_lead a WHERE a.registry_trial_id = s.trial_id
                         AND a.url_key = s.body ->> 'url_key')) AS added
FROM preview_of_trial s
WHERE s.kind = 'article_lead'
GROUP BY s.kind
;
-- Whether the counts would reconcile: every kind the run stated, with what was found.
SELECT t.kind, t.records AS stated,
       (SELECT count(*) FROM staged s WHERE s.kind = t.kind) AS staged
FROM run_stated t JOIN merging m ON m.run_id = t.run_id
;
DELETE FROM merging
;
