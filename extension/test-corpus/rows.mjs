// Reads urls.csv: quoted fields, commas and newlines inside quotes.
import { readFileSync } from "node:fs";

export function readRows(path) {
  const text = readFileSync(path, "utf8");
  const records = [];
  let field = "";
  let record = [];
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { record.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i += 1;
      record.push(field); field = "";
      if (record.some((value) => value !== "")) records.push(record);
      record = [];
    } else field += c;
  }
  if (field || record.length) { record.push(field); records.push(record); }
  const [header, ...rest] = records;
  return rest.map((values) => Object.fromEntries(header.map((name, i) => [name, values[i] ?? ""])));
}
