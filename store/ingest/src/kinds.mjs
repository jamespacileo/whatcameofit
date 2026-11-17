// The kinds of record the store takes and the commands an `action` record may state.
// store/README.md, "Kinds and the keys their bodies carry".
export const KINDS = ["payload", "claim", "source_article", "promise", "reported_statement", "entity", "entity_match",
  "entity_substance", "entity_article", "claim_term", "source_record", "evidence_event", "failure_flag", "trial_read",
  "registry_trial", "registry_load", "article_lead", "link_lead", "link_share", "link_lead_link", "link_lead_label",
  "lead_reading", "decision", "usage", "measure_daily", "measure_claim", "work_entry", "outlet_icon", "work_slice",
  "unlisted_domain", "action"];
// The kinds whose rows are in the bulk tier (pipeline/src/thenwhat/store/tiers.py,
// BULK_KINDS, and a lookup's reading, whose table is bulk too): kept in the inbox when a
// run hands them over.
export const INBOX_KINDS = ["registry_trial", "registry_load", "article_lead", "link_lead", "link_share", "link_lead_link", "link_lead_label",
  "lead_reading", "work_entry", "usage", "measure_daily", "measure_claim"];
export const ACTIONS = ["audit_clear", "archive", "unarchive", "rename", "merge", "conflict_accept", "conflict_dismiss", "publish"];
