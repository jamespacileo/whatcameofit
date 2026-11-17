"""A copy of what an export reads, fetched from the truth store itself (a D1 database)
into a SQLite file of the store's schema. Reading only. Behavior: openspec truth-store,
"The two exports are compared" ("Comparing against the store itself").

D1 cannot export a database that has virtual tables, and the store has its search
tables (Cloudflare's "Import and export data", known limitations, read 2026-11-17). So
the rows are read with `wrangler d1 execute --remote --json`, one bounded page of one table at
a time, each page starting after the last row's key. Bookmarks bracket the read so a
concurrent write invalidates it. Local Wrangler can dump the selected ordinary tables in
one operation, even with search tables present elsewhere in the database.

A payload kept as an object is not in the database. One the local folder lacks is
fetched from the bucket by its key; every payload's bytes are checked against the
checksum the store names when the export reads it (`store_records.py`), so an object
from a local folder is as good as one from the bucket.

How `wrangler` is run is a function the caller may replace: tests answer from a local
file and never run it.
"""

import json
import sqlite3
import subprocess
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from thenwhat.decide.steps import ENTITY_MATCH, EVIDENCE_STAGE, PAPER_MATCH
from thenwhat.export.store_records import TABLES_READ

# Rows asked for in a table's first page. After each answer the page is sized again so
# that the next is about `PAGE_BYTES`; a page that fails is asked again at half the rows.
PAGE_ROWS = 200
# The size of answer a page aims for: far inside what one D1 answer may carry, whatever
# a table's rows weigh (a payload's row can hold 16 KB, a match's a few hundred bytes).
PAGE_BYTES = 1_000_000
MOST_ROWS = 5000

# The rows of a table an export reads, where it does not read them all: a store that
# also holds the bulk tier has payloads, records and decisions no export asks for.
ROWS_READ = {
    "payload": "sha256 IN (SELECT payload_sha256 FROM evidence_event)",
    "source_record": "kind IN ('term', 'organisation', 'paper')",
    "decision_log": f"step IN ('{ENTITY_MATCH}', '{PAPER_MATCH}', '{EVIDENCE_STAGE}')",
}

# Payload objects fetched at the same time.
OBJECTS_AT_ONCE = 8

# Runs `wrangler` with these arguments and returns what it printed.
Wrangler = Callable[[Sequence[str]], str]


class FetchFailed(Exception):
    """The store could not be read: `wrangler` failed, or answered something else."""


@dataclass
class FetchReport:
    # Rows fetched, by table.
    rows: dict[str, int] = field(default_factory=dict)
    # Seconds a table took, by table.
    seconds: dict[str, float] = field(default_factory=dict)
    queries: int = 0
    objects_fetched: int = 0


def wrangler_in(folder: Path, config: Path | None = None) -> Wrangler:
    """`wrangler` as the ingest service's folder has it installed, signed in as whoever
    runs the command."""

    def run(arguments: Sequence[str]) -> str:
        command = ["pnpm", "exec", "wrangler", *arguments]
        if config is not None:
            command += ["--config", str(config)]
        try:
            done = subprocess.run(command, cwd=folder, capture_output=True, text=True, check=False)
        except OSError as error:
            raise FetchFailed(f"Could not run wrangler in {folder}: {error}") from error
        if done.returncode != 0:
            raise FetchFailed(f"wrangler {arguments[0]} {arguments[1]} failed: {_said(done)}")
        return done.stdout

    return run


def _said(done: subprocess.CompletedProcess[str]) -> str:
    """Why wrangler failed, in its own words: with `--json` it prints the error as JSON,
    whose last line alone says nothing."""
    try:
        error = json.loads(done.stdout)["error"]
        notes = [note["text"] for note in error.get("notes", []) if note.get("text")]
        return " ".join([str(error["text"]), *notes])[:600]
    except (ValueError, LookupError, TypeError, AttributeError):
        text = " ".join((done.stderr or done.stdout).split())
        return text[-600:] if text else f"no output (exit {done.returncode})"


