"""A copy of what an export reads, fetched from the truth store itself (a D1 database)
into a SQLite file of the store's schema. Reading only. Behavior: openspec truth-store,
"The two exports are compared" ("Comparing against the store itself").

D1 cannot export a database that has virtual tables, and the store has its search
tables (Cloudflare's "Import and export data", known limitations, read 2026-11-17). So
the rows are read with `wrangler d1 execute --remote --json`, one page of one table at a
time, in the order of the table's key. Only the tables an export reads are fetched.

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
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from thenwhat.export.store_records import TABLES_READ

# Rows asked for at once, by table: a page's JSON has to stay well inside what one
# answer may carry, and a payload's row can hold 16 KB.
PAGE_ROWS = 2000
PAGE_ROWS_OF = {"payload": 100, "source_record": 500, "trial_read": 500, "decision_log": 1000}

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
            said = (done.stderr or done.stdout).strip().splitlines()
            last = said[-1] if said else "no output"
            raise FetchFailed(f"wrangler {arguments[0]} {arguments[1]} failed: {last}")
        return done.stdout

    return run


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


def fetch_store(
    database: str,
    path: Path,
    *,
    schema: Path,
    wrangler: Wrangler,
    payloads: Path | None = None,
    bucket: str | None = None,
    remote: bool = True,
) -> FetchReport:
    """Make `path` a store file holding the rows of `database` an export reads. `schema`
    is the store's `schema.sql`. With `bucket`, each payload object the folder `payloads`
    lacks is fetched into it. Any file already at `path` is replaced. With `remote`
    false, the database and bucket are the ones Wrangler keeps on this machine."""
    where = "--remote" if remote else "--local"
    report = FetchReport()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.executescript(schema.read_text())
        db.execute("PRAGMA foreign_keys = OFF")  # tables arrive whole, in no parent order
        for table in TABLES_READ:
            # A generated column is never written; a BLOB travels as hex. Pages follow
            # the primary key, which every table read has, or the row id.
            described = [row for row in db.execute(f"PRAGMA table_xinfo({table})") if row[6] == 0]
            columns = [(row[1], str(row[2]).upper() == "BLOB") for row in described]
            key = [row[1] for row in sorted(described, key=lambda row: row[5]) if row[5] > 0]
            order = ", ".join(f'"{name}"' for name in key) or "rowid"
            asked = ", ".join(
                f'hex("{name}") AS "{name}"' if blob else f'"{name}"' for name, blob in columns
            )
            put = (
                f"INSERT INTO {table} ({', '.join(f'"{name}"' for name, _ in columns)})"
                f" VALUES ({', '.join('?' for _ in columns)})"
            )
            page = PAGE_ROWS_OF.get(table, PAGE_ROWS)
            fetched = 0
            while True:
                rows = _results(
                    wrangler(
                        [
                            "d1",
                            "execute",
                            database,
                            where,
                            "--json",
                            "--command",
                            f"SELECT {asked} FROM {table} ORDER BY {order}"
                            f" LIMIT {page} OFFSET {fetched}",
                        ]
                    )
                )
                report.queries += 1
                db.execute("BEGIN")
                db.executemany(
                    put,
                    [
                        tuple(
                            bytes.fromhex(row[name])
                            if blob and row[name] is not None
                            else row[name]
                            for name, blob in columns
                        )
                        for row in rows
                    ],
                )
                db.execute("COMMIT")
                fetched += len(rows)
                if len(rows) < page:
                    break
            report.rows[table] = fetched
        if bucket is not None and payloads is not None:
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
                wrangler(["r2", "object", "get", f"{bucket}/{key}", where, "--file", str(held)])

            # One request an object, so several at once: a store holds thousands.
            with ThreadPoolExecutor(max_workers=OBJECTS_AT_ONCE) as pool:
                list(pool.map(get, lacking))
            report.objects_fetched = len(lacking)
    finally:
        db.close()
    return report
