// The site on this machine as a deployment serves it: built from a bundle, with the Worker that
// makes every pair's page, record, embed, oEmbed and card address and every listing on request
// (worker/with-pairs.mjs), from that bundle loaded into D1's local engine. Astro's own dev server
// runs no Worker, so it has no pair pages since none is built (openspec pairs-site task 4.6).
//
//   make pairs-dev                                    the small bundle, http://localhost:8788
//   PAIRS_BUNDLE=/path/to/bundle make pairs-dev       another bundle
//
// Nothing is sent to Cloudflare: the database is a folder under .wrangler/pairs-dev.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { findDeployDatabase } from "./pairs-deploy.mjs";
import { loadPairsBundle, pairsConfig } from "./pairs-preview.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const bundle = path.resolve(SITE_DIR, process.env.PAIRS_BUNDLE || "tests/bundle");
const state = path.join(SITE_DIR, ".wrangler", "pairs-dev");
const port = process.env.PORT || "8788";

const built = spawnSync("pnpm", ["run", "build"], {
  cwd: SITE_DIR,
  stdio: "inherit",
  env: { ...process.env, PAIRS_BUNDLE: bundle, ASTRO_TELEMETRY_DISABLED: "1" },
});
if (built.status !== 0) process.exit(built.status ?? 1);

fs.mkdirSync(state, { recursive: true });
const database = findDeployDatabase("thenwhat-pairs-dev-preview", { localState: path.join(state, "d1") });
const config = pairsConfig({ base: "wrangler.preview.jsonc", database, scratch: state });
loadPairsBundle({ config, database, bundle, local: true, persistTo: database.persistTo });
console.log(`Bundle ${path.relative(SITE_DIR, bundle)} loaded into D1's local engine. Serving http://localhost:${port}`);

const served = spawnSync(
  process.execPath,
  [path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js"), "dev", "--config", config, "--local", "--persist-to", database.persistTo, "--port", port],
  { cwd: SITE_DIR, stdio: "inherit" },
);
process.exit(served.status ?? 0);
