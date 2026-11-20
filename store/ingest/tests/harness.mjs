// The store's D1 database on this machine: Miniflare runs D1's own local engine, on disk
// here. No account, no network, nothing deployed.
//
// The store is made the way a real one is: `wrangler d1 migrations apply --local` applies
// migrations/ once into a template folder, and every test's store is a copy of it. Tests
// read and write it through the D1 binding. The ingest service that once stood in front
// of it was removed with claims on 2026-11-20, so no Worker of the store's own runs here:
// Miniflare is given an empty one, only to hold the binding.
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

let template = null;
let unavailable = null;

// Why the local engine cannot be used here, or null when it can. Found once.
export async function engineUnavailable() {
  if (template || unavailable) return unavailable;
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-store-"));
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
  static async open() {
    const { Miniflare, convertV4MiniflareOptions } = await import("miniflare");
    const service = new Service();
    service.dir = mkdtempSync(join(tmpdir(), "thenwhat-store-copy-"));
    cpSync(template, service.dir, { recursive: true });
    const worker = join(service.dir, "worker.mjs");
    writeFileSync(worker, "export default { fetch() { return new Response(null, { status: 404 }); } };\n");
    service.mf = new Miniflare(convertV4MiniflareOptions({
      resourcePersistencePath: join(service.dir, "v3"),
      cf: false,
      modulesRoot: service.dir,
      modules: [{ type: "ESModule", path: worker }],
      compatibilityDate: "2026-10-01",
      d1Databases: { STORE: "STORE" },
    }));
    service.db = await service.mf.getD1Database("STORE");
    return service;
  }

  async close() {
    await this.mf.dispose();
    rmSync(this.dir, { recursive: true, force: true });
  }
}
