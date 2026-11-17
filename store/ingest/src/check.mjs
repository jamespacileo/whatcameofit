// What a staged record must be before it is let near the store. The rules of the tracker
// are in store/merge.sql; these are the door's: a known kind, a natural key, only fields a
// statement reads, nothing long enough to be an article's text, a payload that is what its
// checksum says, and nothing outside the token's scope.
import { FIELDS } from "./sql.generated.mjs";
import { INLINE_PAYLOAD_BYTES, MAX_RECORD_BYTES, MAX_STRING_CHARS } from "./limits.mjs";
import { sha256 } from "./hash.mjs";

// store/README.md, "Kinds and the keys their bodies carry".
export const KINDS = ["payload", "claim", "source_article", "promise", "reported_statement", "entity", "entity_match",
  "entity_substance", "entity_article", "claim_term", "source_record", "evidence_event", "failure_flag", "trial_read",
  "registry_trial", "registry_load", "article_lead", "link_lead", "link_share", "link_lead_link", "link_lead_label",
  "lead_reading", "decision", "usage", "measure_daily", "measure_claim", "work_entry", "outlet_icon", "work_slice",
  "unlisted_domain", "action"];
export const ACTIONS = ["audit_clear", "archive", "unarchive", "rename", "merge", "conflict_accept", "conflict_dismiss", "publish"];

const KNOWN = new Set(FIELDS);
// Fields that hold a source's own structured record or a step's structured output, and
// the one kind of record each belongs to. There they are bounded by the record's size;
// on any other kind they are a string like any other, so no kind has a field that an
// article's text fits in.
const STRUCTURED = {
  payload: ["body"], source_record: ["body"], decision: ["output", "options"],
  entity_match: ["record_summary", "record_facts"], entity_substance: ["codes"],
  registry_trial: ["interventions", "conditions"], trial_read: ["readings", "refusals"],
  measure_daily: ["waited_by_cause", "requests_by_source", "spans"], measure_claim: ["spans"],
  lead_reading: ["trials"],
};
// Narrower bounds the schema itself states (a CHECK in store/schema.sql).
const SHORTER = { text: 200, slug: 60, new_slug: 60, into_slug: 60 };
const DECIDERS = ["reviewed_by", "decided_by", "labelled_by"];

export class Refusal extends Error {
  constructor(status, code, message, detail) { super(message); this.status = status; this.code = code; this.detail = detail; }
}

function longString(value, limit) {
  if (typeof value === "string") return value.length > limit;
  if (Array.isArray(value)) return value.some((item) => longString(item, limit));
  if (value && typeof value === "object") return Object.values(value).some((item) => longString(item, limit));
  return false;
}

// Refuses the chunk on its first bad record, naming the record by its place and kind and
// the field by its name. Never by a value: a refusal must not carry what was sent.
export async function checkRecords(records, who, bytes) {
  if (!Array.isArray(records)) throw new Refusal(400, "not_a_list", "the body must be a JSON list of records");
  const encoder = new TextEncoder();
  const r2 = [];
  for (const [at, record] of records.entries()) {
    const where = { record: at };
    const bad = (status, code, message, more) => { throw new Refusal(status, code, message, { ...where, ...more }); };
    if (!record || typeof record !== "object" || Array.isArray(record)) bad(400, "not_a_record", "a record is {kind, key, body}");
    const { kind, key, body, ...rest } = record;
    where.kind = typeof kind === "string" ? kind.slice(0, 40) : null;
    if (Object.keys(rest).length) bad(400, "not_a_record", "a record is {kind, key, body} and nothing else");
    if (!KINDS.includes(kind)) bad(400, "unknown_kind", "the store has no such kind of record");
    if (typeof key !== "string" || !key.length) bad(400, "no_natural_key", "a record without its natural key is refused");
    if (key.length > MAX_STRING_CHARS) bad(400, "field_too_long", "the natural key is too long");
    if (!body || typeof body !== "object" || Array.isArray(body)) bad(400, "not_a_record", "a record's body is a JSON object");
    if (!who.kinds.includes(kind)) bad(403, "outside_scope", `a ${who.role} token may not stage this kind of record`);
    for (const [field, value] of Object.entries(body)) {
      if (!KNOWN.has(field)) bad(422, "unknown_field", "no statement reads this field, so the store does not take it", { field });
      const limit = (STRUCTURED[kind] || []).includes(field) ? null : SHORTER[field] || MAX_STRING_CHARS;
      if (limit && longString(value, limit)) bad(422, "field_too_long", `this field holds at most ${limit} characters: the store keeps no article text`, { field });
    }
    if (encoder.encode(JSON.stringify(body)).length > MAX_RECORD_BYTES) bad(413, "record_too_large", `a record is at most ${MAX_RECORD_BYTES} bytes`);
    for (const field of DECIDERS) {
      if (body[field] != null && !who.deciders.includes(body[field])) bad(403, "outside_scope", `a ${who.role} token may not record this decider's decision`, { field });
    }
    if (kind === "action" && !who.actions.includes(body.action)) bad(403, "outside_scope", `a ${who.role} token may not state this action`, { field: "action" });
    if (kind === "payload") {
      if (!/^[0-9a-f]{64}$/.test(body.sha256 || "")) bad(422, "bad_checksum", "a payload is named by its SHA-256 in lower-case hex", { field: "sha256" });
      if (typeof body.body === "string" && body.r2_key == null) {
        const raw = encoder.encode(body.body);
        if (raw.length > INLINE_PAYLOAD_BYTES) bad(413, "payload_too_large_for_a_row", `a payload over ${INLINE_PAYLOAD_BYTES} bytes is put to /payloads first`);
        if (raw.length !== body.bytes || (await sha256(raw)) !== body.sha256) bad(422, "checksum_mismatch", "the payload is not what its checksum and size say");
      } else if (body.body == null && body.r2_key === `payload/${body.sha256}`) r2.push({ at, sha256: body.sha256, bytes: body.bytes });
      else bad(422, "bad_payload", "a payload carries its body, or the key payload/<sha256> of the object put first");
    }
  }
  return { r2, bytes };
}
