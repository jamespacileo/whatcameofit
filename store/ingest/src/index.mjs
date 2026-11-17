// The ingest service's HTTP routes. It answers only to tokens (src/auth.mjs), holds no
// rule of the tracker, runs no statement a caller wrote, and logs nothing: not a token,
// not a record, not a payload, not an address.
//
//   POST   /runs                  register a run: who, which device, what kind of writer
//   PUT    /payloads/<sha256>     a raw payload over 16 KB, into R2 under its checksum
//   POST   /runs/<id>/records     stage one chunk of records in natural-key form
//   POST   /runs/<id>/merge       the merge; the same run twice adds nothing
//   POST   /runs/<id>/preview     the report without applying; the run is then dropped
//   GET    /runs/<id>             what the merge did
//   DELETE /runs/<id>             drop a run that was not merged
//   GET    /inbox?after=&limit=   records of the bulk tier that runs handed over, oldest first
//   POST   /inbox/folded          a fold is recorded from its delta in the bucket and the build's list: {object}
//   POST   /inbox/clear           no further than the furthest fold recorded: {through}
//   GET    /progress              counts only: each slice of trials by stage (trial_slice), last runs, rows by table
//   GET    /progress/page         the same as a page; it holds nothing until a token is typed into it
//   POST   /work/lease|finish|fail    the consumer's queue of due work
//   POST   /slices/take|release       a device's work slices
import { principal } from "./auth.mjs";
import { Refusal, checkRecords } from "./check.mjs";
import { sha256 } from "./hash.mjs";
import { peopleInText } from "./people.mjs";
import { INLINE_PAYLOAD_BYTES, MAX_LEASE, MAX_LEASE_SECONDS, MAX_R2_PAYLOADS_A_CHUNK, MAX_INBOX_RECORDS, MAX_REGISTRATION_BYTES, D1, limits } from "./limits.mjs";
import { INGEST } from "./sql.generated.mjs";
import * as store from "./store.mjs";
import { progress } from "./progress.mjs";
import { PAGE } from "./page.mjs";

const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const refuse = (status, code, message, detail) => { throw new Refusal(status, code, message, detail); };

// The body, read only when it says what it is and how long, and never past its bound.
async function body(request, types, most) {
  const type = (request.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
  if (!types.includes(type)) refuse(415, "content_type", `the body must be ${types.join(" or ")}`);
  const length = request.headers.get("content-length");
  const stated = Number(length);
  if (!/^\d{1,12}$/.test(length || "")) refuse(411, "length_required", "the body's length must be stated");
  if (stated > most) refuse(413, "too_large", `the body is at most ${most} bytes`);
  const bytes = new Uint8Array(await request.arrayBuffer());
  if (bytes.length > most) refuse(413, "too_large", `the body is at most ${most} bytes`);
  return bytes;
}

async function jsonBody(request, most) {
  const bytes = await body(request, ["application/json"], most);
  try { return { bytes, value: JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) }; } catch { return refuse(400, "not_json", "the body is not JSON in UTF-8"); }
}

const RUN_ID = /^[A-Za-z0-9_-]{1,64}$/;
const SHA = /^[0-9a-f]{64}$/;
const NAME = /^[A-Za-z0-9._-]{1,64}$/;

// A run a token may reach: one it could have registered. Any other answers as if absent.
async function ownRun(env, who, id) {
  const run = RUN_ID.test(id) ? await store.getRun(env.STORE, id) : null;
  if (!run || !who.writers.includes(run.writer) || (who.role === "device" && run.device !== who.device)) refuse(404, "no_such_run", "no such run");
  return run;
}

