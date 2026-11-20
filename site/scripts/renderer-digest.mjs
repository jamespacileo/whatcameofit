// A digest of the code that writes what the Worker makes (openspec pairs-site task 4.6e): the
// site's own modules and the Worker's, read at build by astro.config.mjs, which hands it to the
// frames (PairShell.astro, EmbedShell.astro). Every entity tag takes it in, so a change to the
// site's wording or renderers (which the bundle never carries: the bundle has codes, the site has
// the words) gives every page made on request a new tag, and no asker is told an outdated page is
// unchanged.
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const FOLDERS = ["src/lib", "worker"];

/** The first 12 bytes of the SHA-256 of every module under src/lib and worker, by path. */
export function rendererDigest() {
  const hash = createHash("sha256");
  for (const folder of FOLDERS) {
    const files = fs
      .readdirSync(path.join(SITE_DIR, folder), { recursive: true })
      .map(String)
      .filter((name) => /\.(ts|mjs|js|json)$/.test(name))
      .sort();
    for (const name of files) hash.update(`${folder}/${name}\n`).update(fs.readFileSync(path.join(SITE_DIR, folder, name)));
  }
  return hash.digest("hex").slice(0, 24);
}
