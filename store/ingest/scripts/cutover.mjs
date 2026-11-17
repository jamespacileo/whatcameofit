// The cut-over of the store, as one command and one order, for the local engine (the
// rehearsal), the preview and production.
//
//   node scripts/cutover.mjs --env local|preview|production --store-dir <a build's folder> [--confirm <database name>]
//        [--replace] [--dry-run] [--skip-export] [--rows-a-file N]
//   make store-rehearsal STORE_DIR=...                       the same with --env local
//   make store-cutover ENV=preview STORE_DIR=...
//   make store-cutover ENV=production STORE_DIR=... CONFIRM=thenwhat-store
//
// A build's folder, as `thenwhat store build` leaves it: store.hot.sqlite,
// store.bulk.sqlite, payloads/hot and payloads/bulk, and checks.json (made here when it is
// not there).
//
// The stages, in this order; the first that fails stops the run and is named:
//    0 privacy       no person is named in either file or either payload folder
//    1 jurisdiction  the database and the bucket are read back and must be `eu`
//    2 config        the remote configuration, with the database's id looked up by name
//    3 bookmark      D1's Time Travel bookmark, written outside the repository, before
//                    anything is changed: a migration that fails has a point to go back to
//    4 empty         the store must hold no row; with --replace a preview store is emptied
//                    (or replaced, over 200,000 rows); production is never emptied here.
//                    Before the migrations: a loaded store never meets one that makes a
//                    table again
//    5 migrations    refused when the database applied a migration under a name the files
//                    no longer have in that place, or when one that makes a table again
//                    is pending and the store holds rows
//    6 dump          the hot file as SQL, and that SQL replayed strictly on this machine
//    7 import
//    8 checksum      every hot table in D1 against the build's checks
//    9 payloads      the payload objects of both tiers
//   10 bulk          the bulk file, in parts, with its manifest
//   11 verify        the bulk manifest read back and held to the file
//   12 export        local only: the export from the hot file against the working database
//
// Production needs `--env production` and `--confirm <the database's name>`, and every
// script it calls is given `--production` explicitly. Everything the steps print goes
// unfiltered to a log file in the build's folder (cutover/<env>-<time>.log), as it
// arrives; the terminal shows the same with ids masked. A result is written as JSON
// beside it: each stage's seconds, the rows D1 says were written, the build's id.
// `--dry-run` prints the plan and runs nothing.
import { spawn } from "node:child_process";
import { createWriteStream, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import { sha256 } from "./r2.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const has = (flag) => argv.includes(flag);
const env = value("--env");
const dir = value("--store-dir") && resolve(value("--store-dir"));
const NAMES = {
  local: { database: "thenwhat-store-preview", bucket: "thenwhat-payloads-preview" },
  preview: { database: "thenwhat-store-preview", bucket: "thenwhat-payloads-preview" },
  production: { database: "thenwhat-store", bucket: "thenwhat-payloads" },
};
const stop = (message) => { console.error(message); process.exit(2); };
if (!NAMES[env] || !dir) stop("usage: cutover.mjs --env local|preview|production --store-dir <a build's folder> [--confirm <database name>] [--replace] [--dry-run] [--skip-export]");
const { database, bucket } = NAMES[env];
const remote = env !== "local", production = env === "production";
if (production && value("--confirm") !== database) stop(`production is cut over only with --confirm ${database} (CONFIRM=${database} for make)`);
if (!production && value("--confirm") && value("--confirm") !== database) stop(`--confirm names ${value("--confirm")}, but ${env} is ${database}`);

const hot = value("--hot") || join(dir, "store.hot.sqlite"), bulk = value("--bulk") || join(dir, "store.bulk.sqlite");
const payloads = value("--payloads") ? [value("--payloads")] : ["hot", "bulk"].map((tier) => join(dir, "payloads", tier)).filter((path) => existsSync(path));
const checks = join(dir, "checks.json");
const out = join(dir, "cutover");
const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
// On this machine the engine's state is made anew each time; `--work <dir>` keeps it, to
// rehearse against a store that is already loaded.
const work = remote ? out : value("--work") ? resolve(value("--work")) : join(tmpdir(), `thenwhat-rehearsal-${stamp}`);
const sql = join(work, `sql-${env}`), state = join(work, "state");
const config = remote ? here(`../wrangler.${env}.jsonc`) : here("../wrangler.jsonc");
const wrangler = here("../node_modules/.bin/wrangler");
const pipeline = here("../../../pipeline");
const node = (script, ...args) => [process.execPath, [here(`./${script}.mjs`), ...args]];
const thenwhat = (...args) => ["uv", ["run", "--directory", pipeline, "thenwhat", ...args]];
// Where each script is told to act, and for production that it is production.
const d1 = remote ? ["--remote", "--config", config, ...(production ? ["--production", database] : [])] : ["--persist-to", state];
const r2 = remote ? ["--remote", ...(production ? ["--production", bucket] : [])] : ["--persist-to", state];
const d1Wrangler = remote ? ["--remote", "--config", config] : ["--local", "--persist-to", state, "--config", config];
const r2Wrangler = remote ? ["--remote", "--jurisdiction", "eu"] : ["--local", "--persist-to", state];
const replaceCommands = [
  `npx wrangler d1 delete ${database}`,
  `npx wrangler d1 create ${database} --jurisdiction eu`,
  `make store-cutover ENV=${env} STORE_DIR=${dir}${production ? ` CONFIRM=${database}` : ""}`,
];

// ---- running a step: everything to the log as it arrives, the terminal with ids masked ----
let log = null;
const mask = (text) => text.replace(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi, "<id>").replace(/\b[0-9a-f]{32}\b/gi, "<id>");
const say = (text) => { log?.write(`${text}\n`); console.log(mask(text)); };
function run([command, args], { quiet = false } = {}) {
  return new Promise((done) => {
    log?.write(`$ ${command} ${args.join(" ")}\n`);
    const child = spawn(command, args, { cwd: here(".."), env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: ["ignore", "pipe", "pipe"] });
    let text = "";
    const take = (chunk, to) => { const piece = chunk.toString(); text += piece; log?.write(piece); if (!quiet) to.write(mask(piece)); };
    child.stdout.on("data", (chunk) => take(chunk, process.stdout));
    child.stderr.on("data", (chunk) => take(chunk, process.stderr));
    child.on("error", (error) => done({ ok: false, text: `${text}\n${error.message}` }));
    child.on("close", (code) => done({ ok: code === 0, text }));
  });
}
class Failed extends Error {}
// A stage that does not apply says so, and is shown as skipped, never as passed.
class Skipped extends Error {}
const skip = (why) => { throw new Skipped(why); };
const must = async (command, why, options) => { const done = await run(command, options); if (!done.ok) throw new Failed(why || "the step failed; see above"); return done.text; };
const json = (text) => JSON.parse(text.slice(text.search(/[[{]/)));
const query = async (statement) => json(await must([wrangler, ["d1", "execute", "STORE", ...d1Wrangler, "--yes", "--json", "--command", statement]], "D1 did not answer", { quiet: true }))[0].results;

// ---- the stages ----
const result = { env, database, bucket, build: null, bulk_build: null, started: new Date().toISOString(), stages: [], rows_written: null, rows: null, payload_objects: null, passed: false };
const buildOf = (path) => { const db = new DatabaseSync(path, { readOnly: true }); try { return db.prepare("SELECT substr(id, 7, 16) AS build FROM run WHERE id LIKE 'build-%' ORDER BY id LIMIT 1").get()?.build || null; } finally { db.close(); } };

// How many rows the store's tables hold, whichever of them this database has yet.
async function rows() {
  const tables = (await query("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%' AND name NOT LIKE 'd1_%' AND name NOT LIKE '%_fts%'")).map((row) => row.name);
  let held = 0;
  // Ninety counts a statement: D1 answers at most 100 columns.
  for (let at = 0; at < tables.length; at += 90) {
    const [counted] = await query(`SELECT ${tables.slice(at, at + 90).map((table) => `(SELECT count(*) FROM "${table}")`).join(" + ")} AS rows`);
    held += counted.rows;
  }
  return held;
}

async function writeConfig() {
  // The committed configuration with this environment's names and the database's id, which
  // is looked up by name and goes nowhere but this git-ignored file.
  const listed = json(await must([wrangler, ["d1", "list", "--json"]], "the account's databases could not be listed", { quiet: true }));
  const found = listed.find((one) => one.name === database);
  if (!found) throw new Failed(`the account has no database named ${database}`);
  let text = readFileSync(here("../wrangler.jsonc"), "utf8");
  for (const [preview, real] of [["thenwhat-store-preview", database], ["thenwhat-payloads-preview", bucket], ["thenwhat-work-preview", production ? "thenwhat-work" : "thenwhat-work-preview"]]) text = text.replaceAll(preview, real);
  const at = `"database_name": "${database}"`;
  if (!text.includes(at)) throw new Failed("wrangler.jsonc does not name the store's database");
  writeFileSync(config, text.replace(at, `${at}, "database_id": "${found.uuid}"`));
  say(`wrote ${config.split("/").at(-1)} for ${database} (its id is in that file only)`);
}

const stages = [
  ["privacy", "no person is named in the files or the payload folders", async () => {
    await must(thenwhat("store", "prove-no-people", hot, bulk, ...payloads.flatMap((path) => ["--payloads", path])),
      "the build is not proved free of people (or `thenwhat store prove-no-people` could not be run): nothing was sent");
  }],
  ["jurisdiction", "the database and the bucket read back as eu", async () => {
    if (!remote) return skip("local engine: there is no jurisdiction to read");
    const info = json(await must([wrangler, ["d1", "info", database, "--json"]], `the database ${database} could not be read`, { quiet: true }));
    if (info.jurisdiction !== "eu") throw new Failed(`the database ${database} reads back jurisdiction ${JSON.stringify(info.jurisdiction ?? null)}, not "eu": nothing is written to it`);
    // A bucket is found under a jurisdiction only if it was created in it.
    const held = await must([wrangler, ["r2", "bucket", "info", bucket, "--jurisdiction", "eu"]], `the bucket ${bucket} is not found in the eu jurisdiction: nothing is written to it`, { quiet: true });
    const stated = /jurisdiction[^a-z]*([a-z]+)/i.exec(held)?.[1];
    if (stated && stated.toLowerCase() !== "eu") throw new Failed(`the bucket ${bucket} reads back jurisdiction ${stated}, not eu`);
    say(`${database}: eu; ${bucket}: found in eu`);
  }],
  ["config", "the remote configuration, id looked up by name", async () => { if (remote) await writeConfig(); else say("local engine: the committed configuration is used"); }],
  ["bookmark", "the Time Travel bookmark, kept outside the repository", async () => {
    if (!remote) return skip("local engine: no Time Travel");
    const text = await must([wrangler, ["d1", "time-travel", "info", database, "--json"]], "the bookmark could not be read", { quiet: true });
    const folder = join(homedir(), "Library", "Application Support", "thenwhat", "store", "bookmarks");
    mkdirSync(folder, { recursive: true });
    const file = join(folder, `${env}-${stamp}.json`);
    writeFileSync(file, text.slice(text.search(/[[{]/)));
    result.bookmark_file = file;
    say(`bookmark written to ${file}: restore with \`wrangler d1 time-travel restore ${database} --bookmark <it>\``);
  }],
  ["empty", "the store holds no row", async () => {
    // Before the migrations: a store that holds rows must never meet a migration that
    // makes a table again (0007 did, on the loaded preview, and D1 stopped it for its
    // CPU time after 38 s on 17 November 2026).
    const held = await rows();
    if (!held) return say("the store is empty");
    if (!has("--replace")) throw new Failed(`${database} already holds ${held} rows: pass --replace to clear a preview store first, or look at what is there`);
    if (production) throw new Failed(`${database} holds ${held} rows, and production is never emptied by this command. If it is to be replaced, the operator runs:\n  ${replaceCommands.join("\n  ")}`);
    if (!remote || held <= 200_000) return void (await must(node("empty-store", "--empty", database, ...d1)));
    // A large preview store is replaced, not emptied (docs/deploy.md): seconds, and no billed write.
    say(`${database} holds ${held} rows: replacing the preview database`);
    await must([wrangler, ["d1", "delete", database, "--skip-confirmation"]], "the preview database could not be deleted");
    await must([wrangler, ["d1", "create", database, "--jurisdiction", "eu"]], "the preview database could not be created again", { quiet: true });
    await writeConfig();
    const info = json(await must([wrangler, ["d1", "info", database, "--json"]], "the new database could not be read", { quiet: true }));
    if (info.jurisdiction !== "eu") throw new Failed("the new database does not read back as eu");
  }],
  ["migrations", "the schema and the service's tables", async () => {
    // What this database has applied must be the first of the files, in their order: a
    // migration it applied under a name the files no longer have cannot be reconciled.
    const files = readdirSync(here("../migrations")).filter((name) => name.endsWith(".sql")).sort();
    const known = (await query("SELECT count(*) AS n FROM sqlite_master WHERE type = 'table' AND name = 'd1_migrations'"))[0].n;
    const applied = known ? (await query("SELECT name FROM d1_migrations ORDER BY id")).map((row) => row.name) : [];
    say(`applied ${applied.length} of ${files.length}: ${applied.join(", ") || "none"}`);
    const strange = applied.findIndex((name, at) => files[at] !== name);
    if (strange >= 0) throw new Failed(`${database} applied ${applied[strange]} as its migration ${strange + 1}, where the files have ${files[strange] ?? "nothing"}: the migrations were renumbered since. Replace this database:\n  ${replaceCommands.join("\n  ")}`);
    // A migration that makes a table again (it says so: `-- rebuilds: <table>`, or it drops
    // a table) copies every row of it in one transaction, which D1 does not finish on a
    // loaded store. It is applied to an empty store only.
    const rebuilding = files.slice(applied.length).filter((name) => /^-- rebuilds:|\bDROP TABLE\b/m.test(readFileSync(here(`../migrations/${name}`), "utf8")));
    if (rebuilding.length) {
      const held = await rows();
      if (held) throw new Failed(`${rebuilding.join(", ")} makes a table again and ${database} holds ${held} rows: apply to an empty store. Replace this database:\n  ${replaceCommands.join("\n  ")}`);
    }
    await must([wrangler, ["d1", "migrations", "apply", "STORE", ...d1Wrangler]]);
  }],
  ["dump", "the hot file as SQL, replayed strictly here", async () => {
    await must(node("dump-for-import", hot, join(sql, "store.sql"), "--rows-a-file", value("--rows-a-file") || "60000"));
    await must(node("check-dump", sql));
    result.rows = JSON.parse(readFileSync(join(sql, "manifest.json"), "utf8")).rows;
  }],
  ["import", "the files into D1, counted against the manifest", async () => {
    const text = await must(node("import-folder", sql, ...d1));
    const written = /loaded in [\d.]+ s, rows_written (\d+)/.exec(text)?.[1];
    result.rows_written = written ? Number(written) : null;
  }],
  ["checksum", "every hot table in D1 against the build's checks", async () => {
    if (!existsSync(checks)) await must(thenwhat("store", "checksum", hot, "--tier", "hot", "--checks", checks), "the build's checks could not be made");
    await must(node("checksum-d1", "--checks", checks, "--file", hot, ...d1));
  }],
  ["payloads", "the payload objects of both tiers", async () => {
    let objects = 0;
    for (const folder of payloads) {
      const text = await must(node("upload-payloads", folder, ...r2, ...(remote ? [] : ["--state", join(work, `payloads-${objects}.json`)])));
      objects += Number(/^(\d+) objects/m.exec(text)?.[1] || 0);
    }
    result.payload_objects = objects;
  }],
  ["bulk", "the bulk file, in parts, with its manifest", async () => {
    // A rebuild may keep an unchanged bulk file, under the build that made it. If the
    // bucket's manifest for that build already describes this very file, it is not sent again.
    const back = join(work, `manifest-${env}-before.json`);
    rmSync(back, { force: true });
    const there = await run([wrangler, ["r2", "object", "get", `${bucket}/bulk/${result.bulk_build}/manifest.json`, "--file", back, ...r2Wrangler]], { quiet: true });
    if (there.ok && existsSync(back) && JSON.parse(readFileSync(back, "utf8")).sha256 === (await sha256(bulk))) return say(`bulk build ${result.bulk_build} is already in the bucket, the same file: not sent again`);
    await must(node("upload-bulk", bulk, ...r2, "--build", result.bulk_build, ...(remote ? [] : ["--state", join(work, "bulk.json")])));
  }],
  ["verify", "the bulk manifest read back and held to the file", async () => {
    if (!remote) {
      // On the local engine the whole file comes back and is compared.
      await must(node("download-bulk", result.bulk_build, join(work, "bulk-back.sqlite"), ...r2));
      if ((await sha256(join(work, "bulk-back.sqlite"))) !== (await sha256(bulk))) throw new Failed("the bulk file that came back is not the one that went up");
      return say("the bulk file came back the same");
    }
    const file = join(work, `manifest-${env}-back.json`);
    await must([wrangler, ["r2", "object", "get", `${bucket}/bulk/${result.bulk_build}/manifest.json`, "--file", file, ...r2Wrangler]], "the bulk manifest could not be read back", { quiet: true });
    const manifest = JSON.parse(readFileSync(file, "utf8"));
    if (manifest.sha256 !== (await sha256(bulk)) || manifest.build !== result.bulk_build) throw new Failed("the manifest in the bucket does not describe this bulk file");
    say(`the manifest in the bucket describes this bulk file: build ${manifest.build}, ${manifest.parts.length} part(s)`);
  }],
  ["export", "the export from the hot file against the working database", async () => {
    if (remote) return skip("local only: not part of a remote cut-over; `make export-compare` is run on its own");
    if (has("--skip-export")) return skip("--skip-export");
    await must(thenwhat("export-compare", "--store", hot, "--payloads", payloads[0] || dir, "--allow-named"));
  }],
];

if (has("--dry-run")) {
  console.log(`cut-over of ${env}: database ${database}, bucket ${bucket}${remote ? ", remote" : ", local engine"}; build folder ${dir}`);
  for (const [n, [name, what]] of stages.entries()) console.log(`${String(n).padStart(2)} ${name.padEnd(13)} ${what}`);
  console.log(`hot file      ${hot}${existsSync(hot) ? "" : "   (MISSING)"}`);
  console.log(`bulk file     ${bulk}${existsSync(bulk) ? "" : "   (MISSING)"}`);
  console.log(`payloads      ${payloads.join(", ") || "(none found)"}`);
  console.log(`checks        ${checks}${existsSync(checks) ? "" : "   (will be made)"}`);
  console.log(`log, result   ${out}/`);
  if (production) console.log(`production: --confirm ${database} was given; each script gets --production; a store that is not empty stops the run`);
  console.log("nothing was run");
  process.exit(0);
}

for (const [name, path] of [["the hot file", hot], ["the bulk file", bulk]]) if (!existsSync(path)) stop(`${name} is not at ${path}`);
// Production's configuration holds its database's id: it goes even when the run is stopped by hand.
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => { if (production) rmSync(config, { force: true }); console.error(`\nstopped by ${signal}${production ? "; the production configuration was removed" : ""}`); process.exit(130); });
mkdirSync(out, { recursive: true });
mkdirSync(work, { recursive: true });
log = createWriteStream(join(out, `${env}-${stamp}.log`));
// The hot file, and D1 after it, carry the build that made them. The bulk file carries
// its own: a rebuild may keep an unchanged bulk file, and then the two differ. Where the
// build left its note of both (`*.watermarks.json`), the files must agree with it.
result.build = buildOf(hot) || (await sha256(hot)).slice(0, 16);
result.bulk_build = buildOf(bulk) || (await sha256(bulk)).slice(0, 16);
for (const name of readdirSync(dir).filter((one) => one.endsWith(".watermarks.json"))) {
  const noted = JSON.parse(readFileSync(join(dir, name), "utf8"));
  if ((noted.build && noted.build !== result.build) || (noted.bulk_build && noted.bulk_build !== result.bulk_build)) {
    stop(`${name} says build ${noted.build} with bulk build ${noted.bulk_build}, but the files say ${result.build} and ${result.bulk_build}: this folder is not one build`);
  }
}
say(`cut-over of ${env}: database ${database}, bucket ${bucket}, build ${result.build}${result.bulk_build === result.build ? "" : `, keeping bulk build ${result.bulk_build}`}`);
const began = Date.now();
let failed = null;
for (const [n, [name, what, stage]] of stages.entries()) {
  say(`\n== ${n} ${name}: ${what}`);
  const started = Date.now();
  let error = null;
  let skipped = null;
  try { await stage(); } catch (caught) { if (caught instanceof Skipped) { skipped = caught.message; say(`skipped: ${skipped}`); } else error = caught; }
  const seconds = (Date.now() - started) / 1000;
  result.stages.push({ stage: name, seconds: Number(seconds.toFixed(1)), ok: !error, ...(skipped ? { skipped } : {}) });
  if (error) { failed = name; say(`\nFAILED at stage ${n}, ${name}: ${error instanceof Failed ? error.message : error.stack}`); break; }
}
result.seconds = Number(((Date.now() - began) / 1000).toFixed(1));
result.passed = !failed;
result.failed_at = failed;
say("\n== times");
for (const { stage, seconds, ok, skipped } of result.stages) say(skipped ? `${stage.padEnd(13)} skipped (${skipped})` : `${stage.padEnd(13)} ${String(seconds.toFixed(1)).padStart(7)} s${ok ? "" : "   FAILED"}`);
say(`${"total".padEnd(13)} ${String(result.seconds.toFixed(1)).padStart(7)} s`);
say(`build ${result.build}${result.bulk_build === result.build ? "" : ` (bulk build ${result.bulk_build})`}; table rows ${result.rows ?? "?"}; rows D1 says were written ${result.rows_written ?? "not said"}; payload objects ${result.payload_objects ?? "?"}`);
const file = join(out, `result-${env}-${stamp}.json`);
writeFileSync(file, JSON.stringify(result, null, 1) + "\n");
const left = result.stages.filter((stage) => stage.skipped).map((stage) => stage.stage);
say(failed ? `\nFAILED at ${failed}; result in ${file}` : `\nthe cut-over of ${env} passed${left.length ? ` (not run: ${left.join(", ")})` : ""}; result in ${file}`);
// Production's configuration holds its database's id: it does not outlive the run.
if (production) rmSync(config, { force: true });
if (!remote && !value("--work")) rmSync(work, { recursive: true, force: true });
await new Promise((done) => log.end(done));
process.exit(failed ? 1 : 0);
