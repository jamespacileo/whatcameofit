// Every model the review site accounts for, keyed to where it is defined: each D1 table that
// the store's migrations create (store/ingest/migrations) and each page model of the lab's
// bundle export (its JSON Schemas, `pair_page` rows of the model `$schema`). The operator
// reads the `name`; the details view shows the exact table or model, the migration, and per
// environment whether it is present, absent, or not readable yet (the operator, 2026-11-21).
// tests/catalogue.test.mjs holds this list to the migrations: a table added or dropped there
// fails the test until it is listed here.
//
// `hidden` columns are never sent to the browser. They hold text the site must never show
// (an article's words: CLAUDE.md, "Never store or display article text"), raw payloads, or
// bytes; the row's other columns still are.
// Search indexes (`*_fts` and their shadow tables) and SQLite's own tables are not models.

// Each table's primary key, in key order: records are paged in this order and one record is
// addressed by its key's values. tests/catalogue.test.mjs holds these to the migrated schema.
export const KEYS = Object.freeze({
  pair_bundle: ["version"],
  pair: ["version", "key"],
  pair_intervention: ["version", "id"],
  pair_intervention_name: ["version", "intervention_id", "name"],
  pair_condition: ["version", "descriptor_id"],
  pair_trial: ["version", "pair_key", "nct_id"],
  pair_trial_facts: ["version", "nct_id"],
  pair_status_change: ["version", "pair_key", "on_day", "after"],
  pair_page: ["version", "model", "key", "part"],
  registry_trial: ["id"],
  registry_trial_status: ["trial_id", "seen_at"],
  registry_load: ["registry_name", "condition"],
  trial_read: ["id"],
  trial_paper: ["id"],
  trial_slice: ["rule", "year", "number"],
  source_record: ["kind", "source_name", "external_id"],
  entity_substance: ["entity_id"],
  claim: ["id"],
  claim_alias: ["slug"],
  claim_action: ["id"],
  claim_term: ["id"],
  source_article: ["id"],
  promise: ["id"],
  reported_statement: ["id"],
  entity: ["id"],
  entity_article: ["entity_id", "source_article_id"],
  entity_match: ["id"],
  evidence_event: ["id"],
  evidence_conflict: ["id"],
  failure_flag: ["id"],
  measure_claim: ["claim_id"],
  deployment: ["id"],
  outlet_icon: ["domain"],
  article_lead: ["id"],
  link_lead: ["id"],
  link_share: ["link_lead_id", "platform", "community", "shared_at"],
  link_lead_link: ["link_lead_id", "record_kind", "record_key", "reason"],
  link_lead_label: ["link_lead_id", "labelled_by"],
  lead_reading: ["link_lead_id"],
  unlisted_domain_count: ["domain", "day"],
  store_step: ["step"],
  run: ["id"],
  run_step: ["run_id", "step"],
  run_stated: ["run_id", "kind"],
  stg: ["run_id", "kind", "key"],
  merging: ["id"],
  merge_report: ["run_id", "kind"],
  merge_guard: ["run_id"],
  payload: ["sha256"],
  work_item: ["record_kind", "record_key", "step"],
  work_entry: ["record_kind", "record_key", "step", "step_version"],
  work_slice: ["platform", "community", "month"],
  decision_log: ["run_id", "seq"],
  llm_usage: ["run_id", "seq"],
  measure_daily: ["day", "step", "step_version", "writer", "outcome"],
  ingest_chunk: ["run_id", "sha256"],
  inbox: ["seq"],
  inbox_folded: ["run_id"],
  inbox_fold: ["object"],
});

const table = (id, name, area, migration, extra = {}) => ({ id, kind: "table", table: id, name, area, migration, key: KEYS[id], ...extra });

export const AREAS = Object.freeze(["Pairs", "Page models", "Registry", "Legacy claims", "Leads", "Operations"]);

