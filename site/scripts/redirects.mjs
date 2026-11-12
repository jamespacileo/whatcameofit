// Runs after every build. Keeps every topic address that was ever published working.
//
// The export lists vertical slugs retired after launch, each with its successor; each
// becomes a permanent redirect in dist/_redirects, which Cloudflare serves before the
// files. `make deploy` records the topic slugs it published in data/published-topics.json.
// A slug recorded there that is neither a current topic nor retired would leave a
// published address broken, so the build fails and names it.
import fs from "node:fs";
import path from "node:path";

const DIST = path.resolve(process.env.DIST_DIR ?? "dist");

function exportPath() {
  if (process.env.EXPORT_FILE) return path.resolve(process.env.EXPORT_FILE);
  const live = path.resolve("data/export.json");
  return fs.existsSync(live) ? live : path.resolve("data/seed-export.json");
}

const data = JSON.parse(fs.readFileSync(exportPath(), "utf8"));
const current = new Set(data.verticals.map((vertical) => vertical.slug));
const retired = new Map((data.retired_verticals ?? []).map((entry) => [entry.slug, entry.successor]));

const recordFile = path.resolve(process.env.PUBLISHED_TOPICS_FILE ?? "data/published-topics.json");
const published = fs.existsSync(recordFile) ? JSON.parse(fs.readFileSync(recordFile, "utf8")) : [];
const lost = published.filter((slug) => !current.has(slug) && !retired.has(slug));
if (lost.length > 0) {
  console.error(
    `Redirect check failed: these published topics are neither current nor retired: ${lost.join(", ")}.` +
      " Record each with its successor in RETIRED_VERTICALS (pipeline/src/thenwhat/claims/verticals.py) and export again.",
  );
  process.exit(1);
}

const lines = [...retired].map(([slug, successor]) => `/topic/${slug} /topic/${successor} 301`);
const file = path.join(DIST, "_redirects");
if (lines.length > 0) fs.writeFileSync(file, `${lines.join("\n")}\n`);
else fs.rmSync(file, { force: true });
console.log(`Redirect check passed: ${lines.length} retired topic ${lines.length === 1 ? "address" : "addresses"}.`);
