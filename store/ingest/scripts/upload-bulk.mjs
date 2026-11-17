// Puts the bulk tier, one SQLite file, into the PAYLOADS bucket: compressed (zstd), cut
// into parts under Wrangler's limit for one upload, with a manifest written last.
//
//   node scripts/upload-bulk.mjs <bulk.sqlite> --persist-to <dir> [--build <id>]     the local engine
//   node scripts/upload-bulk.mjs <bulk.sqlite> --remote [--build <id>]               the preview bucket, EU
//
//   bulk/<build id>/part-0001.zst ...    the parts, 200 MB each (Wrangler takes 300 MiB at most)
//   bulk/<build id>/manifest.json        build, date, the file's name, size and SHA-256, the
//                                        compressed size and SHA-256, and each part's
//
// The build id is `--build`, else the first 16 hex of the file's SHA-256. The manifest is
// uploaded only when every part is, so a build with a manifest is whole. Resumable: the
// parts are cut again (the same bytes each time) and a part noted as uploaded with the
// same SHA-256 is skipped. `--part-mb N` sets the part size; `--work <dir>` where parts
// are cut (a folder in the system's temporary directory, removed at the end).
import { createReadStream, createWriteStream, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { createZstdCompress } from "node:zlib";
import { WRANGLER_PUT_LIMIT_BYTES, bucket, sha256 } from "./r2.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const file = argv[0];
if (!file || file.startsWith("--") || !existsSync(file)) { console.error("usage: upload-bulk.mjs <bulk.sqlite> (--remote | --persist-to <dir>) [--build <id>] [--part-mb N] [--production <bucket>]"); process.exit(2); }
let to;
try { to = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
const partBytes = Math.floor((Number(value("--part-mb")) || 200) * 1e6);
if (partBytes > WRANGLER_PUT_LIMIT_BYTES) { console.error("a part may not be over Wrangler's 300 MiB an upload"); process.exit(2); }

const started = Date.now();
const whole = await sha256(file);
const build = value("--build") || whole.slice(0, 16);
if (!/^[A-Za-z0-9._-]{1,64}$/.test(build)) { console.error("a build id is letters, digits, ., - or _"); process.exit(2); }
const work = value("--work") || mkdtempSync(join(tmpdir(), "thenwhat-bulk-"));
mkdirSync(work, { recursive: true });
const statePath = value("--state") || here(`../.upload-state/bulk-${build}-${to.name}${to.remote ? "" : ".local"}.json`);
mkdirSync(dirname(statePath), { recursive: true });
const state = existsSync(statePath) ? JSON.parse(readFileSync(statePath, "utf8")) : {};

// Compressed and cut in one pass: each part is closed when it reaches its size.
const parts = [], packed = createHash("sha256");
let out = null, hash = null, size = 0, packedBytes = 0;
const close = async () => {
  if (!out) return;
  await new Promise((resolve, reject) => { out.end((error) => (error ? reject(error) : resolve())); });
  parts.at(-1).bytes = size; parts.at(-1).sha256 = hash.digest("hex");
  out = null;
};
for await (const chunk of createReadStream(file).pipe(createZstdCompress())) {
  packed.update(chunk); packedBytes += chunk.length;
  for (let at = 0; at < chunk.length;) {
    if (!out) {
      const name = `part-${String(parts.length + 1).padStart(4, "0")}.zst`;
      parts.push({ name });
      out = createWriteStream(join(work, name)); hash = createHash("sha256"); size = 0;
    }
    const piece = chunk.subarray(at, at + (partBytes - size));
    hash.update(piece); size += piece.length; at += piece.length;
    if (!out.write(piece)) await new Promise((resolve) => out.once("drain", resolve));
    if (size >= partBytes) await close();
  }
}
await close();
const fileBytes = statSync(file).size;
console.log(`${basename(file)}: ${(fileBytes / 1e6).toFixed(1)} MB, ${(packedBytes / 1e6).toFixed(1)} MB compressed, ${parts.length} part(s), build ${build}, into ${to.label}`);

let uploaded = 0, skipped = 0;
for (const part of parts) {
  const key = `bulk/${build}/${part.name}`, began = Date.now();
  if (state[part.name] === part.sha256) { skipped += 1; continue; }
  try { await to.put(key, join(work, part.name)); } catch (error) { console.error(`FAILED ${key}: ${error.message}\nrun again to go on from here`); process.exit(1); }
  state[part.name] = part.sha256; writeFileSync(statePath, JSON.stringify(state)); uploaded += 1;
  console.log(`  ${part.name}  ${(part.bytes / 1e6).toFixed(1)} MB  ${((Date.now() - began) / 1000).toFixed(1)} s`);
}
const manifest = { build, date: new Date().toISOString().slice(0, 10), file: basename(file), bytes: fileBytes, sha256: whole,
  compression: "zstd", compressed_bytes: packedBytes, compressed_sha256: packed.digest("hex"), parts };
writeFileSync(join(work, "manifest.json"), JSON.stringify(manifest, null, 1) + "\n");
try { await to.put(`bulk/${build}/manifest.json`, join(work, "manifest.json")); } catch (error) { console.error(`FAILED the manifest: ${error.message}`); process.exit(1); }
if (!value("--work")) rmSync(work, { recursive: true, force: true });
console.log(`uploaded ${uploaded} part(s), already there ${skipped}, and the manifest, in ${((Date.now() - started) / 1000).toFixed(1)} s`);
console.log(`restore with: node scripts/download-bulk.mjs ${build} <out.sqlite> ${to.remote ? "--remote" : "--persist-to <dir>"}`);
