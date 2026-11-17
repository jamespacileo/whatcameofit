// Deploys the ingest service, and is the only way it is deployed.
//
//   node scripts/deploy.mjs --env preview --tokens-file <path>
//   node scripts/deploy.mjs --env production --confirm thenwhat-store-ingest --tokens-file <path>
//   make store-deploy ENV=preview TOKENS=<path>
//   make store-deploy ENV=production CONFIRM=thenwhat-store-ingest TOKENS=<path>
//        --dry-run          print the plan and the configuration that would be deployed, ids left out
//        --skip-secret      deploy without setting the secret (it is already set)
//        --smoke <address>  only ask a deployed service the questions below
//
// In this order, stopping at the first failure with the stage named:
//   1 config        the configuration that is deployed, written from the committed
//                   wrangler.jsonc: this environment's Worker, database (its id looked up
//                   by name), bucket; a workers.dev address; no preview URLs; logs still
//                   off; no Queue, since nothing consumes one yet. A git-ignored file,
//                   removed at the end.
//   2 jurisdiction  the database reads back `eu`, the bucket is found in `eu`
//   3 migrations    none is left to apply: the service is never deployed onto a schema
//                   older than its code
//   4 deploy        `wrangler deploy`
//   5 secret        INGEST_TOKENS from the file given, by `wrangler secret put` reading
//                   the file on its standard input. The value is never an argument, never
//                   printed and never logged: only its size and how many tokens it lists.
//   6 smoke         with no token every route answers 401 (and the progress page only its
//                   empty shell); with a wrong token 401; with the operator's token, read
//                   from the environment variable STORE_TOKEN_OPERATOR and never printed,
//                   GET /progress answers 200.
// Production needs `--confirm <the Worker's name>`. What the steps print goes to a log
// outside the repository; the terminal shows it with ids masked.
import { spawn } from "node:child_process";
import { createReadStream, createWriteStream, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const has = (flag) => argv.includes(flag);
const stop = (message) => { console.error(message); process.exit(2); };
const NAMES = {
  preview: { worker: "thenwhat-store-ingest-preview", database: "thenwhat-store-preview", bucket: "thenwhat-payloads-preview", limits: ["1001", "1002"] },
  production: { worker: "thenwhat-store-ingest", database: "thenwhat-store", bucket: "thenwhat-payloads", limits: ["2001", "2002"] },
};

// ---- what a deployed service must answer -----------------------------------------------
const ROUTES = [["GET", "/"], ["POST", "/runs"], ["GET", "/runs/x"], ["DELETE", "/runs/x"], ["POST", "/runs/x/records"], ["POST", "/runs/x/merge"], ["POST", "/runs/x/preview"],
  ["PUT", `/payloads/${"0".repeat(64)}`], ["GET", "/inbox"], ["POST", "/inbox/folded"], ["POST", "/inbox/clear"], ["GET", "/progress"],
  ["POST", "/work/lease"], ["POST", "/slices/take"], ["POST", "/progress/page"], ["GET", "/sql"]];
export async function smoke(address, say = console.log) {
  const at = address.replace(/\/$/, "");
  // Asked too often (the service's own limit for callers without a token): wait a minute, once.
  const ask = async (method, path, token) => { const answer = await once(method, path, token); if (answer.status !== 429) return answer; await new Promise((resolve) => setTimeout(resolve, 61_000)); return once(method, path, token); };
  const once = (method, path, token) => fetch(`${at}${path}`, { method, redirect: "manual", headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), ...(method === "GET" || method === "DELETE" ? {} : { "content-type": "application/json", "content-length": "2" }) }, body: method === "GET" || method === "DELETE" ? undefined : "{}" });
  const wrong = [];
  // A secret takes a moment to reach every location: the first question is asked again for a while.
  for (let tries = 0; ; tries += 1) {
    const first = await ask("GET", "/progress", null).catch(() => null);
    if (first?.status === 401) break;
    if (tries >= 15) { wrong.push(`GET /progress with no token answered ${first?.status ?? "nothing"}, not 401`); break; }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  for (const [method, path] of ROUTES) {
    for (const [who, token] of [["no token", null], ["a wrong token", "wrong-token-wrong-token-wrong-token-0000"]]) {
      const answer = await ask(method, path, token);
      const text = await answer.text();
      if (answer.status !== 401 || text !== JSON.stringify({ error: "unauthorized" })) wrong.push(`${method} ${path} with ${who} answered ${answer.status}`);
    }
  }
  say(`${ROUTES.length} routes: 401 with no token and with a wrong one${wrong.length ? `, but for ${wrong.length}` : ""}`);
  const shell = await ask("GET", "/progress/page", null);
  const page = await shell.text();
  if (shell.status !== 200 || /\d{4,}/.test(page.replace(/<style>[\s\S]*?<\/style>|<script>[\s\S]*?<\/script>/g, ""))) wrong.push("the progress page's shell is not the empty shell");
  else say("the progress page answers its empty shell without a token, and no count");
  const operator = process.env.STORE_TOKEN_OPERATOR;
  if (!operator) wrong.push("STORE_TOKEN_OPERATOR is not set, so the operator's token was not tried");
  else {
    let status = null;
    // Only a 401 is asked again: the secret may not have reached every location yet.
    for (let tries = 0; tries < 15; tries += 1) { status = (await ask("GET", "/progress", operator)).status; if (status !== 401) break; await new Promise((resolve) => setTimeout(resolve, 2000)); }
    if (status === 200) say("the operator's token: GET /progress answers 200"); else wrong.push(`GET /progress with the operator's token answered ${status}, not 200`);
  }
  for (const line of wrong) say(`WRONG: ${line}`);
  return wrong.length === 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  // Only this service is asked, at an address of its own Worker's name: the operator's
  // token is sent there, so it is sent nowhere else.
  if (has("--smoke")) {
    const address = value("--smoke") || "";
    const names = Object.values(NAMES).map((one) => one.worker).sort((a, b) => b.length - a.length);
    if (!new RegExp(`^https://(${names.join("|")})\\.[a-z0-9-]+\\.workers\\.dev/?$`).test(address)) stop(`--smoke takes the address a deploy printed: https://<${names.join(" or ")}>.<subdomain>.workers.dev`);
    process.exit((await smoke(address)) ? 0 : 1);
  }
  const env = value("--env");
  if (!NAMES[env]) stop("usage: deploy.mjs --env preview|production [--confirm <worker name>] --tokens-file <path> [--skip-secret] [--dry-run] | --smoke <address>");
  const { worker, database, bucket, limits } = NAMES[env];
  if (env === "production" && value("--confirm") !== worker) stop(`production is deployed only with --confirm ${worker} (CONFIRM=${worker} for make)`);
  const tokens = value("--tokens-file");
  if (!has("--skip-secret") && !has("--dry-run") && (!tokens || !existsSync(tokens))) stop("--tokens-file names the file that holds the value of INGEST_TOKENS (or pass --skip-secret when it is already set)");

  const wrangler = here("../node_modules/.bin/wrangler");
  const config = here(`../wrangler.deploy-${env}.jsonc`);
  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
  const folder = join(homedir(), "Library", "Application Support", "thenwhat", "store", "deploys");
  let log = null;
  const mask = (text) => text.replace(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi, "<id>").replace(/\b[0-9a-f]{32}\b/gi, "<id>");
  const say = (text) => { log?.write(`${text}\n`); console.log(mask(text)); };
  // A step: what it prints goes to the log as it arrives, and to the terminal masked.
  // `input` is a file sent to its standard input; nothing of it is written anywhere.
  function run(args, { quiet = false, input = null } = {}) {
    return new Promise((done) => {
      log?.write(`$ wrangler ${args.join(" ")}\n`);
      const child = spawn(wrangler, args, { cwd: here(".."), env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: [input ? "pipe" : "ignore", "pipe", "pipe"] });
      if (input) createReadStream(input).pipe(child.stdin);
      let text = "";
      const take = (chunk, to) => { const piece = chunk.toString(); text += piece; log?.write(piece); if (!quiet) to.write(mask(piece)); };
      child.stdout.on("data", (chunk) => take(chunk, process.stdout));
      child.stderr.on("data", (chunk) => take(chunk, process.stderr));
      child.on("error", (error) => done({ ok: false, text: `${text}\n${error.message}` }));
      child.on("close", (code) => done({ ok: code === 0, text }));
    });
  }
  class Failed extends Error {}
  const must = async (args, why, options) => { const done = await run(args, options); if (!done.ok) throw new Failed(why); return done.text; };
  const json = (text) => JSON.parse(text.slice(text.search(/[[{]/)));

  // The configuration that is deployed, from the committed one. `id` is null for a dry run.
  function deployed(id) {
    let text = readFileSync(here("../wrangler.jsonc"), "utf8");
    const swap = (from, to) => { if (!text.includes(from)) throw new Failed(`wrangler.jsonc no longer has ${from}: the deploy script must be brought up to date with it`); text = text.replace(from, to); };
    swap('"name": "thenwhat-store-ingest"', `"name": "${worker}"`);
    swap('"workers_dev": false', '"workers_dev": true');
    if (!/"preview_urls": false/.test(text) || !/"observability": \{ "enabled": false \}/.test(text)) throw new Failed("wrangler.jsonc must keep preview_urls false and observability off");
    swap('"database_name": "thenwhat-store-preview"', `"database_name": "${database}"${id ? `, "database_id": "${id}"` : ""}`);
    swap('"bucket_name": "thenwhat-payloads-preview"', `"bucket_name": "${bucket}", "jurisdiction": "eu"`);
    swap('"namespace_id": "1001"', `"namespace_id": "${limits[0]}"`);
    swap('"namespace_id": "1002"', `"namespace_id": "${limits[1]}"`);
    // No Queue: nothing consumes one yet, and the service wakes a consumer only when bound to one.
    const queue = /\n  "queues": \{\n[\s\S]*?\n  \},/;
    if (!queue.test(text)) throw new Failed("wrangler.jsonc no longer has the queues block where it was");
    return text.replace(queue, "");
  }

  if (has("--dry-run")) {
    console.log(`deploy of ${env}: Worker ${worker}, database ${database}, bucket ${bucket}, on a workers.dev address`);
    console.log("stages: config, jurisdiction, migrations, deploy, secret, smoke");
    console.log(`secret: ${has("--skip-secret") ? "left as it is" : `INGEST_TOKENS from ${tokens || "(--tokens-file not given)"}, by wrangler secret put on standard input`}`);
    console.log("the configuration that would be deployed, without the database's id:\n");
    try { console.log(deployed(null).split("\n").filter((line) => !line.trimStart().startsWith("//")).join("\n")); } catch (error) { stop(error.message); }
    console.log("nothing was run");
    process.exit(0);
  }

  mkdirSync(folder, { recursive: true });
  log = createWriteStream(join(folder, `${env}-${stamp}.log`));
  // The configuration holds the database's id: it goes even when the run is stopped by hand.
  for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => { rmSync(config, { force: true }); console.error(`\nstopped by ${signal}; the deploy configuration was removed`); process.exit(130); });
  say(`deploy of ${env}: Worker ${worker}, database ${database}, bucket ${bucket}`);
  let address = null;
  const stages = [
    ["config", async () => {
      const found = json(await must(["d1", "list", "--json"], "the account's databases could not be listed", { quiet: true })).find((one) => one.name === database);
      if (!found) throw new Failed(`the account has no database named ${database}`);
      writeFileSync(config, deployed(found.uuid));
      say(`wrote ${config.split("/").at(-1)} (the database's id is in that file only, and the file is removed at the end)`);
    }],
    ["jurisdiction", async () => {
      const info = json(await must(["d1", "info", database, "--json"], `the database ${database} could not be read`, { quiet: true }));
      if (info.jurisdiction !== "eu") throw new Failed(`the database ${database} reads back jurisdiction ${JSON.stringify(info.jurisdiction ?? null)}, not "eu"`);
      await must(["r2", "bucket", "info", bucket, "--jurisdiction", "eu"], `the bucket ${bucket} is not found in the eu jurisdiction`, { quiet: true });
      say(`${database}: eu; ${bucket}: found in eu`);
    }],
    ["migrations", async () => {
      const text = await must(["d1", "migrations", "list", "STORE", "--remote", "--config", config], "the migrations could not be listed", { quiet: true });
      const left = [...new Set(text.match(/\b\d{4}_[a-z_0-9]+\.sql\b/g) || [])];
      if (left.length) throw new Failed(`${left.length} migration(s) are not applied to ${database} (${left.join(", ")}): apply them first (the cut-over does), then deploy`);
      say("no migration is left to apply");
    }],
    ["deploy", async () => {
      const text = await must(["deploy", "--config", config], "the deploy failed");
      address = /https:\/\/[a-z0-9.-]+\.workers\.dev/.exec(text)?.[0] || null;
      if (!address) throw new Failed("the deploy did not say the service's address");
    }],
    ["secret", async () => {
      if (has("--skip-secret")) return say("the secret is left as it is (--skip-secret)");
      // Held to its shape before it is sent; nothing of it is shown but two numbers.
      let entries;
      try { entries = JSON.parse(readFileSync(tokens, "utf8")); } catch { throw new Failed("the tokens file is not JSON"); }
      if (!Array.isArray(entries) || !entries.length || !entries.every((entry) => entry && /^[0-9a-f]{64}$/.test(entry.sha256 || "") && typeof entry.role === "string")) throw new Failed("the tokens file must be a list of {name, role, device?, sha256}: checksums of tokens, never tokens");
      if (entries.some((entry) => Object.keys(entry).some((key) => !["name", "role", "device", "sha256"].includes(key)))) throw new Failed("an entry of the tokens file has a field that is not name, role, device or sha256: it may hold a token itself");
      const bytes = readFileSync(tokens).length;
      if (bytes > 5000) throw new Failed(`the tokens file is ${bytes} bytes and a secret holds 5 KB`);
      await must(["secret", "put", "INGEST_TOKENS", "--config", config], "the secret could not be set", { input: tokens });
      say(`INGEST_TOKENS set: ${entries.length} token(s), ${bytes} bytes`);
    }],
    ["smoke", async () => { if (!(await smoke(address, say))) throw new Failed("the deployed service does not answer as it must: see above"); }],
  ];
  let failed = null;
  for (const [n, [name, stage]] of stages.entries()) {
    say(`\n== ${n + 1} ${name}`);
    try { await stage(); } catch (error) { failed = name; say(`\nFAILED at ${name}: ${error instanceof Failed ? error.message : error.stack}`); break; }
  }
  rmSync(config, { force: true });
  say(failed ? `\nthe deploy of ${env} FAILED at ${failed}${address ? `; the service is at ${address} and may be half set up` : ""}` : `\n${worker} is deployed and answers as it must: ${address}\nthe progress page: ${address}/progress/page`);
  await new Promise((done) => log.end(done));
  process.exit(failed ? 1 : 0);
}
