-- thenwhat truth store: the D1 (SQLite) schema. A draft for review; nothing is deployed.
--
-- Read with: openspec/changes/cloudflare-source-of-truth/store-tables.md, which says for each
-- Postgres table whether it moves as is, moves reshaped, stays local or is dropped, and why.
--
-- Conventions
--   * Row ids are the store's own and never leave it. A writer names a record by its natural
--     key; every natural key below is a UNIQUE constraint or the primary key.
--   * Times are ISO-8601 text in UTC. Dates are YYYY-MM-DD. Lists and objects are JSON text.
--   * Every record carries the run that added it and the run that last changed it.
--   * No table holds article text, post text, a post's author, or anything of a reader.
--   * Tables are STRICT, so a column cannot hold a value of another type.

-- ---------------------------------------------------------------------------------------
-- 1. Runs: who wrote, with which code, and what the merge did
-- ---------------------------------------------------------------------------------------

-- The lowest version of each step the store accepts records from.
CREATE TABLE store_step (
  step     TEXT PRIMARY KEY,
  version  INTEGER NOT NULL
) STRICT;

CREATE TABLE run (
  id               TEXT PRIMARY KEY,   -- random, never made from a time
  writer           TEXT NOT NULL CHECK (writer IN
                     ('device', 'daily', 'lookup', 'consumer', 'operator', 'export', 'migration')),
  device           TEXT,               -- the device's name; empty for a reader's lookup
  request_class    TEXT CHECK (request_class IN ('extension', 'site')),
  commit_sha       TEXT NOT NULL,
  registered_at    TEXT NOT NULL,
  stated_checksum  TEXT,               -- of the records handed over, checked by the ingest service
  restore_bookmark TEXT,               -- D1 Time Travel bookmark taken before a large run
  status           TEXT NOT NULL DEFAULT 'registered'
                     CHECK (status IN ('registered', 'merged', 'refused')),
  refusal          TEXT,
  merged_at        TEXT,
  CHECK ((writer = 'lookup') = (request_class IS NOT NULL)),
  CHECK (writer <> 'lookup' OR device IS NULL),
  -- Nothing a lookup leaves holds a time finer than the day, its run included.
  CHECK (writer <> 'lookup' OR (length(registered_at) = 10 AND length(coalesce(merged_at, '0000-00-00')) = 10)),
  CHECK ((status = 'merged') = (merged_at IS NOT NULL)),
  CHECK ((status = 'refused') = (refusal IS NOT NULL))
) STRICT;

CREATE TABLE run_step (
  run_id   TEXT NOT NULL REFERENCES run (id),
  step     TEXT NOT NULL,
  version  INTEGER NOT NULL,
  PRIMARY KEY (run_id, step)
) STRICT;

-- How many records of each kind the writer says it handed over.
CREATE TABLE run_stated (
  run_id   TEXT NOT NULL REFERENCES run (id),
  kind     TEXT NOT NULL,
  records  INTEGER NOT NULL CHECK (records >= 0),
  PRIMARY KEY (run_id, kind)
) STRICT;

-- Records handed over, waiting for their run's merge. One shape for every kind: the kind,
-- the natural key as one string, and the record as JSON. The ingest service fills it with
-- one statement per chunk (`INSERT ... SELECT ... FROM json_each(?2)`).
CREATE TABLE stg (
  run_id  TEXT NOT NULL REFERENCES run (id),
  kind    TEXT NOT NULL,
  key     TEXT NOT NULL CHECK (length(key) > 0),
  body    TEXT NOT NULL CHECK (json_valid(body)),
  PRIMARY KEY (run_id, kind, key)
) STRICT;

-- The one run being merged. A merge's first statement puts its run here when the run is
-- accepted; every later statement reads `staged` and so does nothing for a refused run.
CREATE TABLE merging (
  id      INTEGER PRIMARY KEY CHECK (id = 1),
  run_id  TEXT NOT NULL REFERENCES run (id)
) STRICT;

CREATE VIEW staged AS
  SELECT s.run_id, s.kind, s.key, s.body FROM stg s JOIN merging m ON m.run_id = s.run_id;

-- For each kind: records whose parents were found, records added, and conflicts.
-- Matched is what is left: resolved - added - conflicts.
CREATE TABLE merge_report (
  run_id     TEXT NOT NULL REFERENCES run (id),
  kind       TEXT NOT NULL,
  resolved   INTEGER NOT NULL,
  added      INTEGER NOT NULL,
  conflicts  INTEGER NOT NULL DEFAULT 0,
  note       TEXT,
  PRIMARY KEY (run_id, kind),
  CHECK (added + conflicts <= resolved)
) STRICT;

-- A row may enter only when the run's counts reconcile. The merge's last statements insert
-- here; a mismatch fails the CHECK, which undoes the whole batch.
CREATE TABLE merge_guard (
  run_id      TEXT PRIMARY KEY REFERENCES run (id),
  reconciled  INTEGER NOT NULL CHECK (reconciled = 1)
) STRICT;

-- ---------------------------------------------------------------------------------------
-- 2. Raw payloads, once per checksum
-- ---------------------------------------------------------------------------------------

-- A payload as its source gave it. A small one (a registry listing record) is kept here;
-- a larger one is an R2 object under `payload/<sha256>`. Either way the record that uses
-- it holds the checksum and its own fetch time.
CREATE TABLE payload (
  sha256     TEXT PRIMARY KEY CHECK (length(sha256) = 64),
  bytes      INTEGER NOT NULL CHECK (bytes > 0),
  body       TEXT CHECK (body IS NULL OR length(body) <= 16384),
  r2_key     TEXT,
  added_run  TEXT NOT NULL REFERENCES run (id),
  CHECK ((body IS NULL) <> (r2_key IS NULL))
) STRICT;
CREATE INDEX ix_payload_added_run ON payload (added_run);

