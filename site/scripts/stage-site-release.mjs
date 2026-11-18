#!/usr/bin/env node
// Offline staging half of a content-addressed site release.
//
//   node scripts/stage-site-release.mjs DIST NEW_RELEASE_DIRECTORY [--noindex]
//
// DIST is the built and indexed site; it is only read. Every claim route file (eight per
// claim in DIST/lookup.json), every pagefind/ file and oversized lists are written once, by the SHA-256 of
// its bytes, to NEW_RELEASE_DIRECTORY/objects/site-files/v1/<sha256>, and listed in a
// manifest shard at assets/_site-release/<first two hex digits of sha256(path)>.json.
// Every other regular file is copied to NEW_RELEASE_DIRECTORY/assets/<path>. The release is
// staged in a sibling temporary directory and renamed into place only when every check passes.
// Metrics are printed to stdout as JSON.
import { createHash, randomBytes } from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { FILE_COUNT_LIMIT, FILE_LIMIT, countFiles, oversizedFiles } from "./dist-size.mjs";
import { canMoveLargeReleaseFile } from "../src/lib/release-paths.mjs";

const RESERVED = "_site-release";
const OBJECTS = "objects/site-files/v1";
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const CHUNK = 1 << 20;
const CONCURRENCY = 8;
const USAGE = "Usage: node scripts/stage-site-release.mjs DIST NEW_RELEASE_DIRECTORY [--noindex]";

class UsageError extends Error {}

const claimPaths = (slug) => [
  `${slug}/index.html`,
  `data/claims/${slug}.json`,
  `changes/${slug}.xml`,
  `embed/${slug}/index.html`,
  `oembed/${slug}.json`,
  `og/${slug}.png`,
  `og/square/${slug}.png`,
  `og/tall/${slug}.png`,
];

const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const compare = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

function parseArgs(argv) {
  const positional = [];
  let noindex = false;
  for (const arg of argv) {
    if (arg === "--noindex") {
      if (noindex) throw new UsageError("--noindex was given more than once.");
      noindex = true;
    } else if (arg.startsWith("-")) {
      throw new UsageError(`Unknown option: ${arg}`);
    } else {
      positional.push(arg);
    }
  }
  if (positional.length !== 2) throw new UsageError("Expected exactly DIST and NEW_RELEASE_DIRECTORY.");
  if (positional.some((p) => p.length === 0 || p.includes("\0"))) throw new UsageError("Empty or invalid path argument.");
  return { dist: positional[0], destination: positional[1], noindex };
}

