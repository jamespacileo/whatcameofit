// One Worker deployment selects both its static files and the manifest for the
// offloaded files. Upload and verify every referenced object before that selection.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function releaseSettings(preview = false) {
  const prefix = preview ? "PREVIEW_SITE_FILES" : "SITE_FILES";
  const bucket = process.env[`${prefix}_BUCKET`];
  if (!bucket) return null;
  const remote = process.env[`${prefix}_REMOTE`];
  const jurisdiction = process.env[`${prefix}_JURISDICTION`];
  if (!/^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(bucket)) throw new Error(`Invalid ${prefix}_BUCKET.`);
  if (remote && !/^[\w-]+$/.test(remote)) throw new Error(`Invalid ${prefix}_REMOTE.`);
  if (preview && bucket === process.env.SITE_FILES_BUCKET) throw new Error("Give previews a separate site files bucket.");
  return { bucket, remote, jurisdiction, prefix };
}

export function prepareSiteRelease({ settings, siteDir, dist, noindex, dryRun, run }) {
  if (!dryRun && !settings.remote) {
    throw new Error(`Set ${settings.prefix}_REMOTE to the configured rclone remote for the site files bucket.`);
  }
  const base = process.env.SITE_FILES_STAGE_DIR ?? os.tmpdir();
  const scratch = fs.mkdtempSync(path.join(base, "thenwhat-site-release-"));
  process.once("exit", () => fs.rmSync(scratch, { force: true, recursive: true }));
  const release = path.join(scratch, "release");
  run(process.execPath, [
    path.join(siteDir, "scripts/stage-site-release.mjs"),
    dist,
    release,
    ...(noindex ? ["--noindex"] : []),
  ]);

  const original = path.join(siteDir, noindex ? "wrangler.preview.jsonc" : "wrangler.jsonc");
  // The two checked-in configurations use whole-line comments.
  const config = JSON.parse(fs.readFileSync(original, "utf8").replace(/^[ \t]*\/\/.*$/gm, ""));
  config.main = path.resolve(siteDir, config.main);
  config.assets.directory = path.join(release, "assets");
  config.assets.run_worker_first = config.assets.run_worker_first.filter((rule) => rule !== "!/pagefind/*");
  config.r2_buckets = [
    ...(config.r2_buckets ?? []),
    { binding: "SITE_FILES", bucket_name: settings.bucket, jurisdiction: settings.jurisdiction },
  ];
  const configPath = path.join(scratch, "wrangler.json");
  fs.writeFileSync(configPath, JSON.stringify(config));

  if (!dryRun) {
    const files = path.join(release, "objects/site-files/v1");
    const destination = `${settings.remote}:${settings.bucket}/site-files/v1`;
    run("rclone", ["copy", "--checksum", "--immutable", files, destination]);
    run("rclone", ["check", "--one-way", files, destination]);
  }
  return configPath;
}