-- ---------------------------------------------------------------------------------------
-- 3. Claims and what was said of them
-- ---------------------------------------------------------------------------------------

CREATE TABLE claim (
  id                   INTEGER PRIMARY KEY,
  slug                 TEXT NOT NULL UNIQUE CHECK (
                         length(slug) BETWEEN 1 AND 60
                         AND slug NOT GLOB '*[^a-z0-9-]*'
                         AND slug NOT GLOB '-*' AND slug NOT GLOB '*-' AND slug NOT GLOB '*--*'),
  headline             TEXT NOT NULL,
  summary              TEXT NOT NULL,
  vertical             TEXT NOT NULL,
  approach             TEXT,
  indication           TEXT NOT NULL,
  first_reported_date  TEXT,
  evidence_stage       TEXT CHECK (evidence_stage IN ('in_vitro', 'animal', 'early_human', 'late_human')),
  current_status       TEXT NOT NULL DEFAULT 'no_trial_found' CHECK (current_status IN (
                         'preclinical_only', 'no_trial_found', 'trial_registered', 'phase_1', 'phase_2',
                         'phase_3', 'approved', 'failed', 'terminated', 'retracted')),
  overlay_years        INTEGER,
  status_updated_at    TEXT,
  -- Where the claim began. A claim from a reader's lead is published by rule with no
  -- audit hold (docs/adr/0009); one from a backfill's read batch arrives held (0007).
  origin               TEXT NOT NULL CHECK (origin IN ('seed', 'entry', 'backfill', 'lookup', 'registry')),
  review_state         TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
  reviewed_at          TEXT,
  reviewed_by          TEXT CHECK (reviewed_by IN ('human', 'rule', 'seed', 'assistant')),
  review_rank          INTEGER GENERATED ALWAYS AS (
                         CASE reviewed_by WHEN 'human' THEN 3 WHEN 'assistant' THEN 2
                                          WHEN 'rule' THEN 1 WHEN 'seed' THEN 1 ELSE 0 END) VIRTUAL,
  published_at         TEXT,
  archived_at          TEXT,
  archive_reason       TEXT,
  awaiting_audit_at    TEXT,
  merged_into          INTEGER REFERENCES claim (id),
  created_at           TEXT NOT NULL,
  added_run            TEXT NOT NULL REFERENCES run (id),
  changed_run          TEXT NOT NULL REFERENCES run (id),
  CHECK ((review_state = 'pending') = (reviewed_at IS NULL) AND (reviewed_at IS NULL) = (reviewed_by IS NULL)),
  CHECK ((archived_at IS NULL) = (archive_reason IS NULL)),
  CHECK (merged_into IS NULL OR (archived_at IS NOT NULL AND merged_into <> id))
) STRICT;
CREATE INDEX ix_claim_added_run ON claim (added_run);
CREATE INDEX ix_claim_merged_into ON claim (merged_into) WHERE merged_into IS NOT NULL;

-- A slug a claim used to have. The old address goes on answering, and a writer that still
-- names the claim by it reaches the same claim.
CREATE TABLE claim_alias (
  slug       TEXT PRIMARY KEY,
  claim_id   INTEGER NOT NULL REFERENCES claim (id),
  added_run  TEXT NOT NULL REFERENCES run (id)
) STRICT;

-- Every slug a writer may use, and the claim its records go to: the claim itself, the
-- claim it was merged into, or the claim that was renamed from it.
CREATE VIEW claim_key AS
  SELECT slug, coalesce(merged_into, id) AS claim_id FROM claim
  UNION ALL
  SELECT a.slug, coalesce(c.merged_into, c.id) FROM claim_alias a JOIN claim c ON c.id = a.claim_id;

-- What a reader may be shown: the publication gate as far as the store can state it.
CREATE VIEW claim_public AS
  SELECT * FROM claim
  WHERE review_state = 'approved' AND published_at IS NOT NULL
    AND archived_at IS NULL AND awaiting_audit_at IS NULL;

-- Holds, clears, archives, unarchives, merges and renames, as they happened.
CREATE TABLE claim_action (
  id          INTEGER PRIMARY KEY,
  claim_id    INTEGER NOT NULL REFERENCES claim (id),
  action      TEXT NOT NULL CHECK (action IN ('audit_hold', 'audit_clear', 'archive', 'unarchive',
                'merge', 'rename', 'conflict_accept', 'conflict_dismiss', 'publish')),
  detail      TEXT,
  decided_by  TEXT NOT NULL CHECK (decided_by IN ('human', 'rule', 'assistant')),
  at          TEXT NOT NULL,
  run_id      TEXT NOT NULL REFERENCES run (id),
  -- Only a person brings a claim back.
  CHECK (action <> 'unarchive' OR decided_by = 'human')
) STRICT;
CREATE INDEX ix_claim_action_claim ON claim_action (claim_id);
CREATE INDEX ix_claim_action_run ON claim_action (run_id);

CREATE TABLE source_article (
  id              INTEGER PRIMARY KEY,
  claim_id        INTEGER NOT NULL REFERENCES claim (id),
  url_key         TEXT NOT NULL,       -- the address in the form addresses are compared in
  url             TEXT NOT NULL,
  outlet          TEXT NOT NULL,
  title           TEXT NOT NULL,
  published_date  TEXT NOT NULL,
  content_hash    TEXT,
  archive_url     TEXT,
  added_run       TEXT NOT NULL REFERENCES run (id),
  UNIQUE (claim_id, url_key)
) STRICT;
CREATE INDEX ix_source_article_url_key ON source_article (url_key);
CREATE INDEX ix_source_article_added_run ON source_article (added_run);

