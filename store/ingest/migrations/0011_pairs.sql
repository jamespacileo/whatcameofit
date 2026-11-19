-- The pairs the lab tracks, as the site reads them (change `pairs-site`). A bundle is one
-- folder of the lab's page files (`lab pipeline pages`), named by the checksum of its
-- files. Its rows are loaded under that version and become what the site reads only when
-- the last statement of the load marks the version current, so a load that stops half way
-- changes nothing a reader sees. The tables hold public records only: the lab's page
-- models cannot reach a private field, and a bundle holds no article text.

CREATE TABLE pair_bundle (
  version TEXT PRIMARY KEY,
  loaded_at TEXT NOT NULL,
  counts TEXT NOT NULL CHECK (json_type(counts) = 'object'),
  current INTEGER NOT NULL DEFAULT 0 CHECK (current IN (0, 1))
) STRICT;

CREATE UNIQUE INDEX pair_bundle_one_current ON pair_bundle (current) WHERE current = 1;

-- Every page file as the lab wrote it, for the one keyed read a page is rendered from.
-- A statement is at most 100,000 bytes (docs/sources.md, D1), so a long file is kept in
-- parts, read back in order and joined.
CREATE TABLE pair_page (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  model TEXT NOT NULL,
  key TEXT NOT NULL,
  part INTEGER NOT NULL CHECK (part >= 0),
  body TEXT NOT NULL,
  PRIMARY KEY (version, model, key, part)
) STRICT, WITHOUT ROWID;

CREATE TABLE pair_intervention (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  id TEXT NOT NULL,
  slug TEXT NOT NULL,
  preferred_name TEXT NOT NULL,
  key_kind TEXT NOT NULL,
  approach TEXT,
  registry_type TEXT,
  PRIMARY KEY (version, id)
) STRICT, WITHOUT ROWID;

CREATE INDEX pair_intervention_slug ON pair_intervention (version, slug);

CREATE TABLE pair_intervention_name (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  intervention_id TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  searchable INTEGER NOT NULL CHECK (searchable IN (0, 1)),
  PRIMARY KEY (version, intervention_id, name)
) STRICT, WITHOUT ROWID;

CREATE INDEX pair_intervention_name_name ON pair_intervention_name (version, name COLLATE NOCASE) WHERE searchable = 1;

CREATE TABLE pair_condition (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  descriptor_id TEXT NOT NULL,
  slug TEXT NOT NULL,
  label TEXT NOT NULL,
  PRIMARY KEY (version, descriptor_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX pair_condition_slug ON pair_condition (version, slug);

-- One tracked pair. `status_code` is the lab's code: the site owns every word shown for it.
CREATE TABLE pair (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  key TEXT NOT NULL,
  address TEXT NOT NULL,
  intervention_id TEXT NOT NULL,
  condition_id TEXT NOT NULL,
  status_code TEXT NOT NULL,
  status_as_of TEXT NOT NULL,
  vertical TEXT,
  checked_by_person INTEGER NOT NULL CHECK (checked_by_person IN (0, 1)),
  trials INTEGER NOT NULL CHECK (trials >= 0),
  claim_slug TEXT,
  PRIMARY KEY (version, key)
) STRICT, WITHOUT ROWID;

CREATE UNIQUE INDEX pair_address ON pair (version, address);
CREATE INDEX pair_by_intervention ON pair (version, intervention_id);
CREATE INDEX pair_by_condition ON pair (version, condition_id);
CREATE INDEX pair_by_vertical ON pair (version, vertical);
CREATE INDEX pair_by_claim_slug ON pair (version, claim_slug) WHERE claim_slug IS NOT NULL;

CREATE TABLE pair_trial (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  pair_key TEXT NOT NULL,
  nct_id TEXT NOT NULL,
  arms TEXT NOT NULL CHECK (json_type(arms) = 'array'),
  claim_arm TEXT,
  PRIMARY KEY (version, pair_key, nct_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX pair_trial_by_trial ON pair_trial (version, nct_id);

-- What the registry record of a pair's trial states, for lists and search. The page's own
-- file holds the whole record.
CREATE TABLE pair_trial_facts (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  nct_id TEXT NOT NULL,
  title TEXT,
  phases TEXT NOT NULL CHECK (json_type(phases) = 'array'),
  overall_status TEXT,
  start_day TEXT,
  completion_day TEXT,
  as_of TEXT,
  PRIMARY KEY (version, nct_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE pair_status_change (
  version TEXT NOT NULL REFERENCES pair_bundle (version),
  pair_key TEXT NOT NULL,
  on_day TEXT NOT NULL,
  before TEXT,
  after TEXT NOT NULL,
  PRIMARY KEY (version, pair_key, on_day, after)
) STRICT, WITHOUT ROWID;

CREATE INDEX pair_status_change_by_day ON pair_status_change (version, on_day);
