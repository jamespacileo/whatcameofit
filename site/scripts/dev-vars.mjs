// Writes site/.dev.vars for `wrangler dev` from the repository's .env: only the
// settings the lookup service reads. The file is ignored by git. Nothing is printed
// but the names that were found.
import fs from "node:fs";
import path from "node:path";

const WANTED = ["OPENAI_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "CONTACT_EMAIL", "DECISION_BACKEND", "DECISIONS_MODEL"];
const root = path.resolve(import.meta.dirname, "../..");
const source = path.join(root, ".env");

if (!fs.existsSync(source)) {
  console.error(`No ${source}. Copy .env.example to .env and fill it in first.`);
  process.exit(1);
}

const found = new Map();
for (const line of fs.readFileSync(source, "utf8").split(/\r?\n/)) {
  const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
  if (match && WANTED.includes(match[1]) && match[2]) {
    found.set(match[1], match[2].replace(/^(["'])(.*)\1$/, "$2"));
  }
}

const lines = [...found].map(([name, value]) => `${name}=${JSON.stringify(value)}`);
fs.writeFileSync(path.join(root, "site/.dev.vars"), `${lines.join("\n")}\n`, { mode: 0o600 });
console.log(`Wrote site/.dev.vars with: ${[...found.keys()].join(", ") || "nothing"}.`);
const missing = ["OPENAI_API_KEY", "LLM_MODEL", "CONTACT_EMAIL"].filter((name) => !found.has(name));
if (missing.length > 0) {
  console.error(`Missing from .env: ${missing.join(", ")}. The lookup will answer "not set up".`);
}