CREATE TABLE promise (
  id                 INTEGER PRIMARY KEY,
  claim_id           INTEGER NOT NULL REFERENCES claim (id),
  source_article_id  INTEGER NOT NULL REFERENCES source_article (id),
  description        TEXT NOT NULL,
  parsed_date        TEXT,
  added_run          TEXT NOT NULL REFERENCES run (id),
  UNIQUE (source_article_id, description)
) STRICT;
CREATE INDEX ix_promise_claim ON promise (claim_id);

-- The pipeline's own wording of something an article says; never the article's words.
CREATE TABLE reported_statement (
  id                 INTEGER PRIMARY KEY,
  claim_id           INTEGER NOT NULL REFERENCES claim (id),
  source_article_id  INTEGER NOT NULL REFERENCES source_article (id),
  text               TEXT NOT NULL CHECK (length(text) BETWEEN 1 AND 200),
  text_key           TEXT NOT NULL,
  kind               TEXT NOT NULL,
  firmness           TEXT NOT NULL,
  speaker            TEXT NOT NULL,
  basis              TEXT NOT NULL,
  confidence         REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  decision_ref       TEXT NOT NULL,
  article_read_at    TEXT NOT NULL,
  review_state       TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
  reviewed_at        TEXT,
  reviewed_by        TEXT CHECK (reviewed_by IN ('human', 'rule', 'seed', 'assistant')),
  review_rank        INTEGER GENERATED ALWAYS AS (
                       CASE reviewed_by WHEN 'human' THEN 3 WHEN 'assistant' THEN 2
                                        WHEN 'rule' THEN 1 WHEN 'seed' THEN 1 ELSE 0 END) VIRTUAL,
  created_at         TEXT NOT NULL,
  added_run          TEXT NOT NULL REFERENCES run (id),
  changed_run        TEXT NOT NULL REFERENCES run (id),
  UNIQUE (source_article_id, text_key),
  CHECK ((review_state = 'pending') = (reviewed_at IS NULL) AND (reviewed_at IS NULL) = (reviewed_by IS NULL))
) STRICT;
CREATE INDEX ix_reported_statement_claim ON reported_statement (claim_id);

-- ---------------------------------------------------------------------------------------
-- 4. Entities, matches and terms
-- ---------------------------------------------------------------------------------------

CREATE TABLE entity (
  id               INTEGER PRIMARY KEY,
  claim_id         INTEGER NOT NULL REFERENCES claim (id),
  type             TEXT NOT NULL CHECK (type IN ('intervention', 'paper', 'person', 'institution', 'company')),
  name             TEXT NOT NULL,
  synonyms         TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(synonyms)),
  search_phrases   TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(search_phrases)),
  is_origin_paper  INTEGER NOT NULL DEFAULT 0 CHECK (is_origin_paper IN (0, 1)),
  doi              TEXT,
  named_by         TEXT NOT NULL DEFAULT '["article"]'
                     CHECK (named_by IN ('["article"]', '["registry"]', '["article","registry"]')),
  added_run        TEXT NOT NULL REFERENCES run (id),
  UNIQUE (claim_id, type, name),
  CHECK (is_origin_paper = 0 OR type = 'paper'),
  CHECK (doi IS NULL OR type = 'paper')
) STRICT;
CREATE UNIQUE INDEX uq_entity_origin_paper_per_claim ON entity (claim_id) WHERE is_origin_paper = 1;

CREATE TABLE entity_article (
  entity_id          INTEGER NOT NULL REFERENCES entity (id),
  source_article_id  INTEGER NOT NULL REFERENCES source_article (id),
  PRIMARY KEY (entity_id, source_article_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE entity_match (
  id              INTEGER PRIMARY KEY,
  entity_id       INTEGER NOT NULL REFERENCES entity (id),
  source_name     TEXT NOT NULL,
  external_id     TEXT NOT NULL,
  score           REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
  record_summary  TEXT,
  record_facts    TEXT CHECK (record_facts IS NULL OR json_valid(record_facts)),
  reasons         TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(reasons)),
  review_state    TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
  reviewed_at     TEXT,
  reviewed_by     TEXT CHECK (reviewed_by IN ('human', 'rule', 'seed', 'assistant')),
  review_rank     INTEGER GENERATED ALWAYS AS (
                    CASE reviewed_by WHEN 'human' THEN 3 WHEN 'assistant' THEN 2
                                     WHEN 'rule' THEN 1 WHEN 'seed' THEN 1 ELSE 0 END) VIRTUAL,
  created_at      TEXT NOT NULL,
  added_run       TEXT NOT NULL REFERENCES run (id),
  changed_run     TEXT NOT NULL REFERENCES run (id),
  UNIQUE (entity_id, source_name, external_id),
  CHECK ((review_state = 'pending') = (reviewed_at IS NULL) AND (reviewed_at IS NULL) = (reviewed_by IS NULL))
) STRICT;
-- A trial's page lists the claims whose approved matches name the trial.
CREATE INDEX ix_entity_match_external ON entity_match (source_name, external_id);
CREATE INDEX ix_entity_match_added_run ON entity_match (added_run);

CREATE TABLE claim_term (
  id            INTEGER PRIMARY KEY,
  claim_id      INTEGER NOT NULL REFERENCES claim (id),
  role          TEXT NOT NULL CHECK (role IN ('condition', 'intervention', 'target', 'drug')),
  source_name   TEXT NOT NULL,
  external_id   TEXT NOT NULL,
  label         TEXT NOT NULL,
  score         REAL CHECK (score BETWEEN 0 AND 1),
  fit           TEXT CHECK (fit IN ('exact', 'broader', 'kind')),
  reasons       TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(reasons)),
  review_state  TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
  reviewed_at   TEXT,
  reviewed_by   TEXT CHECK (reviewed_by IN ('human', 'rule', 'seed', 'assistant')),
  review_rank   INTEGER GENERATED ALWAYS AS (
                  CASE reviewed_by WHEN 'human' THEN 3 WHEN 'assistant' THEN 2
                                   WHEN 'rule' THEN 1 WHEN 'seed' THEN 1 ELSE 0 END) VIRTUAL,
  created_at    TEXT NOT NULL,
  added_run     TEXT NOT NULL REFERENCES run (id),
  changed_run   TEXT NOT NULL REFERENCES run (id),
  UNIQUE (claim_id, role, source_name, external_id),
  CHECK ((review_state = 'pending') = (reviewed_at IS NULL) AND (reviewed_at IS NULL) = (reviewed_by IS NULL))
) STRICT;