def _literal(value: Any) -> str:
    if isinstance(value, int | float):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _results(printed: str) -> list[dict[str, Any]]:
    """The rows of the one statement a `d1 execute --json` ran."""
    try:
        answered = json.loads(printed)
        results = answered[0]["results"]
    except (ValueError, LookupError, TypeError) as error:
        raise FetchFailed("wrangler did not answer with a statement's results as JSON.") from error
    if not isinstance(results, list):
        raise FetchFailed("wrangler did not answer with a statement's results as JSON.")
    return results


def _bookmark(database: str, wrangler: Wrangler) -> str:
    answer = wrangler(["d1", "time-travel", "info", database, "--json"])
    try:
        bookmark = json.loads(answer)["bookmark"]
    except (ValueError, TypeError, KeyError) as fault:
        raise FetchFailed("D1 did not return its current bookmark.") from fault
    if not isinstance(bookmark, str) or not bookmark:
        raise FetchFailed("D1 returned an empty or invalid bookmark.")
    return bookmark


def _remote_tables(
    database: str,
    db: sqlite3.Connection,
    wrangler: Wrangler,
    report: FetchReport,
    on_table: Callable[[str, int, float], None],
) -> None:
    before = _bookmark(database, wrangler)
    for table in TABLES_READ:
        # A generated column is never written; a BLOB travels as hex (and an empty one
        # as NULL: `hex(NULL)` is the empty text). Pages follow
        # the primary key, which every table read has, or the row id.
        described = [row for row in db.execute(f"PRAGMA table_xinfo({table})") if row[6] == 0]
        columns = [(row[1], str(row[2]).upper() == "BLOB") for row in described]
        key = [row[1] for row in sorted(described, key=lambda row: row[5]) if row[5] > 0]
        order = ", ".join(f'"{name}"' for name in key) or "rowid"
        asked = ", ".join(
            f'CASE WHEN "{name}" IS NULL THEN NULL ELSE hex("{name}") END AS "{name}"'
            if blob
            else f'"{name}"'
            for name, blob in columns
        )
        put = (
            f"INSERT INTO {table} ({', '.join(f'"{name}"' for name, _ in columns)})"
            f" VALUES ({', '.join('?' for _ in columns)})"
        )
        # Each page starts after the last row's key, so a table is read once
        # through however long it is.
        names = key or ["_rowid"]
        marker = "rowid AS _rowid, " if not key else ""
        only = ROWS_READ.get(table)
        page, fetched, after, began = PAGE_ROWS, 0, None, time.monotonic()
        while True:
            conditions = [only] if only else []
            if after is not None:
                left = ", ".join("rowid" if n == "_rowid" else f'"{n}"' for n in names)
                right = ", ".join(_literal(value) for value in after)
                conditions.append(f"({left}) > ({right})")
            statement = (
                f"SELECT {marker}{asked} FROM {table}"
                + (f" WHERE {' AND '.join(conditions)}" if conditions else "")
                + f" ORDER BY {order} LIMIT {page}"
            )
            try:
                printed = wrangler(
                    ["d1", "execute", database, "--remote", "--json", "--command", statement]
                )
                rows = _results(printed)
            except FetchFailed as fault:
                if page > 1:
                    page = max(1, page // 2)
                    continue
                raise FetchFailed(
                    f"Reading {table} after {fetched} rows, one row a page: {fault}"
                ) from fault
            report.queries += 1
            db.execute("BEGIN")
            db.executemany(
                put,
                [
                    tuple(
                        bytes.fromhex(row[name]) if blob and row[name] is not None else row[name]
                        for name, blob in columns
                    )
                    for row in rows
                ],
            )
            db.execute("COMMIT")
            fetched += len(rows)
            if len(rows) < page:
                break
            after = tuple(rows[-1][name] for name in names)
            page = max(1, min(MOST_ROWS, int(page * PAGE_BYTES / max(len(printed), 1))))
        report.seconds[table] = time.monotonic() - began
        on_table(table, fetched, report.seconds[table])
        report.rows[table] = fetched
    if _bookmark(database, wrangler) != before:
        raise FetchFailed(
            "D1 changed during the export. Run the export again for a consistent copy."
        )


def _local_tables(
    database: str,
    snapshot: Path,
    wrangler: Wrangler,
    report: FetchReport,
    on_table: Callable[[str, int, float], None],
) -> None:
    tables = [argument for table in TABLES_READ for argument in ("--table", table)]
    dump = snapshot.with_suffix(".sql")
    wrangler(["d1", "export", database, "--local", *tables, "--output", str(dump)])
    report.queries += 1
    # The dump contains the selected tables from a single read. Import its own schema
    # so an absent source table or column cannot appear to be an empty, valid one.
    with closing(sqlite3.connect(snapshot.with_suffix(".source"))) as source, source:
        source.execute("BEGIN")
        statement = ""
        with dump.open(encoding="utf-8") as stream:
            for line in stream:
                statement += line
                if line.rstrip().endswith(";") and sqlite3.complete_statement(statement):
                    source.execute(statement)
                    statement = ""
        if statement.strip():
            raise FetchFailed("Wrangler returned an incomplete local D1 export.")
        source.execute("ATTACH DATABASE ? AS target", (str(snapshot),))
        for table in TABLES_READ:
            began = time.monotonic()
            columns = [
                f'"{row[1]}"'
                for row in source.execute(f"PRAGMA target.table_xinfo({table})")
                if row[6] == 0
            ]
            fields = ", ".join(columns)
            selected = ", ".join(f"s.{name}" for name in columns)
            only = ROWS_READ.get(table)
            saved = source.execute(
                f"INSERT INTO target.{table} ({fields}) SELECT {selected} FROM main.{table} AS s"
                + (f" WHERE {only}" if only else "")
            )
            report.rows[table] = saved.rowcount
            report.seconds[table] = time.monotonic() - began
            on_table(table, saved.rowcount, report.seconds[table])


def _fetch_objects(
    db: sqlite3.Connection,
    payloads: Path,
    bucket: str,
    where: str,
    wrangler: Wrangler,
) -> int:
    lacking = [
        key
        for (key,) in db.execute(
            "SELECT r2_key FROM payload WHERE r2_key IS NOT NULL ORDER BY r2_key"
        )
        if not (payloads / key).is_file()
    ]

    def get(key: str) -> None:
        held = payloads / key
        held.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=held.parent) as scratch:
            download = Path(scratch) / "object"
            wrangler(["r2", "object", "get", f"{bucket}/{key}", where, "--file", str(download)])
            download.replace(held)

    # One request an object, so several at once: a store holds thousands.
    with ThreadPoolExecutor(max_workers=OBJECTS_AT_ONCE) as pool:
        list(pool.map(get, lacking))
    return len(lacking)


