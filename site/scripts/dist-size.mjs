// The size every built file must stay under. The host refuses one over 25 MiB, so a deploy
// would fail; the build stops at 20 MiB instead, naming the file. Openspec open-data:
// "No built file near the host's limit".
import fs from "node:fs";
import path from "node:path";

export const FILE_LIMIT = 20 * 2 ** 20;

/** Every file under the directory larger than the limit, by path relative to it, largest first. */
export function oversizedFiles(directory, limit = FILE_LIMIT) {
  const found = [];
  const walk = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile()) {
        const { size } = fs.statSync(full);
        if (size > limit) found.push({ file: path.relative(directory, full), bytes: size });
      }
    }
  };
  walk(directory);
  return found.sort((a, b) => b.bytes - a.bytes);
}