async function register(request, env, who) {
  const { value } = await jsonBody(request, MAX_REGISTRATION_BYTES);
  const { id, writer, request_class, commit, steps = {}, counts = {}, checksum } = value || {};
  if (!RUN_ID.test(id || "")) refuse(400, "bad_run", "a run's id is 1 to 64 letters, digits, - or _");
  if (!who.writers.includes(writer)) refuse(403, "outside_scope", `a ${who.role} token may not register this kind of writer`);
  const device = who.role === "device" ? who.device : writer === "lookup" ? null : value.device ?? who.device;
  if (value.device != null && value.device !== device) refuse(403, "outside_scope", "a token registers runs for its own device only");
  if (device != null && !NAME.test(device)) refuse(400, "bad_run", "a device's name is letters, digits, ., - or _");
  if (writer === "lookup" ? !["extension", "site"].includes(request_class) : request_class != null) refuse(400, "bad_run", "a lookup states its request class, and only a lookup does");
  if (!/^[0-9a-f]{7,40}$/.test(commit || "")) refuse(400, "bad_run", "a run states the commit of the code that wrote it");
  if (!SHA.test(checksum || "")) refuse(400, "bad_run", "a run states the checksum of the records it will hand over");
  const whole = (object) => object && typeof object === "object" && !Array.isArray(object) && Object.entries(object).every(([name, n]) => NAME.test(name) && Number.isInteger(n) && n >= 0);
  if (!whole(steps) || !whole(counts)) refuse(400, "bad_run", "steps and counts are objects of name to whole number");
  for (const kind of Object.keys(counts)) {
    if (!who.kinds.includes(kind)) refuse(403, "outside_scope", `a ${who.role} token may not hand over this kind of record`, { kind });
  }
  const most = limits(env).MAX_RUN_RECORDS;
  if (Object.values(counts).reduce((a, b) => a + b, 0) > most) refuse(413, "run_too_large", `a run is at most ${most} records: split it, parents first`);
  const before = await store.getRun(env.STORE, id);
  if (before) {
    // Registering again writes nothing, whatever the run has become; it only answers
    // whether this is the run that was registered.
    const was = await store.stated(env.STORE, id);
    const same = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
    if (before.writer !== writer || before.device !== device || before.stated_checksum !== checksum || (before.request_class ?? null) !== (request_class ?? null)
      || !same(was.steps, steps) || !same(was.counts, counts)) refuse(409, "run_exists", "this run was registered differently");
    return json(200, { id, status: before.status, registered_at: before.registered_at, again: true });
  }
  const run = await store.registerRun(env.STORE, { id, writer, device, request_class, commit, steps, counts, checksum });
  return json(201, { id, status: run.status, registered_at: run.registered_at, again: false });
}

async function putPayload(request, env, who, checksum) {
  if (!who.may.includes("payload")) refuse(403, "outside_scope", `a ${who.role} token may not hand over payloads`);
  if (!SHA.test(checksum)) refuse(400, "bad_checksum", "a payload is named by its SHA-256 in lower-case hex");
  const bytes = await body(request, ["application/octet-stream", "application/json"], limits(env).MAX_PAYLOAD_BYTES);
  if (bytes.length <= INLINE_PAYLOAD_BYTES) refuse(422, "small_payload", `a payload of ${INLINE_PAYLOAD_BYTES} bytes or less is kept in its staged record, not here`);
  if ((await sha256(bytes)) !== checksum) refuse(422, "checksum_mismatch", "the body is not what its checksum says; nothing was stored");
  // A registry record that still names people is not stored: the store keeps no personal data.
  const people = peopleInText(new TextDecoder("utf-8", { fatal: false }).decode(bytes));
  if (people.length) refuse(422, "personal_data", "a registry record is handed over without the people it names; nothing was stored", { people });
  const key = `payload/${checksum}`;
  if (await env.PAYLOADS.head(key)) return json(200, { key, bytes: bytes.length, stored: false });
  await env.PAYLOADS.put(key, bytes, { sha256: checksum });
  return json(201, { key, bytes: bytes.length, stored: true });
}

