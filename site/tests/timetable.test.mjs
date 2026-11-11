// A year's records as lines: one line per source, with its dated steps.
import assert from "node:assert/strict";
import { test } from "node:test";
import { recordedLines } from "../src/lib/timetable.ts";

const event = (date, sourceUrl) => ({
  kind: "event",
  date,
  mark: date,
  explains: false,
  event: { source_url: sourceUrl },
});
const report = (date) => ({ kind: "report", date, outlet: "", title: "", url: "", archiveUrl: null });

test("records that share a source become one line, placed at its first step", () => {
  const lines = recordedLines([
    event("2024-01-05", "https://registry.example/a"),
    report("2024-02-01"),
    event("2024-03-01", "https://registry.example/b"),
    event("2024-06-09", "https://registry.example/a"),
  ]);
  assert.deepEqual(
    lines.map((line) => (line.kind === "report" ? "report" : line.steps.map((step) => step.date))),
    [["2024-01-05", "2024-06-09"], "report", ["2024-03-01"]],
  );
  assert.equal(lines[0].sourceUrl, "https://registry.example/a");
});
