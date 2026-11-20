// A copy of tests/bundle in the shape the lab writes after its pull requests 125 and 126, for the
// tests that hold the site to both shapes until a recut fixture replaces tests/bundle:
// - `PairRow.claim_slugs`, every published claim's slug that reaches the pair (125);
// - `TrialEvent.shown_on`, the day of the record that shows the event, and `update_key` named
//   only when the lab kept that update, else null (126).
// The schemas are changed as the lab's models generate them; the files as the lab writes them.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";

const FIXTURE = fileURLToPath(new URL("./bundle", import.meta.url));

/** Every object in a parsed file, depth first. */
function* objects(value) {
  if (Array.isArray(value)) for (const item of value) yield* objects(item);
  else if (value && typeof value === "object") {
    yield value;
    for (const item of Object.values(value)) yield* objects(item);
  }
}

const isEvent = (value) => ["key", "nct_id", "kind", "day", "day_basis", "phases", "update_key"].every((name) => name in value);
const isRow = (value) => ["pair", "intervention", "condition", "descriptor", "status", "filing", "origin"].every((name) => name in value);

function reshapeSchema(schema) {
  const event = schema.$defs?.TrialEvent;
  if (event) {
    event.properties.shown_on = { format: "date", title: "Shown On", type: "string" };
    event.properties.update_key = { anyOf: [{ type: "string" }, { type: "null" }], title: "Update Key" };
    event.required = [...event.required, "shown_on"];
  }
  const row = schema.$defs?.PairRow;
  if (row) row.properties.claim_slugs = { default: [], items: { type: "string" }, title: "Claim Slugs", type: "array" };
  return schema;
}

/**
 * The fixture in the new shape. An event's `shown_on` is its update's day. Each row's `claim_slugs` is its origin's slug, as the lab writes
 * for a claim whose own pair is tracked; every other event's update is one the lab did not keep.
 * @param {(page: Record<string, any>, address: string) => void} [change] applied to each pair page after
 */
export function labShapeCopy(change = () => {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-lab-shape-"));
  fs.cpSync(FIXTURE, dir, { recursive: true });
  for (const name of fs.readdirSync(path.join(dir, "schemas"))) {
    const file = path.join(dir, "schemas", name);
    fs.writeFileSync(file, JSON.stringify(reshapeSchema(JSON.parse(fs.readFileSync(file, "utf8")))));
  }
  for (const folder of fs.readdirSync(dir).filter((name) => name.startsWith("p12_"))) {
    for (const name of fs.readdirSync(path.join(dir, folder))) {
      const file = path.join(dir, folder, name);
      const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
      let index = 0;
      for (const value of objects(parsed)) {
        if (isEvent(value)) {
          // The day of the record that shows it: the kept update's day, which is often later
          // than the event itself, as NCT03921528's 2019 event shows in its 2024 record.
          value.shown_on = value.update_key?.split("@")[1] ?? value.day;
          if (index++ % 2) value.update_key = null;
        }
        if (isRow(value)) value.claim_slugs = value.origin ? [value.origin.claim_slug] : [];
      }
      if (folder === "p12_pair_page") change(parsed, name.slice(0, -5));
      fs.writeFileSync(file, JSON.stringify(parsed));
    }
  }
  fs.rmSync(path.join(dir, "manifest.json"));
  writeManifest(dir, { madeAt: "2026-11-20T00:00:00Z" });
  return dir;
}
