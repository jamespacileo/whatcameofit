// The bounds a writer is held to, each under a platform limit read from Cloudflare's
// documentation on 2026-11-17. The service refuses at the door what the platform would
// refuse later, so a refusal names its bound and nothing is half stored.
//
// developers.cloudflare.com/d1/platform/limits (Workers Paid):
//   - a statement is at most 100,000 bytes, and that holds for each statement of a batch;
//   - a query has at most 100 bound parameters;
//   - a string, BLOB or row is at most 2,000,000 bytes (the page does not say this of one
//     bound parameter; it is taken to hold, since the parameter becomes a string);
//   - a query runs at most 30 seconds, "this duration limit also applies to the entire
//     batch call";
//   - 1,000 queries a Worker invocation, where "a `db.batch()` call counts as a single
//     query";
//   - a result is at most 50 MB;
//   - the page states no limit on how many statements a batch holds.
// developers.cloudflare.com/d1/worker-api/d1-database: "Batched statements are SQL
//   transactions"; a failing statement "aborts or rolls back the entire sequence".
// developers.cloudflare.com/workers/platform/limits: 128 MB of memory an isolate; a
//   request body of 100 MB on the zone's plan; 10,000 subrequests a request, calls to R2
//   and D1 included; six connections open at once; a secret is at most 5 KB.
// developers.cloudflare.com/r2/platform/limits: one upload is at most 5 GiB; a key 1,024 bytes.
// developers.cloudflare.com/queues/platform/limits: a message is at most 128 KB.
export const D1 = { statementBytes: 100_000, boundParameters: 100, stringBytes: 2_000_000, batchSeconds: 30 };

// A payload of this size or less is kept in the store, in the staged `payload` record
// itself; only a larger one is an R2 object (design.md decision 2). The figure is the
// schema's, read from its CHECK on payload.body when the statements are bundled.
import { INLINE_PAYLOAD_BYTES } from "./sql.generated.mjs";
export { INLINE_PAYLOAD_BYTES };
// Below this a payload is never an object in the bucket: it always fits its record.
// Between this and the row's bound a writer keeps it in its record, and may put it in
// the bucket instead when the record would not fit once the payload is written as a JSON
// string (a body of mostly control characters grows sixfold).
export const OBJECT_FLOOR_BYTES = 16_384;
// A staged record is one row of `stg`, and the row it becomes must fit a row too.
// It is also large enough for the longest payload kept in a row once written as a JSON
// string inside its record, which at worst doubles it (every character escaped).
export const MAX_RECORD_BYTES = Math.max(1_000_000, 2 * INLINE_PAYLOAD_BYTES + 8_192);
// A string in a record. No field the schema has needs more, and it is far below an
// article's length; the fields in src/check.mjs that hold structured data are bounded by
// the record's size instead.
export const MAX_STRING_CHARS = 2_000;
// Fields a source's own record can make longer, each for one kind of record. A trial's
// arms can be many, and their names are joined into one string.
export const LONGER = { registry_trial: { intervention_names: 20_000 } };
// Registering a run: its steps and counts.
export const MAX_REGISTRATION_BYTES = 64_000;
// Payloads kept in R2 that one chunk may name: each is looked for before it is staged.
export const MAX_R2_PAYLOADS_A_CHUNK = 500;
// Records of the inbox one request may read: a Worker's answer is built in memory.
export const MAX_INBOX_RECORDS = 2_000;
// Due work one request may lease, and the longest lease.
export const MAX_LEASE = 100;
export const MAX_LEASE_SECONDS = 3_600;

const DEFAULTS = { MAX_RUN_RECORDS: 20_000, MAX_CHUNK_BYTES: 1_900_000, MAX_CHUNK_RECORDS: 5_000, MAX_PAYLOAD_BYTES: 8_000_000 };

// The bounds that are settings (wrangler.jsonc `vars`). A chunk is bound as one string, so
// no setting may raise it past D1's string size.
export function limits(env) {
  const out = {};
  for (const [name, fallback] of Object.entries(DEFAULTS)) {
    const value = Number(env[name]);
    out[name] = Number.isInteger(value) && value > 0 ? value : fallback;
  }
  out.MAX_CHUNK_BYTES = Math.min(out.MAX_CHUNK_BYTES, D1.stringBytes - 100_000);
  return out;
}
