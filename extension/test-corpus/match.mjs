// For each address in urls.csv: what kind of address the site takes it for, and whether
// the published lookup.json tracks it. Writes .work/match.json.
// LOOKUP_JSON overrides where lookup.json is read from (default: the public site).
import { readFileSync, writeFileSync } from "node:fs";
import { readAddress, closestClaims } from "../../site/src/lib/lookup-match.mjs";
import { readRows } from "./rows.mjs";

const here = new URL(".", import.meta.url).pathname;
const source = process.env.LOOKUP_JSON ?? "https://whatcameofit.com/lookup.json";
const index = source.startsWith("http")
  ? await fetch(source).then((response) => response.json())
  : JSON.parse(readFileSync(source, "utf8"));

const out = {};
for (const row of readRows(`${here}urls.csv`)) {
  const read = readAddress(row.url);
  const { key: articleKey } = read;
  const article = read.kind === "article" ? index.articles[articleKey] : undefined;
  const slug = article ? (Array.isArray(article) ? article[0] : article) : "";
  out[row.url] = {
    address_kind: read.kind,
    platform: read.platform ?? "",
    server_can_read_post: read.kind === "post" ? read.readable : null,
    tracked_slug: slug,
    closest_claim: slug ? "" : (closestClaims(index, row.url, 1)[0]?.slug ?? ""),
  };
}
writeFileSync(`${here}.work/match.json`, JSON.stringify(out, null, 1));
const rows = Object.values(out);
console.log(`matched ${rows.length} addresses against ${source}: ${rows.filter((r) => r.tracked_slug).length} tracked`);
