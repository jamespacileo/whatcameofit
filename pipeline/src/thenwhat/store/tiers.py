"""The store in two tiers (operator's decision of 2026-11-17, docs/adr/0010): the hot tier is
loaded into D1, the bulk tier is one SQLite file kept in R2 and restored by downloading it.

A table is hot when something on Cloudflare reads it: the export of the site from the store
(`export/store_records.py`), the ingest service's routes (`store/ingest/src`), the merge a
run of a hot kind goes through, and the lookup's writes. Every other table is bulk. Why each
table is where it is: `openspec/changes/cloudflare-source-of-truth/store-tables.md`.

No hot table references a bulk one: the schema's foreign keys run from bulk tables to hot
ones (a lead to its claim and article, an article lead to its trial), and a hot row that
names a bulk record names it by text (an event, a match and a trial read name their trial by
registry and identifier). `test_store_tiers.py` holds that against the schema.

Both files keep the whole schema, so either opens with the same queries; each holds only
its own tier's rows. The run tables are in both, because every row names the run that added
it. A payload goes with the rows that point at it, to both when rows of both tiers do.

Each table's checksum is one statement of aggregates, the same SQL on a store file and on
D1, which answers with one row: see `fingerprint_sql`.
"""

import hashlib
import json
import shutil
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOT = "hot"
BULK = "bulk"
BOTH = "both"

# The tier of each table of store/schema.sql. Full-text tables follow their content.
TIER: dict[str, str] = {
    # Read by the export, and what they hang from.
    "claim": HOT,
    "claim_action": HOT,
    "claim_alias": HOT,
    "claim_term": HOT,
    "source_article": HOT,
    "promise": HOT,
    "reported_statement": HOT,
    "entity": HOT,
    "entity_article": HOT,
    "entity_match": HOT,
    "evidence_event": HOT,
    "evidence_conflict": HOT,
    "failure_flag": HOT,
    "trial_read": HOT,
    "source_record": HOT,
    "decision_log": HOT,
    "outlet_icon": HOT,
    "claim_fts": HOT,
    # Read by nothing, but it hangs from an entity: 472 rows, kept with it.
    "entity_substance": HOT,
    # The merge and the ingest service's routes.
    "run": BOTH,
    "run_step": BOTH,
    "run_stated": BOTH,
    "stg": HOT,
    "merging": HOT,
    "merge_report": HOT,
    "merge_guard": HOT,
    "store_step": HOT,
    "work_item": HOT,
    "work_slice": HOT,
    "deployment": HOT,
    # Counted by a reader's lookup; read by nothing else.
    "unlisted_domain_count": HOT,
    # Read by nothing on Cloudflare.
    "registry_trial": BULK,
    "registry_trial_status": BULK,
    "registry_trial_fts": BULK,
    "registry_load": BULK,
    "article_lead": BULK,
    "link_lead": BULK,
    "link_lead_fts": BULK,
    "link_share": BULK,
    "link_lead_link": BULK,
    "link_lead_label": BULK,
    # A lookup's reading of a lead, with the lead. A reader's lookup still stages leads,
    # shares and readings into D1 after the cut: those tables there then hold only what
    # lookups add, and the consumer works them there (store-tables.md).
    "lead_reading": BULK,
    "work_entry": BULK,
    "llm_usage": BULK,
    "measure_daily": BULK,
    "measure_claim": BULK,
    "payload": BOTH,
}

# The kinds of record whose rows are bulk: a daily push hands over only hot kinds unless
# asked for all, because a bulk kind's parents are not in D1.
BULK_KINDS = frozenset(
    {
        "registry_trial",
        "registry_load",
        "article_lead",
        "link_lead",
        "link_share",
        "link_lead_link",
        "link_lead_label",
        "work_entry",
        "usage",
        "measure_daily",
        "measure_claim",
    }
)


# Full-text indexes that read their table's own columns: emptied by their own command.
EXTERNAL_CONTENT = frozenset({"registry_trial_fts", "link_lead_fts"})


# Hot tables the bulk file also holds a copy of, because bulk rows hang from them: a lead
# names its claim and article, an article lead its trial's claim through a lead, a
# measurement its claim. The daily job's merge into the bulk file finds them there.
REFERENCE = frozenset({"claim", "claim_alias", "claim_action", "source_article"})
# The kinds of record that carry them.
REFERENCE_KINDS = frozenset({"claim", "source_article", "action"})


HOT_KINDS = frozenset(
    {
        "claim",
        "action",
        "source_article",
        "promise",
        "reported_statement",
        "entity",
        "entity_article",
        "entity_match",
        "claim_term",
        "source_record",
        "evidence_event",
        "failure_flag",
        "trial_read",
        "decision",
        "outlet_icon",
        "unlisted_domain",
        "entity_substance",
    }
)