-- A source's own record of a thing, kept once per record with the time it was read. One
-- table for what Postgres keeps in four: vocabulary terms, organisations, papers and
-- substances. The body is what the export reads (a term's and an organisation's record
-- whole; a paper's record with abstract and authors already removed). A substance's
-- record is large, so its body is empty and the whole is a payload.
CREATE TABLE source_record (
  kind            TEXT NOT NULL CHECK (kind IN ('term', 'organisation', 'paper', 'substance')),
  source_name     TEXT NOT NULL,
  external_id     TEXT NOT NULL,       -- for a paper: the DOI in lower case, else pmid:<n>
  url             TEXT,
  pubmed_id       TEXT,
  body            TEXT CHECK (body IS NULL OR json_valid(body)),   -- empty: asked, not held
  payload_sha256  TEXT REFERENCES payload (sha256),
  fetched_at      TEXT NOT NULL,
  added_run       TEXT NOT NULL REFERENCES run (id),
  changed_run     TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (kind, source_name, external_id),
  CHECK (kind = 'paper' OR pubmed_id IS NULL)
) STRICT, WITHOUT ROWID;
CREATE INDEX ix_source_record_pubmed ON source_record (pubmed_id) WHERE pubmed_id IS NOT NULL;

-- The one substance a registry of substances lists an intervention under.
CREATE TABLE entity_substance (
  entity_id    INTEGER PRIMARY KEY REFERENCES entity (id),
  source_name  TEXT NOT NULL,
  external_id  TEXT NOT NULL,
  codes        TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(codes)),
  fetched_at   TEXT NOT NULL,
  added_run    TEXT NOT NULL REFERENCES run (id),
  changed_run  TEXT NOT NULL REFERENCES run (id)
) STRICT;

-- ---------------------------------------------------------------------------------------
-- 5. Evidence
-- ---------------------------------------------------------------------------------------

CREATE TABLE evidence_event (
  id                  INTEGER PRIMARY KEY,
  claim_id            INTEGER NOT NULL REFERENCES claim (id),
  dedupe_key          TEXT NOT NULL,
  entity_match_id     INTEGER REFERENCES entity_match (id),
  type                TEXT NOT NULL CHECK (type IN ('followup_paper', 'trial_registered', 'trial_status_change',
                        'trial_results_posted', 'grant_awarded', 'company_event', 'retraction', 'regulatory_decision')),
  event_date          TEXT NOT NULL,
  date_basis          TEXT,
  source_name         TEXT NOT NULL,
  source_url          TEXT NOT NULL CHECK (length(trim(source_url)) > 0),
  external_id         TEXT NOT NULL,
  trial_phases        TEXT CHECK (trial_phases IS NULL OR json_valid(trial_phases)),
  trial_state         TEXT CHECK (trial_state IN ('started', 'completed', 'terminated', 'withdrawn', 'suspended')),
  regulatory_outcome  TEXT CHECK (regulatory_outcome IN ('approved', 'refused')),
  summary             TEXT NOT NULL,
  confidence          REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  -- Of the fields a status is derived from, worked out by the writer. Two fetches of one
  -- record that say the same of the event have the same content and different payloads.
  content_sha256      TEXT NOT NULL,
  payload_sha256      TEXT NOT NULL REFERENCES payload (sha256),
  fetched_at          TEXT NOT NULL,
  review_state        TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
  reviewed_at         TEXT,
  reviewed_by         TEXT CHECK (reviewed_by IN ('human', 'rule', 'seed', 'assistant')),
  review_rank         INTEGER GENERATED ALWAYS AS (
                        CASE reviewed_by WHEN 'human' THEN 3 WHEN 'assistant' THEN 2
                                         WHEN 'rule' THEN 1 WHEN 'seed' THEN 1 ELSE 0 END) VIRTUAL,
  created_at          TEXT NOT NULL,
  added_run           TEXT NOT NULL REFERENCES run (id),
  changed_run         TEXT NOT NULL REFERENCES run (id),
  UNIQUE (claim_id, dedupe_key),
  CHECK ((type = 'trial_status_change') = (trial_state IS NOT NULL)),
  CHECK ((type = 'regulatory_decision') = (regulatory_outcome IS NOT NULL)),
  CHECK ((review_state = 'pending') = (reviewed_at IS NULL) AND (reviewed_at IS NULL) = (reviewed_by IS NULL))
) STRICT;
CREATE INDEX ix_evidence_event_external ON evidence_event (source_name, external_id);
CREATE INDEX ix_evidence_event_added_run ON evidence_event (added_run);

