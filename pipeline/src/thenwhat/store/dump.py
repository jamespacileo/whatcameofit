"""A store file as data-only SQL that D1's import takes into a database already holding
the schema (`store/ingest/migrations/0001_store_schema.sql`), and a manifest to check the
load against.

D1's import (`wrangler d1 execute <db> --remote --file`, read 2026-11-17, docs/sources.md):
no `BEGIN`/`COMMIT` in the file; a statement is at most 100,000 bytes; a file at most
5 GB; a row at most 2,000,000 bytes; tables must be loaded parents first, or foreign keys
deferred with `PRAGMA defer_foreign_keys = true`. So each file begins with that pragma,
tables go parents first, rows go as multi-row INSERTs under `STATEMENT_BYTES`, and files
are cut at `FILE_BYTES`.

Rows keep their ids, so what references them still does. Generated columns are not
written: the schema computes them. The full-text indexes are not dumped: the two that
read their table's own columns are filled by the schema's triggers as the rows go in and
rebuilt by a last file each; the claims' index, which keeps its own words, is written
again by a last file as the merge writes it.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Under D1's 100,000 bytes a statement, with room for the INSERT's head.
STATEMENT_BYTES = 90_000
# A file of the import. D1 takes 5 GB; smaller files are quicker to retry.
FILE_BYTES = 50_000_000
# Tables the dump never writes: SQLite's and D1's own, the staging of runs, and the
# full-text indexes with their shadow tables.
SKIPPED_PREFIXES = ("sqlite_", "_cf_", "d1_")
STAGING = frozenset({"stg"})
FTS_REBUILT = ("registry_trial_fts", "link_lead_fts")
CLAIM_FTS = """DELETE FROM claim_fts;
INSERT INTO claim_fts (rowid, headline, indication, names)
SELECT c.id, c.headline, c.indication,
       (SELECT group_concat(e.name || ' ' || (SELECT coalesce(group_concat(j.value, ' '), '')
                                              FROM json_each(e.synonyms) j), ' ')
        FROM entity e WHERE e.claim_id = c.id AND e.type = 'intervention')
FROM claim c;
"""
HEAD = "PRAGMA defer_foreign_keys = true;\n"


class DumpRefused(Exception):
    """A row cannot go into one statement D1 accepts."""


@dataclass
class Manifest:
    """What a load must hold: rows by table, and each file with its checksum."""

    tables: dict[str, int] = field(default_factory=dict)
    files: list[dict[str, Any]] = field(default_factory=list)
    store_sha256: str = ""
    payload_objects: int = 0

    def write(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "store_sha256": self.store_sha256,
                    "tables": self.tables,
                    "files": self.files,
                    "payload_objects": self.payload_objects,
                },
                indent=2,
            )
            + "\n"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tables_in_order(db: sqlite3.Connection) -> list[str]:
    """The store's own tables, each after every table it references."""
    names = [
        name
        for (name,) in db.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND sql NOT LIKE 'CREATE VIRTUAL%'"
            " ORDER BY name"
        )
        if not name.startswith(SKIPPED_PREFIXES) and name not in STAGING and "_fts" not in name
    ]
    parents = {
        name: {row[2] for row in db.execute(f"PRAGMA foreign_key_list({name})") if row[2] != name}
        for name in names
    }
    ordered: list[str] = []
    while len(ordered) < len(names):
        ready = [n for n in names if n not in ordered and parents[n] <= set(ordered)]
        if not ready:
            raise DumpRefused(f"The store's tables reference each other in a cycle: {parents}")
        ordered.extend(ready)
    return ordered


def literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, bytes):
        return f"X'{value.hex()}'"
    return "'" + str(value).replace("'", "''") + "'"


