// What a deployment was built from, for a person to read at /bundle-manifest.json and in the
// deploy log: the bundle's version and manifest, how many pairs it holds, and the launch
// measure, the distinct trials the pair pages show over the trials the lab fetched
// (`coverage.trials_fetched` in the manifest). A manifest without that count states no
// measure: the file says so rather than guess one.
import fs from "node:fs";
import path from "node:path";

/**
 * @param {string} folder a bundle folder, with its manifest.json
 */
export function bundleFacts(folder) {
  const manifest = JSON.parse(fs.readFileSync(path.join(folder, "manifest.json"), "utf8"));
  // The version is the checksum's first 16 hexadecimal digits, as the loader and the build name it.
  const version = /^sha256:([0-9a-f]{16})/.exec(manifest.checksum)?.[1];
  if (!version) throw new Error(`${folder}/manifest.json has no sha256 checksum`);
  const pages = path.join(folder, "p12_pair_page");
  const trials = new Set();
  let pairs = 0;
  for (const name of fs.readdirSync(pages).filter((one) => one.endsWith(".json"))) {
    pairs += 1;
    for (const trial of JSON.parse(fs.readFileSync(path.join(pages, name), "utf8")).trials ?? []) trials.add(trial.nct_id);
  }
  const fetched = manifest.coverage?.trials_fetched ?? null;
  return {
    version,
    made_at: manifest.made_at,
    lab_commit: manifest.lab_commit ?? null,
    counts: manifest.counts,
    pairs,
    trials_on_pages: trials.size,
    trials_fetched: fetched,
    launch_measure: fetched ? Number((trials.size / fetched).toFixed(4)) : null,
  };
}

/** One line for a log: the pairs, and the launch measure or why there is none. */
export function factsLine(facts) {
  const measure = facts.launch_measure === null
    ? "no launch measure: the manifest gives no coverage.trials_fetched"
    : `launch measure ${(facts.launch_measure * 100).toFixed(1)}% (${facts.trials_on_pages.toLocaleString("en-GB")} distinct trials on pages of ${facts.trials_fetched.toLocaleString("en-GB")} fetched)`;
  return `Bundle ${facts.version}: ${facts.pairs.toLocaleString("en-GB")} pairs, lab commit ${facts.lab_commit ?? "not given"}; ${measure}.`;
}
