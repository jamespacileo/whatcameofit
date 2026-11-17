// How the scripts here reach the PAYLOADS bucket with Wrangler and its own login: the
// local engine with `--persist-to <dir>`, or with `--remote` the preview bucket this
// service is bound to, in the EU jurisdiction. Production is written to only when its
// bucket is named: `--remote --production <bucket>`. No access key is made or read.
import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { createReadStream, existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const run = promisify(execFile);

// From Wrangler 4.161.0's source (MAX_UPLOAD_SIZE_BYTES, read 2026-11-17): `r2 object put`
// refuses a file over 300 MiB.
export const WRANGLER_PUT_LIMIT_BYTES = 300 * 1024 * 1024;

export async function sha256(path) {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(path)) hash.update(chunk);
  return hash.digest("hex");
}

export function bucket(argv) {
  const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
  const remote = argv.includes("--remote"), persist = value("--persist-to"), production = value("--production");
  if (!remote && !persist) throw new Error("say where: --remote, or --persist-to <dir> for the local engine");
  const bound = /"bucket_name":\s*"([^"]+)"/.exec(readFileSync(here("../wrangler.jsonc"), "utf8"))?.[1];
  if (production && (!remote || production.endsWith("-preview") || !/^[a-z0-9-]{3,63}$/.test(production))) throw new Error("--production names the production bucket, and only with --remote");
  if (!production && !bound?.endsWith("-preview")) throw new Error("wrangler.jsonc does not bind a preview bucket");
  const name = production || bound;
  const config = remote && !production ? here("../wrangler.preview.jsonc") : here("../wrangler.jsonc");
  if (!existsSync(config)) throw new Error("no wrangler.preview.jsonc: run `node scripts/preview-config.mjs` first");
  const where = remote ? ["--remote", "--jurisdiction", "eu"] : ["--local", "--persist-to", persist];
  const wrangler = (...args) => run(here("../node_modules/.bin/wrangler"), ["r2", "object", ...args, ...where, "--config", config],
    { cwd: here(".."), env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, maxBuffer: 16 * 1024 * 1024 });
  // Wrangler's last words on a failure, without the paths it was given.
  const said = (error) => String(error.stderr || error.stdout || error.message).split("\n").filter((line) => /error|not found|fail|denied|limit|exist/i.test(line)).slice(-2).join(" ").slice(0, 300) || "failed";
  async function put(key, path, attempts = 4) {
    for (let attempt = 1; ; attempt += 1) {
      try { await wrangler("put", `${name}/${key}`, "--file", path, "--content-type", "application/octet-stream", "--force"); return; } catch (error) {
        if (attempt >= attempts) throw new Error(said(error));
        await new Promise((resolve) => setTimeout(resolve, 1000 * 2 ** attempt));
      }
    }
  }
  // False when the bucket has no such object.
  async function get(key, path) {
    try { await wrangler("get", `${name}/${key}`, "--file", path); return true; } catch { return false; }
  }
  // Removes one object; removing one that is not there is not a failure. A refusal for
  // asking too fast (429) is waited out, longer each time.
  async function remove(key, attempts = 6) {
    for (let attempt = 1; ; attempt += 1) {
      try { await wrangler("delete", `${name}/${key}`); return; } catch (error) {
        const why = said(error);
        if (/not found|does not exist|no such/i.test(why)) return;
        if (attempt >= attempts) throw new Error(why);
        await new Promise((resolve) => setTimeout(resolve, (/429|too many|rate/i.test(String(error.stderr || error.message)) ? 5000 : 1000) * 2 ** (attempt - 1)));
      }
    }
  }
  return { name, remote, remove, label: remote ? `${name} (remote, jurisdiction eu)` : `${name} (local engine)`, put, get };
}
