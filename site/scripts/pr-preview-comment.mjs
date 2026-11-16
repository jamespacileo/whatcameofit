// The one comment a pull request carries about its preview: where it is, the pages
// worth opening, the claims the pull request adds, and where the build came from.
// The workflow edits the same comment on every run; MARKER is how it finds it.
//
//   STATE=published PREVIEW_URL=https://... PR_NUMBER=12 node scripts/pr-preview-comment.mjs
//
// Prints Markdown. previewComment and addedClaims are pure: no files, no network.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { pullRequestWorker } from "./deploy-checks.mjs";

export const MARKER = "<!-- thenwhat-pr-preview -->";

// At most this many added claims are linked one by one; the rest are counted.
const LISTED = 10;

const PAGES = [
  ["Home", "/"],
  ["Topics", "/topics"],
  ["How it works", "/how-it-works"],
  ["Guide", "/guide"],
  ["Anniversaries", "/anniversaries"],
  ["Open data", "/data"],
  ["About", "/about"],
];
const FILES = [
  ["lookup.json", "/lookup.json"],
  ["sitemap.xml", "/sitemap.xml"],
  ["changes.xml", "/changes.xml"],
  ["robots.txt", "/robots.txt"],
];

/** Slugs of the claims `after` holds and `before` does not, in `after`'s order. */
export function addedClaims(before, after) {
  const had = new Set((before?.claims ?? []).map((claim) => claim.slug));
  return (after?.claims ?? []).map((claim) => claim.slug).filter((slug) => !had.has(slug));
}

const links = (url, pairs) => pairs.map(([name, at]) => `[${name}](${url}${at})`).join(" · ");

/**
 * @param {{ state: "published" | "failed", url?: string, worker: string, sha?: string,
 *   repoUrl?: string, runUrl?: string, accountId?: string, claims?: number,
 *   added?: string[] | null, at?: Date }} build
 */
export function previewComment({ state, url, worker, sha, repoUrl, runUrl, accountId, claims, added, at }) {
  const commit = sha ? (repoUrl ? `[\`${sha.slice(0, 7)}\`](${repoUrl}/commit/${sha})` : `\`${sha.slice(0, 7)}\``) : "this commit";
  const log = runUrl ? `[build log](${runUrl})` : null;
  const when = at ? `updated ${at.toISOString().slice(0, 16).replace("T", " ")} UTC` : null;

  if (state === "failed") {
    return [
      MARKER,
      "### Preview not updated",
      "",
      `The build of ${commit} failed${log ? `: see the ${log}` : ""}. If \`${worker}\` was published before, it still serves the earlier commit.`,
      "",
      `<sub>${[when, "The next push tries again."].filter(Boolean).join(" · ")}</sub>`,
    ].join("\n");
  }

  const lines = [MARKER, "### Preview", "", `**${url}**`, "", `**Pages:** ${links(url, PAGES)}`, "", `**Files:** ${links(url, FILES)}`];
  if (added?.length) {
    lines.push("", `**Claims this pull request adds (${added.length}):**`);
    for (const slug of added.slice(0, LISTED)) lines.push(`- [${slug}](${url}/${slug})`);
    if (added.length > LISTED) lines.push(`- and ${added.length - LISTED} more`);
  }
  const dashboard = accountId
    ? `[Worker \`${worker}\`](https://dash.cloudflare.com/${accountId}/workers/services/view/${worker}/production)`
    : `Worker \`${worker}\``;
  const facts = [`Built from ${commit}`, log, dashboard, claims ? `${claims} claims` : null, when].filter(Boolean);
  lines.push(
    "",
    `<sub>${facts.join(" · ")}</sub>`,
    "<sub>Replaced on every push and deleted when this pull request closes. Not indexed, and without the registry search.</sub>",
  );
  return lines.join("\n");
}

if (import.meta.filename === path.resolve(process.argv[1] ?? "")) {
  const env = process.env;
  const siteDir = path.resolve(import.meta.dirname, "..");
  const file = "data/published-export.json";
  let after = null;
  let added = null;
  try {
    after = JSON.parse(fs.readFileSync(path.join(siteDir, file), "utf8"));
    // In a pull request's run the checkout is the merge with the base, whose first
    // parent is the base. Anywhere that is not so, the list of added claims is left out.
    const base = spawnSync("git", ["show", `HEAD^1:site/${file}`], { cwd: siteDir, encoding: "utf8", maxBuffer: 1 << 30 });
    if (base.status === 0) added = addedClaims(JSON.parse(base.stdout), after);
  } catch {
    // The comment is still worth posting without the counts.
  }
  const repoUrl = env.GITHUB_REPOSITORY ? `${env.GITHUB_SERVER_URL ?? "https://github.com"}/${env.GITHUB_REPOSITORY}` : undefined;
  console.log(
    previewComment({
      state: env.STATE === "published" && env.PREVIEW_URL ? "published" : "failed",
      url: env.PREVIEW_URL,
      worker: pullRequestWorker(env.PR_NUMBER) ?? "the preview Worker",
      sha: env.HEAD_SHA,
      repoUrl,
      runUrl: repoUrl && env.GITHUB_RUN_ID ? `${repoUrl}/actions/runs/${env.GITHUB_RUN_ID}` : undefined,
      accountId: env.CLOUDFLARE_ACCOUNT_ID,
      claims: after?.claims?.length,
      added,
      at: new Date(),
    }),
  );
}