def fetch_store(
    database: str,
    path: Path,
    *,
    schema: Path,
    wrangler: Wrangler,
    payloads: Path | None = None,
    bucket: str | None = None,
    remote: bool = True,
    on_table: Callable[[str, int, float], None] = lambda *_: None,
) -> FetchReport:
    """Make `path` a store file holding the rows of `database` an export reads. `schema`
    is the store's `schema.sql`. With `bucket`, each payload object the folder `payloads`
    lacks is fetched into it. Any file already at `path` is replaced. With `remote`
    false, the database and bucket are the ones Wrangler keeps on this machine. `on_table`
    is told each table's rows and seconds as it is done."""
    report = FetchReport()
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as scratch:
        snapshot = Path(scratch) / "store.sqlite"
        db = sqlite3.connect(snapshot, isolation_level=None)
        try:
            db.executescript(schema.read_text())
            db.execute("PRAGMA foreign_keys = OFF")  # Only the export's tables are copied.
            if remote:
                _remote_tables(database, db, wrangler, report, on_table)
            else:
                _local_tables(database, snapshot, wrangler, report, on_table)
            if bucket is not None and payloads is not None:
                report.objects_fetched = _fetch_objects(
                    db, payloads, bucket, "--remote" if remote else "--local", wrangler
                )
        except sqlite3.Error as fault:
            raise FetchFailed(f"Could not copy the D1 store: {fault}") from fault
        finally:
            db.close()
        snapshot.replace(path)
    return report
