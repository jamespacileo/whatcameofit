// One name for everything that decides what a pull request's copy of the site serves:
// the files the build and the Worker are made from, and the settings they are given.
// Two commits with the same key publish the same copy, so the second need not be
// built or sent again. Behaviour: openspec delivery-time.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import path from "node:path";

// Settings the build or the Worker reads. A new one must be added here, or a copy
// built with the old value would be taken for the new.
export const SETTINGS = [
  "SITE_URL",
  "LOOKUP_URL",
  "SUGGEST_URL",
  "CORRECTIONS_URL",
  "CHROME_STORE_URL",
  "SAFARI_STORE_URL",
  "PUBLIC_BUILD",
  "EXPORT_FILE",
  "PUBLISHED_TOPICS_FILE",
  "CONTACT_EMAIL",
  "PREVIEW_SITE_FILES_BUCKET",
  "PREVIEW_SITE_FILES_JURISDICTION",
];

// Files under site/ that no copy is made from: the tests and the notes.
const UNREAD = /^site\/(tests\/|README\.md$|AGENTS\.md$|Dockerfile$|\.dockerignore$|\.vscode\/|\.impeccable)/;

/**
 * Pure: no files, no network.
 * @param {{ path: string, blob: string }[]} files every tracked file under site/ with its git blob id
 * @param {Record<string, string | undefined>} settings
 */
export function keyFrom(files, settings) {
  const hash = createHash("sha256");
  for (const file of files.filter((file) => !UNREAD.test(file.path)).sort((a, b) => (a.path < b.path ? -1 : 1))) {
    hash.update(`${file.path}\0${file.blob}\n`);
  }
  for (const name of SETTINGS) hash.update(`${name}=${settings[name] ?? ""}\n`);
  return hash.digest("hex");
}

/**
 * The key of the checked-out commit, or null when it cannot be known: outside a git
 * checkout, or with uncommitted changes under site/. With no key, everything is built.
 */
export function buildKey(siteDir, settings) {
  const git = (...args) => spawnSync("git", args, { cwd: siteDir, encoding: "utf8", maxBuffer: 64 << 20 });
  const changed = git("status", "--porcelain", "--", ".");
  if (changed.status !== 0 || changed.stdout.trim() !== "") return null;
  const listed = git("ls-tree", "-r", "--full-tree", "HEAD", "--", "site");
  if (listed.status !== 0) return null;
  const files = listed.stdout
    .split("\n")
    .filter(Boolean)
    .map((line) => {
      const [meta, file] = line.split("\t");
      return { path: file, blob: meta.split(" ")[2] };
    });
  if (files.length === 0) return null;
  // The export is named by where it is, not by where this machine keeps the checkout.
  const exportFile = settings.EXPORT_FILE ? path.relative(siteDir, path.resolve(siteDir, settings.EXPORT_FILE)) : "";
  return keyFrom(files, { ...settings, EXPORT_FILE: exportFile });
}
