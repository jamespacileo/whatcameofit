// Freeze an explicitly reviewed export for GitHub, without giving CI database access.
import fs from "node:fs";
import path from "node:path";
import { deployProblems } from "./deploy-checks.mjs";

const [source, destination] = process.argv.slice(2);
if (!source || !destination) {
  console.error("Usage: node stage-public-export.mjs SOURCE DESTINATION");
  process.exit(1);
}
let temporary;
try {
  const data = JSON.parse(fs.readFileSync(source, "utf8"));
  const problems = deployProblems({ data, siteUrl: process.env.SITE_URL || "https://whatcameofit.com" });
  if (problems.length) throw new Error(problems.join("\n"));
  fs.mkdirSync(path.dirname(path.resolve(destination)), { recursive: true });
  temporary = `${destination}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(data, null, 2)}\n`, { flag: "wx" });
  fs.renameSync(temporary, destination);
  console.log(`Staged ${data.claims.length} reviewed claims in ${destination}. Commit this file to publish them.`);
} catch (error) {
  if (temporary && fs.existsSync(temporary)) fs.unlinkSync(temporary);
  console.error(`Public snapshot unchanged: ${error.message}`);
  process.exit(1);
}
