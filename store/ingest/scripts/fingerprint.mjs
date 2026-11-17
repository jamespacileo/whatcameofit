// The scripts' own checksum of a table, made of SQLite's core functions only, since D1
// has no SHA. D1 refuses a result of more than 100 columns ("too many columns in result
// set", seen on the preview on 2026-11-17; the local engine does not), so a table's
// columns are spread over statements of at most 90 result columns each.
export const MAX_RESULT_COLUMNS = 90;
const quote = (name) => `"${name.replaceAll('"', '""')}"`;
const M = 1000000007;
const weights = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59];

// The three figures of one column: every one an integer under 2^53.
function figures(column) {
  const c = quote(column), text = `CAST(${c} AS TEXT)`, hex = `hex(CAST(${c} AS BLOB))`;
  // How often each of the sixteen hex digits occurs in the value, weighted: every byte counts.
  const digits = weights.map((weight, digit) => `${weight} * (length(${hex}) - length(replace(${hex}, '${digit.toString(16).toUpperCase()}', '')))`).join(" + ");
  return [`count(${c}) AS ${quote(`${column} set`)}`,
    `coalesce(sum(length(CAST(${c} AS BLOB))), 0) AS ${quote(`${column} bytes`)}`,
    `coalesce(sum((${digits} + coalesce(unicode(substr(${text}, 1, 1)), 0) * 61 + coalesce(unicode(substr(${text}, length(${text}) / 2 + 1, 1)), 0) * 131 + coalesce(unicode(substr(${text}, -1, 1)), 0) * 67) % ${M}) % ${M}, 0) AS ${quote(`${column} sum`)}`];
}

// A table's statements: each begins with its rows, then as many columns' figures as fit.
export function fingerprint(table, columns) {
  const each = Math.floor((MAX_RESULT_COLUMNS - 1) / 3), parts = [];
  for (let at = 0; at < Math.max(columns.length, 1); at += each) {
    parts.push(`SELECT ${[`count(*) AS "rows"`, ...columns.slice(at, at + each).flatMap(figures)].join(", ")} FROM ${quote(table)}`);
  }
  return parts;
}
