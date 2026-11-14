// Freeze a publishable export for GitHub, without giving CI database access.
import fs from "node:fs";
import path from "node:path";
import { SITE } from "../site.config.mjs";
import { deployProblems } from "./deploy-checks.mjs";

const [source, destination, historyFile] = process.argv.slice(2);
if (!source || !destination) {
  console.error("Usage: node stage-public-export.mjs SOURCE DESTINATION [TOPIC_HISTORY]");
  process.exit(1);
}
let temporary;
try {
  const data = JSON.parse(fs.readFileSync(source, "utf8"));
  const problems = deployProblems({ data, siteUrl: SITE.url });
  if (problems.length) throw new Error(problems.join("\n"));
  if (historyFile) {
    const before = fs.existsSync(historyFile) ? JSON.parse(fs.readFileSync(historyFile, "utf8")) : [];
    const topics = [...new Set([...before, ...data.verticals.map(vertical => vertical.slug)])].sort();
    // Record history first: a failed snapshot write may reserve an extra address,
    // but can never lose the redirect protection for a previously published one.
    fs.mkdirSync(path.dirname(path.resolve(historyFile)), { recursive: true });
    temporary = `${historyFile}.${process.pid}.tmp`;
    fs.writeFileSync(temporary, `${JSON.stringify(topics, null, 2)}\n`, { flag: "wx" });
    fs.renameSync(temporary, historyFile);
  }
  fs.mkdirSync(path.dirname(path.resolve(destination)), { recursive: true });
  temporary = `${destination}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(data, null, 2)}\n`, { flag: "wx" });
  fs.renameSync(temporary, destination);
  const unchecked = data.claims.filter((claim) => !claim.checked_by_person).length;
  console.log(`Staged ${data.claims.length} claims (${unchecked} not checked by a person) in ${destination}. Commit this file to publish them.`);
} catch (error) {
  if (temporary && fs.existsSync(temporary)) fs.unlinkSync(temporary);
  console.error(`Public snapshot unchanged: ${error.message}`);
  process.exit(1);
}