-- An event a run held that says something else than the approved event stored under the
-- same key. Kept apart, whole, so the audit can see both; never used for a status.
CREATE TABLE evidence_conflict (
  id              INTEGER PRIMARY KEY,
  claim_id        INTEGER NOT NULL REFERENCES claim (id),
  dedupe_key      TEXT NOT NULL,
  content_sha256  TEXT NOT NULL,
  payload_sha256  TEXT NOT NULL REFERENCES payload (sha256),
  fetched_at      TEXT NOT NULL,
  event           TEXT NOT NULL CHECK (json_valid(event)),   -- the run's event, as handed over
  reason          TEXT NOT NULL,
  state           TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'accepted', 'dismissed')),
  run_id          TEXT NOT NULL REFERENCES run (id),
  resolved_run    TEXT REFERENCES run (id),
  UNIQUE (claim_id, dedupe_key, content_sha256),
  CHECK ((state = 'open') = (resolved_run IS NULL))
) STRICT;
CREATE INDEX ix_evidence_conflict_run ON evidence_conflict (run_id);

CREATE TABLE failure_flag (
  id                 INTEGER PRIMARY KEY,
  claim_id           INTEGER NOT NULL REFERENCES claim (id),
  trial_external_id  TEXT NOT NULL,
  evidence_event_id  INTEGER NOT NULL REFERENCES evidence_event (id),
  source_url         TEXT NOT NULL CHECK (length(trim(source_url)) > 0),
  created_at         TEXT NOT NULL,
  added_run          TEXT NOT NULL REFERENCES run (id),
  UNIQUE (claim_id, trial_external_id)
) STRICT;

-- One read of a trial's stored record by a model, and the readings the rules let through.
-- A newer read replaces this one and its readings.
CREATE TABLE trial_read (
  id                    INTEGER PRIMARY KEY,
  source_name           TEXT NOT NULL,
  trial_id              TEXT NOT NULL,
  input_hash            TEXT NOT NULL,
  instructions_version  TEXT NOT NULL,
  provider              TEXT NOT NULL,
  model                 TEXT NOT NULL,
  refusals              TEXT NOT NULL CHECK (json_valid(refusals)),
  -- Each: outcome, kind, field, words, number, unit, code, confidence, decided_by.
  -- Postgres keeps these as rows of `reading`; nothing asks for one alone.
  readings              TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(readings)),
  read_at               TEXT NOT NULL,
  added_run             TEXT NOT NULL REFERENCES run (id),
  changed_run           TEXT NOT NULL REFERENCES run (id),
  UNIQUE (source_name, trial_id)
) STRICT;

-- ---------------------------------------------------------------------------------------
-- 6. The registry corpus: every trial, with what its plain page shows
-- ---------------------------------------------------------------------------------------

CREATE TABLE registry_trial (
  id                  INTEGER PRIMARY KEY,
  registry_name       TEXT NOT NULL,
  external_id         TEXT NOT NULL,
  title               TEXT NOT NULL,
  conditions          TEXT NOT NULL CHECK (json_valid(conditions)),
  interventions       TEXT NOT NULL CHECK (json_valid(interventions)),   -- type, name, other names
  intervention_names  TEXT NOT NULL,   -- the names alone, joined, for search
  phases              TEXT NOT NULL CHECK (json_valid(phases)),
  overall_status      TEXT,
  start_date          TEXT,            -- as the registry writes it: can be a month
  sponsor_class       TEXT,
  search_name         TEXT,
  search_indication   TEXT,
  payload_sha256      TEXT NOT NULL REFERENCES payload (sha256),
  fetched_at          TEXT NOT NULL,   -- when the payload held was fetched
  checked_at          TEXT NOT NULL,   -- when the registry was last found to say the same
  added_run           TEXT NOT NULL REFERENCES run (id),
  changed_run         TEXT NOT NULL REFERENCES run (id),
  UNIQUE (registry_name, external_id)
) STRICT;
CREATE INDEX ix_registry_trial_added_run ON registry_trial (added_run);
CREATE INDEX ix_registry_trial_changed_run ON registry_trial (changed_run);

-- Each state a trial has been seen in, from the first load on.
CREATE TABLE registry_trial_status (
  trial_id        INTEGER NOT NULL REFERENCES registry_trial (id),
  seen_at         TEXT NOT NULL,
  overall_status  TEXT,
  run_id          TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (trial_id, seen_at)
) STRICT, WITHOUT ROWID;

CREATE TABLE registry_load (
  registry_name  TEXT NOT NULL,
  condition      TEXT NOT NULL,
  loaded_from    TEXT NOT NULL,
  completed_at   TEXT NOT NULL,
  changed_run    TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (registry_name, condition)
) STRICT, WITHOUT ROWID;

-- A news article a search found for a trial. Unreviewed; its text is never stored.
CREATE TABLE article_lead (
  id                 INTEGER PRIMARY KEY,
  registry_trial_id  INTEGER NOT NULL REFERENCES registry_trial (id),
  url_key            TEXT NOT NULL,
  url                TEXT NOT NULL,
  outlet             TEXT NOT NULL,
  title              TEXT NOT NULL,
  published_date     TEXT,
  outlet_kind        TEXT NOT NULL CHECK (outlet_kind IN ('general_news', 'trade_press', 'press_release', 'unknown')),
  source_name        TEXT NOT NULL,
  search_query       TEXT NOT NULL,
  fetched_at         TEXT NOT NULL,
  added_run          TEXT NOT NULL REFERENCES run (id),
  UNIQUE (registry_trial_id, url_key)
) STRICT;

-- ---------------------------------------------------------------------------------------
-- 7. Link leads: only those on listed outlets, which is all that is ever scored
-- ---------------------------------------------------------------------------------------

