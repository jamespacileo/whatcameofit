// The ingest service on this machine: Miniflare runs the Worker with D1's own local engine,
// an R2 bucket and a Queue, all on disk here. No account, no network, nothing deployed.
//
// The store is made the way a real one will be: `wrangler d1 migrations apply --local`
// applies migrations/ once into a template folder, and every test's store is a copy of it.
// Tests write only through the service's HTTP routes. They read the store through the D1
// binding to check what a request left, and set the one piece of the store's own
// configuration the service has no route for (`store_step`).
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
export const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
export const runChecksum = (chunks) => sha([...new Set(chunks)].sort().join("\n"));

// One token for each writer the scenarios use. Made here, known nowhere else.
const WRITERS = [
  { name: "device-mini", role: "device", device: "mini" },
  { name: "device-macbook", role: "device", device: "macbook" },
  { name: "daily", role: "daily", device: "mini" },
  { name: "lookup", role: "lookup" },
  { name: "consumer", role: "consumer" },
  { name: "export", role: "export" },
  { name: "operator", role: "operator" },
];
export const TOKENS = Object.fromEntries(WRITERS.map((w) => [w.name, `test-token-${w.name}-${sha(w.name).slice(0, 24)}`]));
export const ENTRIES = WRITERS.map((w) => ({ ...w, sha256: sha(TOKENS[w.name]) }));

let template = null;
let unavailable = null;

// Why the local engine cannot be used here, or null when it can. Found once.
export async function engineUnavailable() {
  if (template || unavailable) return unavailable;
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-ingest-"));
  try {
    execFileSync(join(root, "node_modules/.bin/wrangler"), ["d1", "migrations", "apply", "STORE", "--local", "--persist-to", dir],
      { cwd: root, env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: "pipe", timeout: 180_000 });
    // Wrangler leaves the schema in SQLite's write-ahead log. It is folded into the
    // database file here, so that a copy of the folder is a whole store.
    const { DatabaseSync } = await import("node:sqlite");
    const objects = join(dir, "v3/d1/miniflare-D1DatabaseObject");
    for (const file of readdirSync(objects).filter((name) => name.endsWith(".sqlite"))) {
      const db = new DatabaseSync(join(objects, file));
      db.exec("PRAGMA wal_checkpoint(TRUNCATE)");
      db.close();
    }
    template = dir;
  } catch (error) {
    unavailable = `D1's local engine is unavailable here (${String(error.message).split("\n")[0]}): install with \`pnpm --dir store/ingest install\` and try again`;
  }
  return unavailable;
}

process.on("exit", () => { if (template) rmSync(template, { recursive: true, force: true }); });

export class Service {
  static async open({ entries = ENTRIES, vars = {} } = {}) {
    const { Miniflare, convertV4MiniflareOptions } = await import("miniflare");
    const service = new Service();
    service.dir = mkdtempSync(join(tmpdir(), "thenwhat-ingest-store-"));
    cpSync(template, service.dir, { recursive: true });
    service.mf = new Miniflare(convertV4MiniflareOptions({
      resourcePersistencePath: join(service.dir, "v3"),
      cf: false,
      // The Worker's own files, the entry first: nothing is bundled, so what runs is src/.
      modules: ["index", "auth", "check", "hash", "limits", "sql.generated", "store"]
        .map((name) => ({ type: "ESModule", path: join(root, `src/${name}.mjs`) })),
      compatibilityDate: "2026-10-01",
      d1Databases: { STORE: "STORE" },
      r2Buckets: { PAYLOADS: "payloads" },
      queueProducers: { WORK: "work" },
      bindings: { INGEST_TOKENS: JSON.stringify(entries), ...vars },
    }));
    service.db = await service.mf.getD1Database("STORE");
    service.put = new Set();
    service.runs = 0;
    return service;
  }

  async close() {
    await this.mf.dispose();
    rmSync(this.dir, { recursive: true, force: true });
  }

  // One request. `as` names a writer's token; a body that is not bytes is sent as JSON.
  async ask(method, path, { as = "operator", token = TOKENS[as], body, type, headers = {} } = {}) {
    const raw = body === undefined ? undefined : body instanceof Uint8Array || typeof body === "string" ? body : JSON.stringify(body);
    const response = await this.mf.dispatchFetch(`http://ingest.test${path}`, {
      method,
      headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), ...(raw === undefined ? {} : { "content-type": type || "application/json" }), ...headers },
      body: raw,
    });
    const text = await response.text();
    let value = null;
    try { value = JSON.parse(text); } catch {}
    return { status: response.status, body: value, text };
  }

  // What a request left, read through the binding.
  async all(sql, ...args) {
    const statement = this.db.prepare(sql);
    return (args.length ? statement.bind(...args) : statement).raw();
  }

  async one(sql, ...args) {
    const rows = await this.all(sql, ...args);
    return rows.length ? rows[0][0] : null;
  }

  // Register a run and hand over its records, [[kind, key, body], ...], in chunks. The
  // last answer that was not a success is returned, or null.
  async hand(id, records, { as = "device-mini", writer = as.split("-")[0], stated, steps = { link_triage: 3 }, chunk = 2000, request_class } = {}) {
    for (const [kind, , body] of records) {
      if (kind === "payload" && body.r2_key && PAYLOADS.has(body.sha256) && !this.put.has(body.sha256)) {
        const done = await this.ask("PUT", `/payloads/${body.sha256}`, { as, body: PAYLOADS.get(body.sha256), type: "application/octet-stream" });
        if (done.status > 201) return done;
        this.put.add(body.sha256);
      }
    }
    const counts = {};
    for (const [kind] of records) counts[kind] = (counts[kind] || 0) + 1;
    const chunks = [];
    for (let i = 0; i < records.length; i += chunk) {
      chunks.push(JSON.stringify(records.slice(i, i + chunk).map(([kind, key, body]) => ({ kind, key, body }))));
    }
    const registered = await this.ask("POST", "/runs", { as, body: {
      id, writer, commit: "abc1234", steps, counts: stated || counts, checksum: runChecksum(chunks.map(sha)),
      ...(writer === "lookup" ? { request_class: request_class || "extension" } : {}) } });
    if (registered.status > 201) return registered;
    for (const text of chunks) {
      const staged = await this.ask("POST", `/runs/${id}/records`, { as, body: text, headers: { "x-content-sha256": sha(text) } });
      if (staged.status !== 200) return staged;
    }
    return null;
  }

  merge(id, as = "device-mini") { return this.ask("POST", `/runs/${id}/merge`, { as }); }
  preview(id, as = "device-mini") { return this.ask("POST", `/runs/${id}/preview`, { as }); }
  drop(id, as = "device-mini") { return this.ask("DELETE", `/runs/${id}`, { as }); }
}

// Payload bodies by checksum, so a test can put the ones kept in R2.
export const PAYLOADS = new Map();
