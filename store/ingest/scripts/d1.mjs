// How the scripts here reach the store with Wrangler: the local engine unless `--remote`
// is given, and then only through wrangler.preview.jsonc (scripts/preview-config.mjs),
// which holds the database's id and is never committed. Nothing here prints an id.
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const run = promisify(execFile);

// The flags after the script's own arguments: --remote, --persist-to <folder>, --config <file>.
export function target(argv) {
  const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
  const remote = argv.includes("--remote");
  const config = value("--config") || (remote ? here("../wrangler.preview.jsonc") : here("../wrangler.jsonc"));
  if (remote && !existsSync(config)) throw new Error("no wrangler.preview.jsonc: run `node scripts/preview-config.mjs` first");
  const where = remote ? ["--remote"] : ["--local", ...(value("--persist-to") ? ["--persist-to", value("--persist-to")] : [])];
  return { remote, flags: [...where, "--config", config, "--yes", "--json"] };
}

// One `wrangler d1 execute`, its JSON answer parsed. A failure throws with Wrangler's words.
export async function execute(to, ...args) {
  try {
    const { stdout } = await run(here("../node_modules/.bin/wrangler"), ["d1", "execute", "STORE", ...args, ...to.flags],
      { cwd: here(".."), env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, maxBuffer: 256 * 1024 * 1024 });
    return JSON.parse(stdout.slice(stdout.search(/[[{]/)));
  } catch (error) {
    throw new Error(String(error.stdout || "").slice(-2000) + String(error.stderr || error.message).slice(-2000));
  }
}

// Every number of this name anywhere in an answer, added up: Wrangler's answer for a file
// differs between the local engine and D1 itself.
export function sum(answer, name) {
  let total = 0, seen = false;
  const walk = (value) => {
    if (Array.isArray(value)) value.forEach(walk);
    else if (value && typeof value === "object") {
      for (const [key, item] of Object.entries(value)) {
        if (key === name && typeof item === "number") { total += item; seen = true; } else walk(item);
      }
    }
  };
  walk(answer);
  return seen ? total : null;
}
