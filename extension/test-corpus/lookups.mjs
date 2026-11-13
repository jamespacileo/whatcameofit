// Send each untracked address to the lookup service, as the site's address box does, and
// keep every answer in .work/results.json. Rows already answered are skipped, so a run can
// be stopped and started again. Posts the service cannot read by address (X, Reddit, ...)
// need the browser pass in README.md.
//
//   node lookups.mjs                        address pass
//   node lookups.mjs --browser <file.json>  send text read in a browser: {id: {text, links, platform?, pageUrl}}
//
// LOOKUP_API overrides the service (default: make lookup-dev on this machine). Each search
// is a paid model call, capped by LLM_MONTHLY_BUDGET_USD in the service's settings.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { readRows } from "./rows.mjs";

const here = new URL(".", import.meta.url).pathname;
const API = process.env.LOOKUP_API ?? "http://localhost:8787/api/lookup";
const resultsFile = `${here}.work/results.json`;
const results = existsSync(resultsFile) ? JSON.parse(readFileSync(resultsFile, "utf8")) : {};
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
  const key = browserInputs ? `${row.id}:browser` : row.id;
  if (results[key]) continue;
  if (browserInputs) {
    const input = browserInputs[row.id];
    if (!input) continue;
    const links = await unshorten(input.links ?? []);
    results[key] = { mode: "browser text", sent_links: links, ...(await ask({ ...input, links })) };
  } else {
    if (m.tracked_slug) continue; // the popup shows the reviewed claim, no search
    if (m.address_kind === "post" && !m.server_can_read_post) continue;
    results[key] = { mode: "address", ...(await ask({ url: row.url })) };
  }
  asked += 1;
  const b = results[key].body;
  console.log(row.id, results[key].http, `${results[key].ms}ms`,
    b.error ?? (b.about_a_treatment === false ? "no treatment" : `${b.treatment ?? ""} / ${b.condition ?? ""} / ${(b.candidates ?? []).length} records`));
  writeFileSync(resultsFile, JSON.stringify(results, null, 1));
  await sleep(13000); // the service allows 5 searches a minute per reader
}
console.log(`asked ${asked}; ${Object.keys(results).length} answers on record`);
