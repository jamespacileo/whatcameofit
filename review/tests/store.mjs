// A local D1 made the way a deployed store is: every migration of store/ingest/migrations, in
// order. D1 takes one statement at a time, so each file is split at the semicolons that end a
// statement, keeping a trigger's body (BEGIN ... END;) whole.
import fs from "node:fs";
import path from "node:path";

export const MIGRATIONS = "../store/ingest/migrations";

/** A line without its comment: `--` starts one only outside a quoted string ('*--*' is a GLOB). */
function uncommented(line) {
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    if (line[i] === "'") quoted = !quoted;
    else if (!quoted && line[i] === "-" && line[i + 1] === "-") return line.slice(0, i);
  }
  return line;
}

export function statementsOf(text) {
  const lines = text.split("\n").map(uncommented).filter((line) => line.trim());
  const out = [];
  let buffer = [];
  for (const line of lines) {
    buffer.push(line);
    const joined = buffer.join("\n").trim();
    const trigger = /^CREATE TRIGGER/i.test(joined);
    if (trigger ? /^\s*END;\s*$/i.test(line) : /;\s*$/.test(line)) {
      out.push(joined.replace(/;\s*$/, ""));
      buffer = [];
    }
  }
  if (buffer.join("").trim()) out.push(buffer.join("\n").trim());
  return out;
}

/** Applies migrations up to and including `through` (a file name prefix such as "0011"). */
export async function migrate(db, { through = "9999", only } = {}) {
  const files = fs.readdirSync(MIGRATIONS).filter((name) => name.endsWith(".sql")).sort()
    .filter((name) => name.slice(0, 4) <= through && (!only || only.includes(name.slice(0, 4))));
  for (const file of files) {
    for (const sql of statementsOf(fs.readFileSync(path.join(MIGRATIONS, file), "utf8"))) await db.prepare(sql).run();
  }
  return files;
}