def tier_of(table: str) -> str:
    """A table's tier; a shadow table of a full-text index follows the index."""
    if table in TIER:
        return TIER[table]
    for index in ("registry_trial_fts", "link_lead_fts", "claim_fts"):
        if table.startswith(index + "_"):
            return TIER[index]
    raise KeyError(f"store/schema.sql has a table no tier names: {table}")


def in_tier(table: str, tier: str) -> bool:
    return tier_of(table) in (tier, BOTH)


def kept_in(table: str, tier: str) -> bool:
    """Whether a tier's file holds the table's rows: its own tables, those of both, and
    for the bulk file the hot tables it keeps a copy of."""
    return in_tier(table, tier) or (tier == BULK and table in REFERENCE)


def tables(db: sqlite3.Connection) -> list[str]:
    """The store's own tables, full-text shadows and SQLite's own left out."""
    return [
        name
        for (name,) in db.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            " ORDER BY name"
        )
        if not any(
            name.startswith(index + "_")
            for index in ("registry_trial_fts", "link_lead_fts", "claim_fts")
        )
    ]


def references(db: sqlite3.Connection) -> Iterator[tuple[str, str, str]]:
    """Each foreign key of the schema: table, column, table referenced."""
    for table in tables(db):
        for row in db.execute(f"PRAGMA foreign_key_list({table})"):
            yield table, row[3], row[2]