async function stage(request, env, who, id) {
  const run = await ownRun(env, who, id);
  if (run.status !== "registered") refuse(409, "run_closed", `this run is ${run.status} and takes no more records`);
  const bounds = limits(env);
  const { bytes, value } = await jsonBody(request, bounds.MAX_CHUNK_BYTES);
  const checksum = request.headers.get("x-content-sha256") || "";
  if (!SHA.test(checksum) || (await sha256(bytes)) !== checksum) refuse(422, "checksum_mismatch", "the chunk is not what its X-Content-SHA256 says; nothing was staged");
  if (Array.isArray(value) && value.length > bounds.MAX_CHUNK_RECORDS) refuse(413, "chunk_too_large", `a chunk is at most ${bounds.MAX_CHUNK_RECORDS} records`);
  const { r2, unheld } = await checkRecords(value, who);
  // What is staged is the checked value written out again, not the bytes that arrived:
  // a key given twice reads one way to JSON.parse and another to SQLite.
  const text = JSON.stringify(value);
  if (new TextEncoder().encode(text).length > D1.stringBytes - 50_000) refuse(413, "too_large", "the chunk is too large once written out");
  if (unheld.length) {
    const free = await store.released(env.STORE, unheld.map((claim) => claim.slug));
    const first = unheld.find((claim) => !free.has(claim.slug));
    if (first) refuse(403, "outside_scope", `a ${who.role} token hands over an approved claim only with its audit hold`, { record: first.at, kind: "claim", field: "awaiting_audit_at" });
  }
  if (r2.length > MAX_R2_PAYLOADS_A_CHUNK) refuse(413, "chunk_too_large", `a chunk names at most ${MAX_R2_PAYLOADS_A_CHUNK} payloads kept in R2`);
  // A payload kept in R2 is looked for before its record is staged, five at a time.
  for (let i = 0; i < r2.length; i += 5) {
    const found = await Promise.all(r2.slice(i, i + 5).map((p) => env.PAYLOADS.head(`payload/${p.sha256}`)));
    for (const [n, object] of found.entries()) {
      const p = r2[i + n];
      if (!object) refuse(409, "payload_not_handed_over", "this payload was never put to /payloads", { record: p.at, kind: "payload" });
      if (object.size !== p.bytes) refuse(422, "checksum_mismatch", "the payload held is not the size its record says", { record: p.at, kind: "payload" });
    }
  }
  const done = await store.stageChunk(env.STORE, id, text, checksum, value.length);
  if (!done.accepted) refuse(409, "run_closed", "this run takes no more records");
  return json(200, { run: id, records: value.length, staged: done.staged, again: done.again });
}

async function merge(env, who, id, ctx) {
  await ownRun(env, who, id);
  const done = await store.merge(env.STORE, id);
  // The message only wakes the consumer; what is due is read from the store, so a
  // message that is lost loses nothing. It says nothing of a reader or of a time.
  if (done.status === "merged" && !done.again && env.WORK) {
    ctx.waitUntil(store.dueSteps(env.STORE).then((steps) => Promise.all(steps.map((step) => env.WORK.send({ wake: step })))).catch(() => {}));
  }
  const status = { merged: 200, refused: 409, undone: 409, not_merged: 409 }[done.status] ?? 409;
  return json(status, { run: id, ...done });
}

async function work(request, env, who, verb) {
  if (!who.may.includes("work")) refuse(403, "outside_scope", `a ${who.role} token may not take work`);
  const { value: v } = await jsonBody(request, MAX_REGISTRATION_BYTES);
  const text = (...names) => names.every((name) => typeof v?.[name] === "string" && v[name].length && v[name].length <= 500) || refuse(400, "bad_request", `${names.join(", ")} are needed`);
  const db = env.STORE;
  if (verb === "lease") {
    text("step");
    const count = Math.min(Math.max(Number(v.count) || 1, 1), MAX_LEASE);
    const seconds = Math.min(Math.max(Number(v.lease_seconds) || 600, 1), MAX_LEASE_SECONDS);
    const until = store.stamp(new Date(Date.now() + seconds * 1000));
    const { results } = await db.prepare(INGEST.lease_work).bind(v.step, count, store.now(), until).all();
    return json(200, { leased: results, lease_until: until });
  }
  text("kind", "key", "step");
  if (verb === "finish") await db.prepare(INGEST.finish_work).bind(v.kind, v.key, v.step).run();
  else {
    // The kind of error, as a short code: never a message that could quote a page.
    if (!/^[a-z0-9_]{1,60}$/.test(v.error || "")) refuse(400, "bad_request", "error is a short code of lower-case letters, digits and _");
    await db.prepare(INGEST.fail_work).bind(v.kind, v.key, v.step, v.error, Math.min(Math.max(Number(v.max_attempts) || 3, 1), 20)).run();
  }
  const item = await db.prepare("SELECT state, attempts, error FROM work_item WHERE record_kind = ?1 AND record_key = ?2 AND step = ?3").bind(v.kind, v.key, v.step).first();
  return item ? json(200, item) : refuse(404, "no_such_work", "no such work");
}