CREATE TABLE link_lead (
  id                 INTEGER PRIMARY KEY,
  url_key            TEXT NOT NULL UNIQUE,
  url_key_version    INTEGER NOT NULL,
  url                TEXT NOT NULL,
  outlet             TEXT NOT NULL,
  -- A lead on an unlisted outlet is counted by its writer and never stored.
  outlet_kind        TEXT NOT NULL CHECK (outlet_kind IN ('general_news', 'trade_press', 'press_release')),
  title              TEXT NOT NULL,
  first_shared_at    TEXT NOT NULL,
  origin             TEXT NOT NULL CHECK (origin IN ('file', 'reader')),
  names_topic        INTEGER NOT NULL DEFAULT 0 CHECK (names_topic IN (0, 1)),
  screen_outcome     TEXT CHECK (screen_outcome IN ('in_scope', 'already_tracked')),
  triage_score       REAL CHECK (triage_score BETWEEN 0 AND 1),
  triage_version     INTEGER,
  read_outcome       TEXT,
  read_detail        TEXT,
  claim_id           INTEGER REFERENCES claim (id),
  source_article_id  INTEGER REFERENCES source_article (id),
  added_run          TEXT NOT NULL REFERENCES run (id),
  changed_run        TEXT NOT NULL REFERENCES run (id),
  CHECK ((triage_score IS NULL) = (triage_version IS NULL))
) STRICT;
CREATE INDEX ix_link_lead_added_run ON link_lead (added_run);
CREATE INDEX ix_link_lead_claim ON link_lead (claim_id) WHERE claim_id IS NOT NULL;
-- The next lead to read: topic leads first, then by score.
CREATE INDEX ix_link_lead_due ON link_lead (names_topic DESC, triage_score DESC) WHERE read_outcome IS NULL;

CREATE TABLE link_share (
  link_lead_id  INTEGER NOT NULL REFERENCES link_lead (id),
  platform      TEXT NOT NULL,
  community     TEXT NOT NULL,
  shared_at     TEXT NOT NULL,
  score         INTEGER NOT NULL,
  item_number   INTEGER,
  added_run     TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (link_lead_id, platform, community, shared_at),
  -- A reader's asking is a share with a date and nothing else.
  CHECK (platform <> 'reader'
         OR (community = 'reader' AND length(shared_at) = 10 AND score = 0 AND item_number IS NULL))
) STRICT, WITHOUT ROWID;
CREATE INDEX ix_link_share_added_run ON link_share (added_run);

-- A stored record that screening found for a lead, with the reason. A candidate only.
CREATE TABLE link_lead_link (
  link_lead_id  INTEGER NOT NULL REFERENCES link_lead (id),
  record_kind   TEXT NOT NULL CHECK (record_kind IN ('claim', 'registry_trial')),
  record_key    TEXT NOT NULL,         -- a claim's slug, or registry|trial number
  reason        TEXT NOT NULL,
  added_run     TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (link_lead_id, record_kind, record_key, reason)
) STRICT, WITHOUT ROWID;

CREATE TABLE link_lead_label (
  link_lead_id  INTEGER NOT NULL REFERENCES link_lead (id),
  labelled_by   TEXT NOT NULL CHECK (labelled_by IN ('human', 'assistant')),
  label         TEXT NOT NULL CHECK (label IN ('treatment_report', 'health_other', 'not_health')),
  labelled_at   TEXT NOT NULL,
  changed_run   TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (link_lead_id, labelled_by)
) STRICT, WITHOUT ROWID;

-- What a lookup read an article to report, awaiting the rules. Not a claim, and holds
-- none of the article's words: the treatment and the condition as names, with scores.
CREATE TABLE lead_reading (
  link_lead_id  INTEGER PRIMARY KEY REFERENCES link_lead (id),
  intervention  TEXT NOT NULL,
  indication    TEXT NOT NULL,
  confidence    REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  reasons       TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(reasons)),
  -- Each: registry, trial number, score, reasons. Candidates, never matches.
  trials        TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(trials)),
  read_version  INTEGER NOT NULL,
  read_on       TEXT NOT NULL CHECK (length(read_on) = 10),
  added_run     TEXT NOT NULL REFERENCES run (id),
  changed_run   TEXT NOT NULL REFERENCES run (id)
) STRICT;

-- ---------------------------------------------------------------------------------------
-- 8. Work: what is due in the store, what was done, and who holds which slice
-- ---------------------------------------------------------------------------------------

-- Work the store itself is to do: a reader's lead to process, a pending claim to prepare.
-- A Cloudflare Queue message only wakes the consumer; what is due is read from here, so
-- nothing is lost when a message is.
CREATE TABLE work_item (
  record_kind  TEXT NOT NULL CHECK (record_kind IN ('link_lead', 'claim')),
  record_key   TEXT NOT NULL,
  step         TEXT NOT NULL CHECK (step IN ('lead_process', 'prepare')),
  state        TEXT NOT NULL DEFAULT 'due' CHECK (state IN ('due', 'done', 'failed')),
  attempts     INTEGER NOT NULL DEFAULT 0,
  lease_until  TEXT,
  error        TEXT,
  due_since    TEXT NOT NULL,
  PRIMARY KEY (record_kind, record_key, step),
  CHECK (state <> 'failed' OR error IS NOT NULL)
) STRICT, WITHOUT ROWID;
CREATE INDEX ix_work_item_due ON work_item (step, due_since) WHERE state = 'due';

