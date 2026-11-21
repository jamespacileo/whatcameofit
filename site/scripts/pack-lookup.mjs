import { readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { gzipSync } from "node:zlib";
import { LEGACY_LOOKUP, PACKED_LOOKUP } from "../src/lib/lookup-assets.mjs";
import { FILE_LIMIT } from "./dist-size.mjs";

/** Keep the original response bytes while staying below the limit for an uploaded asset. */
export function packLookup(dist, limit = FILE_LIMIT) {
  const source = join(dist, LEGACY_LOOKUP);
  if (statSync(source).size <= limit) return;
  const packed = gzipSync(readFileSync(source));
  if (packed.length > limit) throw new Error(`Compressed ${LEGACY_LOOKUP} still exceeds the asset limit`);
  writeFileSync(join(dist, PACKED_LOOKUP), packed);
  unlinkSync(source);
}

if (import.meta.main) packLookup(resolve(process.env.DIST_DIR ?? "dist"));
