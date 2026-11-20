// The one comment a pull request carries about its preview: where it is, the pages
// worth opening, how many pairs it holds, and where the build came from.
// The workflow edits the same comment on every run; MARKER is how it finds it.
//
//   STATE=published PREVIEW_URL=https://... PR_NUMBER=12 node scripts/pr-preview-comment.mjs
//
// Prints Markdown. previewComment is pure: no files, no network.
import path from "node:path";

import { pullRequestWorker } from "./deploy-checks.mjs";

export const MARKER = "<!-- thenwhat-pr-preview -->";

const PAGES = [
  ["Home", "/"],
  ["Topics", "/topics"],
  ["How it works", "/how-it-works"],
  ["Guide", "/guide"],
  ["Open data", "/data"],
  ["About", "/about"],
];
const FILES = [
  ["lookup.json", "/lookup.json"],
  ["sitemap.xml", "/sitemap.xml"],
  ["changes.xml", "/changes.xml"],
  ["robots.txt", "/robots.txt"],
];

const links = (url, pairs) => pairs.map(([name, at]) => `[${name}](${url}${at})`).join(" · ");

/**
 * @param {{ state: "published" | "failed", url?: string, worker: string, sha?: string,
 *   repoUrl?: string, runUrl?: string, accountId?: string,
 *   pairs?: { count: number, version?: string } | null, at?: Date }} build
 */
export function previewComment({ state, url, worker, sha, repoUrl, runUrl, accountId, pairs, at }) {
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
  const dashboard = accountId
    ? `[Worker \`${worker}\`](https://dash.cloudflare.com/${accountId}/workers/services/view/${worker}/production)`
    : `Worker \`${worker}\``;
  const counted = pairs
    ? `${pairs.count} ${pairs.count === 1 ? "pair" : "pairs"}${pairs.version ? ` from bundle \`${pairs.version}\`` : ""}`
    : null;
  const facts = [`Built from ${commit}`, log, dashboard, counted, when].filter(Boolean);
  lines.push(
    "",
    `<sub>${facts.join(" · ")}</sub>`,
    "<sub>Replaced on every push and deleted when this pull request closes. Not indexed, and without the registry search.</sub>",
  );
  return lines.join("\n");
}

if (import.meta.filename === path.resolve(process.argv[1] ?? "")) {
  const env = process.env;
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
      // Set by pr-preview.mjs from the bundle the copy was built from.
      pairs: /^\d+$/.test(env.PAIRS_COUNT ?? "") ? { count: Number(env.PAIRS_COUNT), version: env.PAIRS_VERSION || undefined } : null,
      at: new Date(),
    }),
  );
}