-- The work ledger for records the store holds: one step finished or failed for one record
-- at one version. The link steps keep no entry here: a lead's own columns say what was
-- scored and read.
CREATE TABLE work_entry (
  record_kind      TEXT NOT NULL,
  record_key       TEXT NOT NULL,
  step             TEXT NOT NULL,
  step_version     INTEGER NOT NULL,
  outcome          TEXT NOT NULL CHECK (outcome IN ('done', 'nothing_found', 'failed')),
  attempts         INTEGER NOT NULL,
  requests_used    INTEGER NOT NULL,
  fingerprint      TEXT NOT NULL,
  stale            INTEGER NOT NULL DEFAULT 0 CHECK (stale IN (0, 1)),
  error            TEXT,
  last_attempt_at  TEXT NOT NULL,
  changed_run      TEXT NOT NULL REFERENCES run (id),
  PRIMARY KEY (record_kind, record_key, step, step_version),
  CHECK ((outcome = 'failed') = (error IS NOT NULL))
) STRICT, WITHOUT ROWID;

-- One platform, one community, one month: who has taken it, and the run that finished it.
CREATE TABLE work_slice (
  platform   TEXT NOT NULL,
  community  TEXT NOT NULL,
  month      TEXT NOT NULL CHECK (length(month) = 7),
  device     TEXT,
  taken_at   TEXT,
  lapses_at  TEXT,
  done_run   TEXT REFERENCES run (id),
  unheld     INTEGER NOT NULL DEFAULT 0 CHECK (unheld IN (0, 1)),   -- finished without being taken
  PRIMARY KEY (platform, community, month),
  CHECK ((device IS NULL) = (taken_at IS NULL) AND (taken_at IS NULL) = (lapses_at IS NULL))
) STRICT, WITHOUT ROWID;

-- ---------------------------------------------------------------------------------------
-- 9. Decisions, spend and measurements
-- ---------------------------------------------------------------------------------------

-- A decision step's answer. It has no natural key, so it is named by its run and its
-- place in the run. `input_ref` names a record by natural key (claim:<slug>, ...).
CREATE TABLE decision_log (
  run_id       TEXT NOT NULL REFERENCES run (id),
  seq          INTEGER NOT NULL,
  step         TEXT NOT NULL,
  input_ref    TEXT NOT NULL,
  backend      TEXT NOT NULL,
  model        TEXT,
  options      TEXT NOT NULL CHECK (json_valid(options)),
  output       TEXT CHECK (output IS NULL OR json_valid(output)),
  confidence   REAL,
  error        TEXT,
  human_label  TEXT,
  created_at   TEXT NOT NULL,
  PRIMARY KEY (run_id, seq)
) STRICT, WITHOUT ROWID;
CREATE INDEX ix_decision_log_ref ON decision_log (input_ref, step);

-- Model spend, by the run that spent it; the run says which device or which readers.
CREATE TABLE llm_usage (
  run_id         TEXT NOT NULL REFERENCES run (id),
  seq            INTEGER NOT NULL,
  purpose        TEXT NOT NULL,
  model          TEXT NOT NULL,
  input_tokens   INTEGER NOT NULL,
  output_tokens  INTEGER NOT NULL,
  cost_usd       REAL NOT NULL,
  -- A day for a reader's lookup, a time otherwise.
  created_at     TEXT NOT NULL,
  PRIMARY KEY (run_id, seq)
) STRICT, WITHOUT ROWID;
CREATE INDEX ix_llm_usage_created ON llm_usage (created_at);

CREATE VIEW spend_by_writer AS
  SELECT substr(u.created_at, 1, 7) AS month, r.writer, coalesce(r.device, r.request_class) AS who,
         sum(u.cost_usd) AS cost_usd, sum(u.input_tokens) AS input_tokens, sum(u.output_tokens) AS output_tokens
  FROM llm_usage u JOIN run r ON r.id = u.run_id
  GROUP BY 1, 2, 3;

CREATE TABLE measure_daily (
  day                 TEXT NOT NULL,
  step                TEXT NOT NULL,
  step_version        INTEGER NOT NULL,
  writer              TEXT NOT NULL,
  outcome             TEXT NOT NULL,
  spans               INTEGER NOT NULL,
  records             INTEGER NOT NULL,
  reused              INTEGER NOT NULL,
  ran_seconds         REAL NOT NULL,
  waited_seconds      REAL NOT NULL,
  waited_by_cause     TEXT NOT NULL CHECK (json_valid(waited_by_cause)),
  requests_by_source  TEXT NOT NULL CHECK (json_valid(requests_by_source)),
  tokens_in           INTEGER NOT NULL,
  tokens_out          INTEGER NOT NULL,
  cost_usd            REAL NOT NULL,
  inner_cost_usd      REAL NOT NULL,
  rows_written        INTEGER NOT NULL,
  PRIMARY KEY (day, step, step_version, writer, outcome)
) STRICT, WITHOUT ROWID;

CREATE TABLE measure_claim (
  claim_id        INTEGER PRIMARY KEY REFERENCES claim (id),
  first_seen_at   TEXT NOT NULL,
  last_step_at    TEXT NOT NULL,
  spans           INTEGER NOT NULL,
  ran_seconds     REAL NOT NULL,
  waited_seconds  REAL NOT NULL,
  cost_usd        REAL NOT NULL
) STRICT;

-- The small icon an outlet's own site serves; a row with no content says it had none.
CREATE TABLE outlet_icon (
  domain      TEXT PRIMARY KEY,
  icon_url    TEXT,
  media_type  TEXT,
  content     BLOB,
  fetched_at  TEXT NOT NULL,
  changed_run TEXT NOT NULL REFERENCES run (id),
  CHECK ((content IS NULL) = (media_type IS NULL) AND (content IS NULL) = (icon_url IS NULL))
) STRICT, WITHOUT ROWID;

