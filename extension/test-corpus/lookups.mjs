// Send each untracked address to the lookup service, as the site's address box does, and
// keep every answer outside the worktree. Rows already answered are skipped, so a run can
// be stopped and started again. Posts the service cannot read by address (X, Reddit, ...)
// need the browser pass in README.md.
//
//   node lookups.mjs                        address pass
//   node lookups.mjs --browser <file.json>  send text read in a browser: {id: {text, links, platform?, pageUrl}}
//
// LOOKUP_API overrides the service (default: make lookup-dev on this machine). Each search
// is a paid model call, capped by LLM_MONTHLY_BUDGET_USD in the service's settings.
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { readRows } from "./rows.mjs";

const here = fileURLToPath(new URL(".", import.meta.url));
const API = process.env.LOOKUP_API ?? "http://localhost:8787/api/lookup";
const cacheScript = `${here}corpus_cache.py`;
const cache = JSON.parse(execFileSync("python3", ["-I", cacheScript, "read", here], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }));
const results = cache.results;
const match = JSON.parse(readFileSync(`${here}.work/match.json`, "utf8"));
const browserFile = process.argv[2] === "--browser" ? process.argv[3] : null;
const browserInputs = browserFile ? JSON.parse(readFileSync(browserFile, "utf8")) : null;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function ask(body) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const started = Date.now();
    const response = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const answer = await response.json().catch(() => ({}));
    if (response.status === 429) { await sleep(20000); continue; }
    return { http: response.status, ms: Date.now() - started, body: answer };
  }
  return { http: 429, ms: 0, body: { error: "busy" } };
}

// Like the popup, open a t.co link to learn where it leads, and send that address.
async function unshorten(links) {
  const out = [];
  for (const link of links) {
    if (!/^https:\/\/t\.co\//.test(link)) { out.push(link); continue; }
    const response = await fetch(link, { redirect: "manual" }).catch(() => null);
    out.push(response?.headers.get("location") ?? link);
  }
  return out;
}

let asked = 0;
for (const row of readRows(`${here}urls.csv`)) {
  const m = match[row.url] ?? {};
  const mode = browserInputs ? "browser" : "address";
  if (results[row.url]?.[mode]) continue;
  let result;
  if (browserInputs) {
    const input = browserInputs[row.id];
    if (!input) continue;
    const links = await unshorten(input.links ?? []);
    result = { mode: "browser text", sent_links: links, ...(await ask({ ...input, links })) };
  } else {
    if (m.tracked_slug) continue; // the popup shows the reviewed claim, no search
    if (m.address_kind === "post" && !m.server_can_read_post) continue;
    result = { mode: "address", ...(await ask({ url: row.url })) };
  }
  execFileSync("python3", ["-I", cacheScript, "put-result", row.url, mode], { input: JSON.stringify(result) });
  (results[row.url] ??= {})[mode] = result;
  asked += 1;
  const b = result.body;
  console.log(row.id, result.http, `${result.ms}ms`,
    b.error ?? (b.about_a_treatment === false ? "no treatment" : `${b.treatment ?? ""} / ${b.condition ?? ""} / ${(b.candidates ?? []).length} records`));
  await sleep(13000); // the service allows 5 searches a minute per reader
}
const total = Object.values(results).reduce((count, modes) => count + Object.keys(modes).length, 0);
console.log(`asked ${asked}; ${total} answers on record`);
