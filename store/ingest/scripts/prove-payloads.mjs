// Proves that every payload object the hot and the bulk file refer to is in the bucket
// under its key with its bytes, and that any copy in the build's payload folders is too
// (payload-proof.mjs says how). The cut-over's payloads stage runs it after the uploads.
//
//   node scripts/prove-payloads.mjs --hot <file> --bulk <file> [--payloads <folder>]... (--remote | --persist-to <dir>) [--production <bucket>] [--jobs N]
//
// Exit 1 when an object is missing, differs, or could not be read; the first are named.
import { existsSync } from "node:fs";
import { provePayloads } from "./payload-proof.mjs";
import { bucket } from "./r2.mjs";

const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const hot = value("--hot"), bulk = value("--bulk");
const folders = argv.flatMap((arg, at) => (arg === "--payloads" ? [argv[at + 1]] : []));
if (!hot || !bulk || folders.some((folder) => !folder || folder.startsWith("--"))) { console.error("usage: prove-payloads.mjs --hot <file> --bulk <file> [--payloads <folder>]... (--remote | --persist-to <dir>) [--production <bucket>] [--jobs N]"); process.exit(2); }
let from;
try { from = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
for (const folder of folders) if (!existsSync(folder)) { console.error(`no payload folder at ${folder}`); process.exit(2); }

try {
  const proof = await provePayloads({ files: [{ tier: "hot", path: hot }, { tier: "bulk", path: bulk }], folders, store: from, jobs: Number(value("--jobs")) || 4 });
  for (const why of proof.failures) console.error(`FAILED payload/${why}`);
  if (proof.failed > proof.failures.length) console.error(`… and ${proof.failed - proof.failures.length} more`);
  process.exit(proof.ok ? 0 : 1);
} catch (error) { console.error(`FAILED: ${error.message}`); process.exit(1); }