async function slice(request, env, who, verb) {
  if (!who.may.includes("slice")) refuse(403, "outside_scope", `a ${who.role} token may not take a slice`);
  const { value: v } = await jsonBody(request, MAX_REGISTRATION_BYTES);
  const device = who.role === "device" ? who.device : v?.device;
  if (![v?.platform, v?.community, device].every((name) => NAME.test(name || "")) || !/^\d{4}-\d{2}$/.test(v?.month || "")) refuse(400, "bad_request", "platform, community, month (YYYY-MM) and a device are needed");
  if (verb === "release") {
    await env.STORE.prepare(INGEST.release_slice).bind(v.platform, v.community, v.month, device).run();
    return json(200, { released: true });
  }
  const seconds = Math.min(Math.max(Number(v.lapse_seconds) || 86_400, 1), 7 * 86_400);
  const lapses = store.stamp(new Date(Date.now() + seconds * 1000));
  const { results } = await env.STORE.prepare(INGEST.take_slice).bind(v.platform, v.community, v.month, device, store.now(), lapses).all();
  return json(results.length ? 200 : 409, { taken: results.length > 0, device: results[0]?.device ?? null, lapses_at: results.length ? lapses : null });
}

// The inbox of the bulk tier, for the daily job, the bulk file's one writer.
async function inbox(request, env, who, url, verb) {
  if (!who.may.includes("inbox")) refuse(403, "outside_scope", `a ${who.role} token may not read or clear the inbox`);
  const whole = (text) => (/^\d{1,15}$/.test(text ?? "") ? Number(text) : null);
  if (verb !== "read") {
    const { value } = await jsonBody(request, MAX_REGISTRATION_BYTES);
    const stated = Number.isInteger(value?.through) && value.through >= 0 ? value.through : null;
    if (verb === "folded") {
      // The delta that holds what was folded must already be in the bucket, beside its
      // build, and listed in the build's deltas.json. How far it folded is read from that
      // list, written when the delta was uploaded, never taken from the caller.
      const key = /^(bulk\/[A-Za-z0-9._-]{1,64})\/(delta-[A-Za-z0-9._-]{1,80})$/.exec(value?.object || "");
      if (!key) refuse(400, "bad_request", "object is the delta's key: bulk/<build id>/delta-...");
      const [held, list] = await Promise.all([env.PAYLOADS.head(value.object), env.PAYLOADS.get(`${key[1]}/deltas.json`)]);
      if (!held || !held.size) refuse(409, "delta_not_uploaded", "no such delta object is in the bucket: upload it first");
      let listed = null;
      try { listed = (await list?.json())?.deltas?.find((delta) => delta.name === key[2]) ?? null; } catch { listed = null; }
      if (!listed) refuse(409, "delta_not_listed", "the build's deltas.json does not list this delta: upload it with scripts/upload-delta.mjs");
      if (listed.bytes !== held.size) refuse(409, "delta_differs", "the object is not the size its build's list says");
      if (!Number.isInteger(listed.through) || listed.through < 0) refuse(409, "delta_has_no_through", "the build's list does not say how far this delta folded the inbox: upload it with --through");
      if (stated !== null && stated !== listed.through) refuse(409, "through_differs", "the delta's own list says another through", { listed_through: listed.through });
      const recorded = await store.recordFold(env.STORE, value.object, listed.through, held.size);
      if (!recorded) refuse(409, "beyond_inbox", "through is past the last record the inbox has given");
      return json(200, recorded);
    }
    const through = stated;
    if (through === null) refuse(400, "bad_request", "through is the last record folded, as the inbox gave it");
    const folded = await store.foldedThrough(env.STORE);
    if (through > folded) refuse(409, "not_folded", "the inbox is cleared no further than the furthest fold recorded: record the fold first", { folded_through: folded });
    return json(200, await store.clearInbox(env.STORE, through));
  }
  const after = whole(url.searchParams.get("after") ?? "0"), limit = whole(url.searchParams.get("limit") ?? "500");
  if (after === null || limit === null || limit < 1) refuse(400, "bad_request", "after and limit are whole numbers");
  return json(200, await store.inbox(env.STORE, after, Math.min(limit, MAX_INBOX_RECORDS)));
}