async function lstatOrNull(target) {
  try {
    return await fsp.lstat(target);
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

/** Resolve DIST and the destination, refusing a symlinked DIST, an existing destination, or one inside DIST. */
async function resolvePaths(distArg, destinationArg) {
  const distStat = await lstatOrNull(distArg);
  if (!distStat) throw new Error(`DIST does not exist: ${distArg}`);
  if (distStat.isSymbolicLink()) throw new Error(`DIST is a symlink, which is refused: ${distArg}`);
  if (!distStat.isDirectory()) throw new Error(`DIST is not a directory: ${distArg}`);
  const dist = fs.realpathSync.native(distArg);

  const absoluteDestination = path.resolve(destinationArg);
  const base = path.basename(absoluteDestination);
  if (!base || base === "." || base === "..") throw new Error(`Invalid destination: ${destinationArg}`);
  if (await lstatOrNull(absoluteDestination)) throw new Error(`Destination already exists: ${destinationArg}`);
  const parentArg = path.dirname(absoluteDestination);
  const parentStat = await lstatOrNull(parentArg);
  if (!parentStat) throw new Error(`Destination's parent directory does not exist: ${parentArg}`);
  const parent = fs.realpathSync.native(parentArg);
  if (!(await fsp.stat(parent)).isDirectory()) throw new Error(`Destination's parent is not a directory: ${parentArg}`);
  const destination = path.join(parent, base);

  const inside = (outer, inner) => {
    const rel = path.relative(outer, inner);
    return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
  };
  if (inside(dist, destination) || inside(dist.toLowerCase(), destination.toLowerCase())) {
    throw new Error(`Destination is inside DIST: ${destinationArg}`);
  }
  // Also compare by identity, which catches hard-to-spell aliases (case, mounts).
  const distIdentity = await fsp.stat(dist);
  for (let current = parent; ; current = path.dirname(current)) {
    const s = await fsp.stat(current);
    if (s.dev === distIdentity.dev && s.ino === distIdentity.ino) throw new Error(`Destination is inside DIST: ${destinationArg}`);
    if (path.dirname(current) === current) break;
  }
  return { dist, destination, parent, base };
}

/** Every regular file under DIST, by POSIX relative path, with its size. Refuses anything else. */
async function walk(dist) {
  const files = new Map();
  const pending = [""];
  while (pending.length) {
    const relDir = pending.pop();
    const entries = await fsp.readdir(path.join(dist, relDir));
    for (const name of entries) {
      const rel = relDir ? `${relDir}/${name}` : name;
      if (!relDir && name.toLowerCase() === RESERVED) {
        throw new Error(`DIST uses the reserved ${RESERVED} namespace: ${rel}`);
      }
      const s = await fsp.lstat(path.join(dist, rel));
      if (s.isSymbolicLink()) throw new Error(`Symlinks are refused: ${rel}`);
      if (s.isDirectory()) pending.push(rel);
      else if (s.isFile()) files.set(rel, s.size);
      else throw new Error(`Special files are refused: ${rel}`);
    }
  }
  return files;
}

async function readLookup(dist, files) {
  if (!files.has("lookup.json")) throw new Error("DIST/lookup.json is missing.");
  const fh = await fsp.open(path.join(dist, "lookup.json"), fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  let text;
  try {
    if (!(await fh.stat()).isFile()) throw new Error("DIST/lookup.json is not a regular file.");
    text = await fh.readFile("utf8");
  } finally {
    await fh.close();
  }
  let lookup;
  try {
    lookup = JSON.parse(text);
  } catch (error) {
    throw new Error(`DIST/lookup.json is not valid JSON: ${error.message}`);
  }
  const claims = lookup && typeof lookup === "object" && !Array.isArray(lookup) ? lookup.claims : undefined;
  if (!claims || typeof claims !== "object" || Array.isArray(claims) || !Object.hasOwn(lookup, "claims")) {
    throw new Error("DIST/lookup.json has no claims object.");
  }
  const slugs = Reflect.ownKeys(claims);
  for (const slug of slugs) {
    if (typeof slug !== "string" || !SLUG.test(slug)) throw new Error(`Invalid claim slug in lookup.json: ${String(slug)}`);
  }
  return slugs.sort(compare);
}

/** Stream a source file into a new file, hashing the bytes. Refuses a source that changes underneath. */
async function copyHashed(source, target, expectedSize, buffer) {
  const input = await fsp.open(source, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const before = await input.stat();
    if (!before.isFile()) throw new Error(`Not a regular file: ${source}`);
    if (before.size !== expectedSize) throw new Error(`File changed while staging: ${source}`);
    const output = await fsp.open(target, "wx");
    const hash = createHash("sha256");
    let bytes = 0;
    try {
      for (;;) {
        const { bytesRead } = await input.read(buffer, 0, buffer.length, null);
        if (bytesRead === 0) break;
        const chunk = buffer.subarray(0, bytesRead);
        hash.update(chunk);
        let written = 0;
        while (written < bytesRead) {
          const result = await output.write(chunk, written, bytesRead - written, null);
          written += result.bytesWritten;
        }
        bytes += bytesRead;
      }
    } finally {
      await output.close();
    }
    const after = await input.stat();
    if (bytes !== before.size || after.size !== before.size || after.mtimeMs !== before.mtimeMs || after.ino !== before.ino) {
      throw new Error(`File changed while staging: ${source}`);
    }
    return { digest: hash.digest("hex"), bytes };
  } finally {
    await input.close();
  }
}

async function hashFile(file, buffer) {
  const fh = await fsp.open(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    const hash = createHash("sha256");
    let bytes = 0;
    for (;;) {
      const { bytesRead } = await fh.read(buffer, 0, buffer.length, null);
      if (bytesRead === 0) break;
      hash.update(buffer.subarray(0, bytesRead));
      bytes += bytesRead;
    }
    return { digest: hash.digest("hex"), bytes };
  } finally {
    await fh.close();
  }
}

async function pool(items, worker) {
  let next = 0;
  let failure;
  const run = async () => {
    const buffer = Buffer.allocUnsafe(CHUNK);
    while (!failure && next < items.length) {
      try {
        await worker(items[next++], buffer);
      } catch (error) {
        failure ??= error;
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, items.length) }, run));
  if (failure) throw failure;
}

async function treeMetrics(directory) {
  let files = 0;
  let bytes = 0;
  for (const entry of await fsp.readdir(directory, { withFileTypes: true, recursive: true })) {
    if (entry.isFile()) {
      files += 1;
      bytes += (await fsp.lstat(path.join(entry.parentPath, entry.name))).size;
    }
  }
  return { files, bytes };
}

async function stage({ dist, staging, noindex }) {
  const files = await walk(dist);
  const slugs = await readLookup(dist, files);

  const moved = new Set();
  const missing = [];
  for (const slug of slugs) {
    for (const rel of claimPaths(slug)) {
      if (files.has(rel)) moved.add(rel);
      else missing.push(rel);
    }
  }
  if (missing.length) {
    throw new Error(`Missing ${missing.length} claim file(s): ${missing.slice(0, 20).join(", ")}${missing.length > 20 ? ", …" : ""}`);
  }
  let pagefindFiles = 0;
  for (const [rel, size] of files) {
    if (rel.startsWith("pagefind/")) {
      moved.add(rel);
      pagefindFiles += 1;
    } else if (size > FILE_LIMIT && canMoveLargeReleaseFile(rel)) {
      moved.add(rel);
    }
  }
  if (pagefindFiles === 0) throw new Error("DIST has no pagefind/ files; the site must be indexed before staging.");

  const movedPaths = [...moved].sort(compare);
  const assetPaths = [...files.keys()].filter((rel) => !moved.has(rel)).sort(compare);
  const shards = new Map();
  for (const rel of movedPaths) {
    const shard = sha256(rel).slice(0, 2);
    if (!shards.has(shard)) shards.set(shard, []);
    shards.get(shard).push(rel);
  }

  // Refuse early, before copying, when the final assets cannot fit.
  const plannedAssets = assetPaths.length + shards.size;
  if (plannedAssets > FILE_COUNT_LIMIT) {
    throw new Error(`The release assets would hold ${plannedAssets} files; the limit is ${FILE_COUNT_LIMIT}.`);
  }
  const tooLarge = assetPaths.filter((rel) => files.get(rel) > FILE_LIMIT);
  if (tooLarge.length) {
    throw new Error(`Asset file(s) over ${FILE_LIMIT} bytes: ${tooLarge.slice(0, 20).join(", ")}`);
  }

  const assetsDir = path.join(staging, "assets");
  const objectsDir = path.join(staging, ...OBJECTS.split("/"));
  const tempDir = path.join(staging, ".incoming");
  await fsp.mkdir(assetsDir);
  await fsp.mkdir(objectsDir, { recursive: true });
  await fsp.mkdir(tempDir);

  // Assets: copied as they are.
  const assetDigests = new Map();
  const madeDirs = new Set();
  const ensureDir = async (dir) => {
    if (madeDirs.has(dir)) return;
    await fsp.mkdir(dir, { recursive: true });
    madeDirs.add(dir);
  };
  await pool(assetPaths, async (rel, buffer) => {
    const target = path.join(assetsDir, ...rel.split("/"));
    await ensureDir(path.dirname(target));
    const { digest } = await copyHashed(path.join(dist, ...rel.split("/")), target, files.get(rel), buffer);
    assetDigests.set(rel, digest);
  });

  // Objects: each distinct content written once under its digest.
  const entries = new Map();
  const placed = new Map();
  let tempCounter = 0;
  let deduplicated = 0;
  await pool(movedPaths, async (rel, buffer) => {
    const temp = path.join(tempDir, String(tempCounter++));
    const { digest, bytes } = await copyHashed(path.join(dist, ...rel.split("/")), temp, files.get(rel), buffer);
    entries.set(rel, [digest, bytes]);
    if (placed.has(digest)) {
      deduplicated += 1;
      await fsp.unlink(temp);
    } else {
      placed.set(digest, bytes);
      await fsp.rename(temp, path.join(objectsDir, digest));
    }
  });
  await fsp.rmdir(tempDir);

  // Manifests, deterministic: shards and paths in code-unit order.
  const manifestDir = path.join(assetsDir, RESERVED);
  await fsp.mkdir(manifestDir);
  let manifestBytes = 0;
  for (const shard of [...shards.keys()].sort(compare)) {
    const listed = {};
    for (const rel of shards.get(shard)) listed[rel] = entries.get(rel);
    const body = JSON.stringify({ noindex, files: listed });
    await fsp.writeFile(path.join(manifestDir, `${shard}.json`), body, { flag: "wx" });
    manifestBytes += Buffer.byteLength(body);
  }

  // Read checks: everything staged is read back and compared.
  await pool(assetPaths, async (rel, buffer) => {
    const { digest, bytes } = await hashFile(path.join(assetsDir, ...rel.split("/")), buffer);
    if (digest !== assetDigests.get(rel) || bytes !== files.get(rel)) throw new Error(`Staged asset does not match its source: ${rel}`);
  });
  await pool([...placed.keys()], async (expected, buffer) => {
    const { digest, bytes } = await hashFile(path.join(objectsDir, expected), buffer);
    if (digest !== expected || bytes !== placed.get(expected)) throw new Error(`Staged object does not match its digest: ${expected}`);
  });
  const objectNames = await fsp.readdir(objectsDir);
  if (objectNames.length !== placed.size) throw new Error("The object store holds unexpected files.");
  for (const shard of shards.keys()) {
    const manifest = JSON.parse(await fsp.readFile(path.join(manifestDir, `${shard}.json`), "utf8"));
    if (manifest.noindex !== noindex) throw new Error(`Manifest ${shard} has the wrong noindex flag.`);
    const listed = Object.keys(manifest.files);
    const expected = shards.get(shard);
    if (listed.length !== expected.length || listed.some((rel, i) => rel !== expected[i])) {
      throw new Error(`Manifest ${shard} does not list its paths in order.`);
    }
    for (const rel of listed) {
      const [digest, bytes] = manifest.files[rel];
      if (placed.get(digest) !== bytes) throw new Error(`Manifest ${shard} names an object that is not staged: ${rel}`);
    }
  }

  // The host's limits, applied to the final assets including manifests.
  const assetCount = countFiles(assetsDir);
  if (assetCount > FILE_COUNT_LIMIT) {
    throw new Error(`The release assets hold ${assetCount} files; the limit is ${FILE_COUNT_LIMIT}.`);
  }
  const oversized = oversizedFiles(assetsDir, FILE_LIMIT);
  if (oversized.length) {
    throw new Error(`Asset file(s) over ${FILE_LIMIT} bytes: ${oversized.slice(0, 20).map((f) => `${f.file} (${f.bytes})`).join(", ")}`);
  }

  const inputBytes = [...files.values()].reduce((sum, n) => sum + n, 0);
  const movedBytes = movedPaths.reduce((sum, rel) => sum + files.get(rel), 0);
  const assetMetrics = await treeMetrics(assetsDir);
  const objectMetrics = await treeMetrics(objectsDir);
  return {
    noindex,
    claims: slugs.length,
    input: { files: files.size, bytes: inputBytes },
    moved: {
      files: movedPaths.length,
      bytes: movedBytes,
      claimFiles: slugs.length * 8,
      pagefindFiles,
      largeListFiles: movedPaths.length - slugs.length * 8 - pagefindFiles,
    },
    objects: { files: objectMetrics.files, bytes: objectMetrics.bytes, deduplicatedFiles: deduplicated },
    assets: {
      files: assetMetrics.files,
      bytes: assetMetrics.bytes,
      copiedFiles: assetPaths.length,
      manifests: shards.size,
      manifestBytes,
    },
    limits: { fileBytes: FILE_LIMIT, fileCount: FILE_COUNT_LIMIT },
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { dist, destination, parent, base } = await resolvePaths(args.dist, args.destination);

  const staging = path.join(parent, `.${base}.staging-${process.pid}-${randomBytes(6).toString("hex")}`);
  await fsp.mkdir(staging);
  let cleaned = false;
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    fs.rmSync(staging, { recursive: true, force: true });
  };
  const onSignal = (signal) => {
    cleanup();
    process.exit(signal === "SIGINT" ? 130 : 143);
  };
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, onSignal);

  try {
    const metrics = await stage({ dist, staging, noindex: args.noindex });
    if (await lstatOrNull(destination)) throw new Error(`Destination appeared while staging: ${destination}`);
    await fsp.rename(staging, destination);
    cleaned = true;
    process.stdout.write(`${JSON.stringify({ release: destination, ...metrics }, null, 2)}\n`);
  } catch (error) {
    cleanup();
    throw error;
  }
}

main().catch((error) => {
  if (error instanceof UsageError) {
    process.stderr.write(`${error.message}\n${USAGE}\n`);
    process.exitCode = 2;
  } else {
    process.stderr.write(`stage-site-release: ${error.message}\n`);
    process.exitCode = 1;
  }
});
