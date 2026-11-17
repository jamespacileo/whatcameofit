-- A paper's abstract in the payloads Postgres holds (docs/adr/0011). No row is a pass:
-- once `thenwhat backfill strip-paper-abstracts --apply` has run, this answers nothing.
-- Read-only: psql "$DATABASE_URL" -f pipeline/src/thenwhat/store/no_abstracts.sql

SELECT 'evidence_event' AS "table", source_name AS source, 'AbstractText' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.AbstractText')
  GROUP BY source_name
UNION ALL
SELECT 'evidence_event' AS "table", source_name AS source, 'abstract' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract')
  GROUP BY source_name
UNION ALL
SELECT 'evidence_event' AS "table", source_name AS source, 'abstractText' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstractText')
  GROUP BY source_name
UNION ALL
SELECT 'evidence_event' AS "table", source_name AS source, 'abstract_inverted_index' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract_inverted_index')
  GROUP BY source_name
UNION ALL
SELECT 'evidence_event' AS "table", source_name AS source, 'fullText' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.fullText')
  GROUP BY source_name
UNION ALL
SELECT 'paper_record' AS "table", source_name AS source, 'AbstractText' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.AbstractText')
  GROUP BY source_name
UNION ALL
SELECT 'paper_record' AS "table", source_name AS source, 'abstract' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.abstract')
  GROUP BY source_name
UNION ALL
SELECT 'paper_record' AS "table", source_name AS source, 'abstractText' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.abstractText')
  GROUP BY source_name
UNION ALL
SELECT 'paper_record' AS "table", source_name AS source, 'abstract_inverted_index' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.abstract_inverted_index')
  GROUP BY source_name
UNION ALL
SELECT 'paper_record' AS "table", source_name AS source, 'fullText' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.fullText')
  GROUP BY source_name
UNION ALL
SELECT 'trial_paper' AS "table", source_name AS source, 'AbstractText' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.AbstractText')
  GROUP BY source_name
UNION ALL
SELECT 'trial_paper' AS "table", source_name AS source, 'abstract' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract')
  GROUP BY source_name
UNION ALL
SELECT 'trial_paper' AS "table", source_name AS source, 'abstractText' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstractText')
  GROUP BY source_name
UNION ALL
SELECT 'trial_paper' AS "table", source_name AS source, 'abstract_inverted_index' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract_inverted_index')
  GROUP BY source_name
UNION ALL
SELECT 'trial_paper' AS "table", source_name AS source, 'fullText' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.fullText')
  GROUP BY source_name
ORDER BY 1, 2, 3;
