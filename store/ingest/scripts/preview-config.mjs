// Writes wrangler.preview.jsonc, the configuration a remote command is run with: the
// committed wrangler.jsonc plus the preview database's id, which is looked up by name
// from the signed-in account and never printed or committed (the file is git-ignored).
//
//   node scripts/preview-config.mjs
//   wrangler d1 migrations apply STORE --remote --config wrangler.preview.jsonc
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const NAME = "thenwhat-store-preview";
const listed = JSON.parse(execFileSync(here("../node_modules/.bin/wrangler"), ["d1", "list", "--json"],
  { cwd: here(".."), env: { ...process.env, WRANGLER_SEND_METRICS: "false" }, stdio: ["ignore", "pipe", "inherit"] }));
const found = listed.find((database) => database.name === NAME);
if (!found) { console.error(`the account has no database named ${NAME}`); process.exit(1); }
const text = readFileSync(here("../wrangler.jsonc"), "utf8");
const at = `"database_name": "${NAME}"`;
if (!text.includes(at)) { console.error("wrangler.jsonc does not name the preview database"); process.exit(1); }
writeFileSync(here("../wrangler.preview.jsonc"), text.replace(at, `${at}, "database_id": "${found.uuid}"`));
console.log(`wrote wrangler.preview.jsonc for ${NAME} (its id is in that file only)`);