-- Domains readers asked about that are on no outlet list: a count by day, no address.
CREATE TABLE unlisted_domain_count (
  domain  TEXT NOT NULL,
  day     TEXT NOT NULL CHECK (length(day) = 10),
  asked   INTEGER NOT NULL CHECK (asked > 0),
  PRIMARY KEY (domain, day)
) STRICT, WITHOUT ROWID;

-- Each deployment: what the live site was built from.
CREATE TABLE deployment (
  id               INTEGER PRIMARY KEY,
  export_sha256    TEXT NOT NULL,
  export_taken_at  TEXT NOT NULL,
  claims           INTEGER NOT NULL,
  events           INTEGER NOT NULL,
  held             INTEGER NOT NULL,
  run_id           TEXT NOT NULL REFERENCES run (id)
) STRICT;

-- ---------------------------------------------------------------------------------------
-- 10. Search (FTS5)
-- ---------------------------------------------------------------------------------------

-- Trials by title, condition and intervention name, for the site's search and for finding
-- a claim's candidate trials. The index reads the table's own columns; three triggers
-- keep it in step.
CREATE VIRTUAL TABLE registry_trial_fts USING fts5 (
  title, conditions, intervention_names,
  content = 'registry_trial', content_rowid = 'id', tokenize = 'unicode61 remove_diacritics 2'
);
CREATE TRIGGER registry_trial_fts_insert AFTER INSERT ON registry_trial BEGIN
  INSERT INTO registry_trial_fts (rowid, title, conditions, intervention_names)
  VALUES (new.id, new.title, new.conditions, new.intervention_names);
END;
CREATE TRIGGER registry_trial_fts_delete AFTER DELETE ON registry_trial BEGIN
  INSERT INTO registry_trial_fts (registry_trial_fts, rowid, title, conditions, intervention_names)
  VALUES ('delete', old.id, old.title, old.conditions, old.intervention_names);
END;
CREATE TRIGGER registry_trial_fts_update
AFTER UPDATE OF title, conditions, intervention_names ON registry_trial BEGIN
  INSERT INTO registry_trial_fts (registry_trial_fts, rowid, title, conditions, intervention_names)
  VALUES ('delete', old.id, old.title, old.conditions, old.intervention_names);
  INSERT INTO registry_trial_fts (rowid, title, conditions, intervention_names)
  VALUES (new.id, new.title, new.conditions, new.intervention_names);
END;

-- Lead titles, for the topic words screening and the reading order look for. The spike
-- found the same 322 leads this way as Postgres's regular expression did.
CREATE VIRTUAL TABLE link_lead_fts USING fts5 (
  title, content = 'link_lead', content_rowid = 'id', tokenize = 'unicode61 remove_diacritics 2'
);
CREATE TRIGGER link_lead_fts_insert AFTER INSERT ON link_lead BEGIN
  INSERT INTO link_lead_fts (rowid, title) VALUES (new.id, new.title);
END;
CREATE TRIGGER link_lead_fts_delete AFTER DELETE ON link_lead BEGIN
  INSERT INTO link_lead_fts (link_lead_fts, rowid, title) VALUES ('delete', old.id, old.title);
END;

-- Claims by headline, condition and every name of their intervention. It keeps its own
-- copy of the words, and the merge's last statements rewrite the rows of claims a run
-- touched. A search joins `claim_public`, so a held claim is never found.
CREATE VIRTUAL TABLE claim_fts USING fts5 (
  headline, indication, names, tokenize = 'unicode61 remove_diacritics 2'
);

-- ---------------------------------------------------------------------------------------
-- 11. Staged records with their parents found
-- ---------------------------------------------------------------------------------------

-- A staged record names its parent by natural key. These views find the parent, and a
-- record whose parent is not in the store is simply absent from them: it is then neither
-- added nor counted, the counts do not reconcile, and the merge is undone.

CREATE VIEW staged_of_claim AS
  SELECT s.run_id, s.kind, s.key, s.body, k.claim_id
  FROM staged s JOIN claim_key k ON k.slug = s.body ->> 'slug';

CREATE VIEW staged_of_article AS
  SELECT s.run_id, s.kind, s.key, s.body, s.claim_id, a.id AS source_article_id
  FROM staged_of_claim s
  JOIN source_article a ON a.claim_id = s.claim_id AND a.url_key = s.body ->> 'url_key';

CREATE VIEW staged_of_entity AS
  SELECT s.run_id, s.kind, s.key, s.body, s.claim_id, e.id AS entity_id
  FROM staged_of_claim s
  JOIN entity e ON e.claim_id = s.claim_id
               AND e.type = s.body ->> 'entity_type' AND e.name = s.body ->> 'entity_name';

CREATE VIEW staged_of_lead AS
  SELECT s.run_id, s.kind, s.key, s.body, l.id AS link_lead_id
  FROM staged s JOIN link_lead l ON l.url_key = s.body ->> 'lead_url_key';

CREATE VIEW staged_of_trial AS
  SELECT s.run_id, s.kind, s.key, s.body, t.id AS trial_id
  FROM staged s
  JOIN registry_trial t ON t.registry_name = s.body ->> 'registry_name'
                       AND t.external_id = s.body ->> 'trial_id';

-- A staged merge of one claim into another: the claim that goes and the claim that stays.
CREATE VIEW staged_claim_merge AS
  SELECT s.run_id, gone.id AS gone_id, k.claim_id AS kept_id, kept.slug AS kept_slug, s.body
  FROM staged s
  JOIN claim gone ON gone.slug = s.body ->> 'slug' AND gone.merged_into IS NULL
  JOIN claim_key k ON k.slug = s.body ->> 'into_slug'
  JOIN claim kept ON kept.id = k.claim_id
  WHERE s.kind = 'action' AND s.body ->> 'action' = 'merge' AND gone.id <> k.claim_id;