def _statements(db: sqlite3.Connection, table: str) -> Iterator[tuple[str, int]]:
    """A table's rows as INSERTs of several rows each, under `STATEMENT_BYTES`."""
    columns = [row[1] for row in db.execute(f"PRAGMA table_xinfo({table})") if row[6] == 0]
    head = f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n"
    order = (
        "rowid"
        if db.execute(
            "SELECT sql NOT LIKE '%WITHOUT ROWID%' FROM sqlite_schema WHERE name = ?", (table,)
        ).fetchone()[0]
        else "1"
    )
    rows: list[str] = []
    size = len(head)
    for values in db.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order}"):
        text = "(" + ", ".join(literal(value) for value in values) + ")"
        if len(head) + len(text.encode()) + 2 > STATEMENT_BYTES:
            raise DumpRefused(
                f"A row of {table} is {len(text.encode()):,} bytes as SQL; D1 takes a statement"
                f" of at most {STATEMENT_BYTES:,}."
            )
        if rows and size + len(text.encode()) + 2 > STATEMENT_BYTES:
            yield head + ",\n".join(rows) + ";\n", len(rows)
            rows, size = [], len(head)
        rows.append(text)
        size += len(text.encode()) + 2
    if rows:
        yield head + ",\n".join(rows) + ";\n", len(rows)


class _Files:
    """Numbered SQL files, each opening with `HEAD` and cut at `FILE_BYTES`."""

    def __init__(self, out: Path, manifest: Manifest) -> None:
        self.out, self.manifest = out, manifest
        self.number, self.written = 0, 0
        self.path: Path | None = None
        self.text: list[str] = []

    def start(self, label: str) -> None:
        self.close()
        self.number += 1
        self.path = self.out / f"{self.number:04d}_{label}.sql"
        self.text, self.written = [HEAD], len(HEAD)

    def write(self, statement: str, label: str) -> None:
        size = len(statement.encode())
        if self.path is None or self.written + size > FILE_BYTES:
            self.start(label)
        self.text.append(statement)
        self.written += size

    def close(self) -> None:
        if self.path is None:
            return
        self.path.write_text("".join(self.text), encoding="utf-8")
        self.manifest.files.append(
            {
                "name": self.path.name,
                "bytes": self.path.stat().st_size,
                "sha256": _sha256(self.path),
            }
        )
        self.path, self.text = None, []


def dump(store: Path, out: Path, *, payloads: Path | None = None) -> Manifest:
    """Write `store` as numbered SQL files in `out`, and `manifest.json` beside them. Any
    SQL files already in `out` are removed first."""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.sql"):
        old.unlink()
    manifest = Manifest(store_sha256=_sha256(store))
    if payloads is not None and payloads.is_dir():
        manifest.payload_objects = sum(1 for p in payloads.rglob("*") if p.is_file())
    files = _Files(out, manifest)
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    try:
        for table in tables_in_order(db):
            manifest.tables[table] = db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if not manifest.tables[table]:
                continue
            files.start(table)
            for statement, _ in _statements(db, table):
                files.write(statement, table)
        files.start("claim_fts")
        files.write(CLAIM_FTS, "claim_fts")
        for index in FTS_REBUILT:
            files.start(index)
            files.write(f"INSERT INTO {index} ({index}) VALUES ('rebuild');\n", index)
        files.close()
    finally:
        db.close()
    manifest.tables["claim_fts"] = manifest.tables.get("claim", 0)
    manifest.write(out / "manifest.json")
    return manifest


def count_query(manifest: dict[str, Any]) -> str:
    """One SELECT of every table's count, one column a table, to run on the loaded D1."""
    return (
        "SELECT "
        + ", ".join(f"(SELECT count(*) FROM {table}) AS {table}" for table in manifest["tables"])
        + ";"
    )


def counts_of(answer: Any) -> dict[str, int]:
    """The counts from `wrangler d1 execute --json`'s answer, or from a plain object."""
    if isinstance(answer, list):
        answer = answer[0]
    if isinstance(answer, dict) and "results" in answer:
        answer = answer["results"][0]
    return {str(table): int(count) for table, count in dict(answer).items()}


def differences(manifest: dict[str, Any], counts: dict[str, int]) -> list[str]:
    """Each table whose loaded count is not the manifest's, in words."""
    return [
        f"{table}: {expected:,} in the store file, {counts.get(table, 'none')} loaded"
        for table, expected in manifest["tables"].items()
        if counts.get(table) != expected
    ]