export const TABLES = Object.freeze([
  // Pairs: what the site reads, one copy per bundle version (0011).
  table("pair_bundle", "Bundles", "Pairs", "0011_pairs.sql", { hidden: [] }),
  table("pair", "Pairs", "Pairs", "0011_pairs.sql", { versioned: true }),
  table("pair_intervention", "Treatments", "Pairs", "0011_pairs.sql", { versioned: true }),
  table("pair_intervention_name", "Treatment names", "Pairs", "0011_pairs.sql", { versioned: true }),
  table("pair_condition", "Conditions", "Pairs", "0011_pairs.sql", { versioned: true }),
  table("pair_trial", "Pair trials", "Pairs", "0011_pairs.sql", { versioned: true }),
  table("pair_trial_facts", "Trial facts", "Pairs", "0011_pairs.sql", { versioned: true }),
  table("pair_status_change", "Status changes", "Pairs", "0011_pairs.sql", { versioned: true }),
  // The page files themselves are read through their page models, not as rows.
  table("pair_page", "Page files", "Pairs", "0011_pairs.sql", { versioned: true, hidden: ["body"] }),

  // Registry records and what was read from them.
  table("registry_trial", "Registry trials", "Registry", "0001_store_schema.sql"),
  table("registry_trial_status", "Registry status history", "Registry", "0001_store_schema.sql"),
  table("registry_load", "Registry loads", "Registry", "0001_store_schema.sql"),
  table("trial_read", "Trial readings", "Registry", "0001_store_schema.sql"),
  table("trial_paper", "Trial papers", "Registry", "0006_trial_papers_and_slices.sql"),
  table("trial_slice", "Trial slices", "Registry", "0006_trial_papers_and_slices.sql"),
  table("source_record", "Source records", "Registry", "0001_store_schema.sql", { hidden: ["body"] }),
  table("entity_substance", "Substance codes", "Registry", "0001_store_schema.sql"),

  // Claims, removed from the site on 2026-11-20; kept in the store as it was.
  table("claim", "Claims", "Legacy claims", "0001_store_schema.sql"),
  table("claim_alias", "Claim aliases", "Legacy claims", "0001_store_schema.sql"),
  table("claim_action", "Claim actions", "Legacy claims", "0001_store_schema.sql"),
  table("claim_term", "Claim terms", "Legacy claims", "0001_store_schema.sql"),
  table("source_article", "Source articles", "Legacy claims", "0001_store_schema.sql"),
  table("promise", "Promises", "Legacy claims", "0001_store_schema.sql"),
  table("reported_statement", "Reported statements", "Legacy claims", "0001_store_schema.sql", { hidden: ["text", "text_key"] }),
  table("entity", "Entities", "Legacy claims", "0001_store_schema.sql"),
  table("entity_article", "Entity articles", "Legacy claims", "0001_store_schema.sql"),
  table("entity_match", "Entity matches", "Legacy claims", "0001_store_schema.sql"),
  table("evidence_event", "Evidence events", "Legacy claims", "0001_store_schema.sql"),
  table("evidence_conflict", "Evidence conflicts", "Legacy claims", "0001_store_schema.sql"),
  table("failure_flag", "Failure flags", "Legacy claims", "0001_store_schema.sql"),
  table("measure_claim", "Claim measures", "Legacy claims", "0001_store_schema.sql"),
  table("deployment", "Deployments", "Legacy claims", "0001_store_schema.sql"),
  table("outlet_icon", "Outlet icons", "Legacy claims", "0001_store_schema.sql", { hidden: ["content"] }),

  // Leads: links found where people share news.
  table("article_lead", "Article leads", "Leads", "0001_store_schema.sql"),
  table("link_lead", "Link leads", "Leads", "0001_store_schema.sql"),
  table("link_share", "Link shares", "Leads", "0001_store_schema.sql"),
  table("link_lead_link", "Lead links", "Leads", "0001_store_schema.sql"),
  table("link_lead_label", "Lead labels", "Leads", "0001_store_schema.sql"),
  table("lead_reading", "Lead readings", "Leads", "0001_store_schema.sql"),
  table("unlisted_domain_count", "Unlisted domains", "Leads", "0001_store_schema.sql"),

  // Operations: runs, merges, queues and spending.
  table("store_step", "Store steps", "Operations", "0001_store_schema.sql"),
  table("run", "Runs", "Operations", "0001_store_schema.sql"),
  table("run_step", "Run steps", "Operations", "0001_store_schema.sql"),
  table("run_stated", "Run statements", "Operations", "0001_store_schema.sql"),
  table("stg", "Staged records", "Operations", "0001_store_schema.sql", { hidden: ["body"] }),
  table("merging", "Merges in progress", "Operations", "0001_store_schema.sql"),
  table("merge_report", "Merge reports", "Operations", "0001_store_schema.sql"),
  table("merge_guard", "Merge guards", "Operations", "0001_store_schema.sql"),
  table("payload", "Payloads", "Operations", "0007_payload_inline_limit.sql", { hidden: ["body"] }),
  table("work_item", "Work items", "Operations", "0001_store_schema.sql"),
  table("work_entry", "Work entries", "Operations", "0008_work_entry_waits.sql"),
  table("work_slice", "Work slices", "Operations", "0001_store_schema.sql"),
  table("decision_log", "Decisions", "Operations", "0001_store_schema.sql", { hidden: ["options", "output"] }),
  table("llm_usage", "Model usage", "Operations", "0001_store_schema.sql"),
  table("measure_daily", "Daily measures", "Operations", "0001_store_schema.sql"),
  table("ingest_chunk", "Ingest chunks", "Operations", "0002_ingest_service.sql"),
  table("inbox", "Inbox", "Operations", "0003_inbox.sql", { hidden: ["body"] }),
  table("inbox_folded", "Inbox folded runs", "Operations", "0004_inbox_folded.sql"),
  table("inbox_fold", "Inbox folds", "Operations", "0005_inbox_fold.sql"),
]);

/** The page models of the lab's bundle export: one schema and one page file per record. */
const page = (model, name) => ({ id: `page:${model}`, kind: "page-model", model, name, area: "Page models", source: "bundle schema" });

export const PAGE_MODELS = Object.freeze([
  page("PairPage", "Pair pages"),
  page("PairInterventionPage", "Treatment pages"),
  page("PairTopicPage", "Topic pages"),
  page("PairTopicsPage", "Topics index"),
  page("PairClinicalCategoryPage", "Clinical category pages"),
  page("PairDataFile", "Pair data files"),
  page("PairChangesFeed", "Changes feed"),
]);

export const MODELS = Object.freeze([...TABLES, ...PAGE_MODELS]);

export const modelById = new Map(MODELS.map((model) => [model.id, model]));

/** Names in sqlite_master that are not models: search indexes, their shadow tables, SQLite's own. */
export const notAModel = (name) => /_fts(_[a-z]+)?$/.test(name) || name.startsWith("sqlite_") || name.startsWith("_cf_");