def split(full: Path, out: Path, tier: str, *, payloads: Path | None = None) -> Path:
    """Write `out`, a store file holding `full`'s rows of one tier and the schema whole.
    With `payloads`, the folder of `full`'s payload objects, the tier's objects are
    copied to `<payloads>/<tier>/` under the same keys."""
    out.unlink(missing_ok=True)
    shutil.copyfile(full, out)
    db = sqlite3.connect(out, isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("BEGIN")
        emptied = [t for t in tables(db) if t != "payload" and not kept_in(t, tier)]
        # The full-text triggers would delete from their index row by row: they go while
        # the rows do, and are put back as they were.
        triggers = db.execute(
            "SELECT name, sql FROM sqlite_schema WHERE type = 'trigger' AND tbl_name IN"
            f" ({', '.join('?' for _ in emptied)})",
            emptied,
        ).fetchall()
        for name, _ in triggers:
            db.execute(f"DROP TRIGGER {name}")
        for table in emptied:
            if table in EXTERNAL_CONTENT:
                db.execute(f"INSERT INTO {table} ({table}) VALUES ('delete-all')")
            else:
                db.execute(f"DELETE FROM {table}")
        for _, sql in triggers:
            db.execute(sql)
        pointing = [
            f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"
            for table, column, parent in references(db)
            if parent == "payload" and in_tier(table, tier)
        ]
        db.execute(
            "DELETE FROM payload WHERE sha256 NOT IN ("
            + (" UNION ".join(pointing) or "SELECT NULL")
            + ")"
        )
        db.execute("COMMIT")
        if payloads is not None:
            for (key,) in db.execute("SELECT r2_key FROM payload WHERE r2_key IS NOT NULL"):
                source, target = payloads / key, payloads / tier / key
                if source.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        db.execute("VACUUM")
    finally:
        db.close()
    return out


# --- checksums -----------------------------------------------------------------------


def _columns(db: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    """A table's stored columns with their declared type; generated ones are left out."""
    return [
        (row[1], (row[2] or "").upper())
        for row in db.execute(f"PRAGMA table_xinfo({table})")
        if row[6] == 0
    ]


def fingerprint_sql(db: sqlite3.Connection, table: str) -> str:
    """One SELECT of aggregates over a table that D1 answers with one row, cheap there:
    one scan, no sort, nothing held but the sums.

    For each column: how many values it holds, their total length in bytes, and the sum
    of the code points of each value's first, middle and last character (of its hex
    for a BLOB). The method and its limits: a missing, extra or truncated row, a value
    changed in length, nullness or at one of those three characters changes the sums;
    two rows that swap values between them, or a change inside a value of the same
    length away from those characters, does not. It is a check that a load arrived
    whole, not a cryptographic one."""
    parts = ["count(*)"]
    for column, kind in _columns(db, table):
        text = f"hex({column})" if kind == "BLOB" else f"CAST({column} AS TEXT)"
        parts += [
            f"count({column})",
            f"sum(length(CAST({column} AS BLOB)))",
            f"sum(unicode({text}))",
            f"sum(unicode(substr({text}, length({text}) / 2 + 1, 1)))",
            f"sum(unicode(substr({text}, -1, 1)))",
        ]
    named = ", ".join(f"{part} AS c{number}" for number, part in enumerate(parts))
    return f"SELECT {named} FROM {table}"


def hash_of(row: Any) -> str:
    """The checksum of a fingerprint's one row, the same from Python's SQLite and from D1's
    JSON (each value as an integer or null, in order)."""
    if isinstance(row, dict):
        values = [row[f"c{number}"] for number in range(len(row))]
    else:
        values = list(row)
    normal = [None if value is None else int(value) for value in values]
    return hashlib.sha256(json.dumps(normal, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Checksum:
    table: str
    rows: int
    sha256: str
    sql: str


def checksums(path: Path, tier: str | None = None) -> list[Checksum]:
    """Each table's rows and checksum in a store file, with the SQL that gives the same
    checksum on D1. Full-text indexes are left out: D1 cannot read them as rows of the
    same text the triggers wrote, and their content tables are counted."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        found = []
        for table in tables(db):
            if table.endswith("_fts") or (tier is not None and not in_tier(table, tier)):
                continue
            sql = fingerprint_sql(db, table)
            row = db.execute(sql).fetchone()
            found.append(Checksum(table, int(row[0]), hash_of(row), sql))
        return found
    finally:
        db.close()


def answer_row(answer: Any) -> Any:
    """The one row of a `wrangler d1 execute --json` answer, or the row itself."""
    if isinstance(answer, list):
        answer = answer[0]
    if isinstance(answer, dict) and "results" in answer:
        answer = answer["results"][0]
    return answer


ALL = "all"
CHOICES = (BOTH, HOT, BULK, ALL)


def tier_path(file: Path, tier: str) -> Path:
    """Where a tier's file of a build goes: `store.sqlite` gives `store.hot.sqlite`."""
    return file.with_name(f"{file.stem}.{tier}{file.suffix}")


def split_build(file: Path, payloads: Path, tier: str) -> list[Path]:
    """The tier files of a built store file, written beside it, with each tier's payload
    objects under `<payloads>/<tier>/`. For `all` the whole file is the one written; for
    any other the whole file and its objects folder are removed once split."""
    if tier == ALL:
        return [file]
    wanted = [HOT, BULK] if tier == BOTH else [tier]
    written = [split(file, tier_path(file, one), one, payloads=payloads) for one in wanted]
    file.unlink()
    shutil.rmtree(payloads / "payload", ignore_errors=True)
    return written


def records_of(records: Iterable[Any], kinds: frozenset[str]) -> tuple[list[Any], int]:
    """The records of these kinds, and the payloads they point at; how many were left
    out. Read as a stream: `gather` gives a payload just before the record that points at
    it, and an earlier record's payload once, so a payload is kept when the record after
    it is kept and points at it."""
    chosen: list[Any] = []
    left_out = 0
    held: Any = None
    for record in records:
        if record.kind == "payload":
            if held is not None:
                left_out += 1
            held = record
            continue
        if held is not None:
            if record.kind in kinds and record.body.get("payload_sha256") == held.key:
                chosen.append(held)
            else:
                left_out += 1
            held = None
        if record.kind in kinds:
            chosen.append(record)
        else:
            left_out += 1
    return chosen, left_out + (held is not None)


def hot_records(records: Iterable[Any]) -> tuple[list[Any], int]:
    """The records a push to D1 hands over: those of hot kinds and their payloads."""
    return records_of(records, HOT_KINDS)


def bulk_records(records: Iterable[Any]) -> tuple[list[Any], int]:
    """The records the daily job merges into the bulk file: bulk kinds and their
    payloads, with the claims, articles and actions bulk rows hang from."""
    return records_of(records, BULK_KINDS | REFERENCE_KINDS)


def checks(path: Path, tier: str | None = None) -> dict[str, Any]:
    """The checks the ingest lane's `checksum-d1.mjs` runs on D1: for each table its one
    SELECT and the row it must give, read from the store file; and the build's id."""
    from thenwhat.store.build import BUILD_ID_SQL

    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        held = db.execute(BUILD_ID_SQL).fetchone()
        found: dict[str, Any] = {}
        for table in tables(db):
            if table.endswith("_fts") or (tier is not None and not in_tier(table, tier)):
                continue
            sql = fingerprint_sql(db, table)
            cursor = db.execute(sql)
            names = [column[0] for column in cursor.description]
            found[table] = {
                "sql": sql,
                "expected": dict(zip(names, cursor.fetchone(), strict=True)),
            }
        return {"build": held[0] if held else None, "tables": found}
    finally:
        db.close()