// The progress page's shell: static, the same for everyone, with no count in it. It asks
// /progress itself, with the token typed into it. It may load nothing from anywhere else.
const page = () => new Response(PAGE, { status: 200, headers: {
  "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "referrer-policy": "no-referrer", "x-frame-options": "DENY", "x-content-type-options": "nosniff",
  "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
} });

// Asked too often. The platform's rate-limit bindings count for a minute in each
// Cloudflare location; they are approximate, and absent on this machine. A caller without
// a known token is counted by its address, which is used as the key and is neither stored
// nor logged; a caller with one, by the token's name.
const tooOften = async (limiter, key) => Boolean(limiter) && !(await limiter.limit({ key })).success;
const slowDown = () => json(429, { error: "too_many_requests" });

async function route(request, env, ctx) {
  const from = request.headers.get("cf-connecting-ip") || "unknown";
  if (request.method === "GET" && new URL(request.url).pathname === "/progress/page") return (await tooOften(env.LIMIT_UNKNOWN, from)) ? slowDown() : page();
  const who = await principal(request, env);
  // Without a token nothing answers, whatever was asked for.
  if (!who) return (await tooOften(env.LIMIT_UNKNOWN, from)) ? slowDown() : json(401, { error: "unauthorized" });
  if (await tooOften(env.LIMIT_TOKEN, who.name)) return slowDown();
  const { pathname } = new URL(request.url);
  const parts = pathname.split("/").filter(Boolean);
  const at = `${request.method} /${parts[0] || ""}${parts.length > 1 ? "/*" : ""}${parts[2] ? `/${parts[2]}` : ""}`;
  switch (at) {
    case "POST /runs": return register(request, env, who);
    case "PUT /payloads/*": return putPayload(request, env, who, parts[1]);
    case "POST /runs/*/records": return stage(request, env, who, parts[1]);
    case "POST /runs/*/merge": return merge(env, who, parts[1], ctx);
    case "POST /runs/*/preview": {
      await ownRun(env, who, parts[1]);
      const done = await store.preview(env.STORE, parts[1]);
      return json(done.previewed ? 200 : 409, { run: parts[1], ...done });
    }
    case "GET /runs/*": {
      await ownRun(env, who, parts[1]);
      return json(200, { run: parts[1], ...(await store.report(env.STORE, parts[1])) });
    }
    case "DELETE /runs/*": {
      const run = await ownRun(env, who, parts[1]);
      if (run.status !== "registered") refuse(409, "run_closed", `a ${run.status} run is kept`);
      await store.discard(env.STORE, parts[1]);
      return json(200, { run: parts[1], dropped: true });
    }
    case "GET /inbox": return inbox(request, env, who, new URL(request.url), "read");
    case "POST /inbox/*": if (parts[1] === "folded") return inbox(request, env, who, new URL(request.url), "folded"); if (parts[1] === "clear") return inbox(request, env, who, new URL(request.url), "clear"); break;
    case "GET /progress":
      if (!who.may.includes("progress")) refuse(403, "outside_scope", `a ${who.role} token may not read the progress`);
      return json(200, await progress(env.STORE));
    case "POST /work/*": if (["lease", "finish", "fail"].includes(parts[1])) return work(request, env, who, parts[1]); break;
    case "POST /slices/*": if (["take", "release"].includes(parts[1])) return slice(request, env, who, parts[1]); break;
  }
  return json(404, { error: "not_found" });
}

export default {
  async fetch(request, env, ctx) {
    try {
      return await route(request, env, ctx);
    } catch (error) {
      if (error instanceof Refusal) return json(error.status, { error: error.code, message: error.message, ...(error.detail ? { detail: error.detail } : {}) });
      // What failed is not said: a database error can quote the value it refused.
      return json(500, { error: "failed" });
    }
  },
};
