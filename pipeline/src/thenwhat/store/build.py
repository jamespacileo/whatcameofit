"""The whole tracker as one SQLite file of the store's schema, made locally and loaded in
bulk: the way the store is first filled and the way it is restored, never row by row
through the ingest service.

The records are the pipeline's own natural-key form (`gather`), merged by
`store/merge.sql` in runs as a D1 batch runs it, so the file holds what the store's merge
would hold. Large payloads are written once each to a folder under their R2 key, for
upload to the bucket beside the load.

Two things are handed over here that a snapshot pushed through the service never carries
(`gather.py`), because the file is filled once and never pushed again: a renamed claim
is handed over under its first slug and renamed in order, so the store knows every
address it had; a merged claim's publication, so the store can say its address was
public (the export lists it under `moved`).
"""

import gzip
import hashlib
import json
import secrets
import sqlite3
import time
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, ClaimChange
from thenwhat.store.form import Payload, Record, body, key_of, when
from thenwhat.store.gather import Gathered, stream
from thenwhat.store.push import body_sha256
from thenwhat.store.tiers import HOT_KINDS

# Records to a run. Each run is one merge, parents before children across runs.
RUN_RECORDS = 20_000
# Records to a staged chunk.
CHUNK_RECORDS = 500


class BuildFailed(Exception):
    """The store's merge refused a run of the build."""


@dataclass
class BuildReport:
    runs: int = 0
    handed: Counter[str] = field(default_factory=Counter)
    added: Counter[str] = field(default_factory=Counter)
    payload_objects: int = 0
    payload_bytes: int = 0
    # Rows whose natural key an earlier row gave, and ledger entries naming no record.
    repeated: Counter[str] = field(default_factory=Counter)
    unnamed: Counter[str] = field(default_factory=Counter)
    size: int = 0
    # Each record handed over, as `push` keeps it: what a later push starts from.
    state: dict[str, str] = field(default_factory=dict)
    # The same, of the hot tier's records alone: what a load of the hot file holds, and
    # so what a push to D1 after that load starts from. A bulk record (a trial of the
    # target set) is not in D1 until a push brings it.
    hot_state: dict[str, str] = field(default_factory=dict)
    # Names the build: its runs are `build-<id>-<n>`, so a store file and D1 both say
    # which build they hold with `build_id_sql`.
    build_id: str = field(default_factory=lambda: secrets.token_hex(8))


# Which build a store file or D1 holds: one row, the id, or none.
BUILD_ID_SQL = (
    "SELECT substr(id, 7, 16) AS build FROM run WHERE id LIKE 'build-%' ORDER BY id LIMIT 1"
)


def statements(path: Path) -> list[str]:
    """A SQL file's statements: split at a line holding only `;`, comment lines dropped."""
    found = []
    for chunk in path.read_text().split("\n;\n"):
        lines = [line for line in chunk.splitlines() if line.strip() and not line.startswith("--")]
        if lines:
            found.append("\n".join(lines))
    return found


def named(path: Path) -> dict[str, str]:
    """A SQL file's statements by their `-- name:` line."""
    found: dict[str, str] = {}
    name: str | None = None
    lines: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("-- name:"):
            name, lines = line.split(":", 1)[1].strip(), []
        elif line.strip() == ";" and name:
            found[name], name = "\n".join(lines), None
        elif name and not line.startswith("--"):
            lines.append(line)
    return found


def _renames(session: Session) -> tuple[dict[str, str], list[list[Record]]]:
    """Each renamed claim's first slug by the slug it has now, and the renames that bring
    it there, one run a rename so that each sees the one before."""
    now_slug = {claim_id: slug for claim_id, slug in session.execute(select(Claim.id, Claim.slug))}
    by_claim: dict[int, list[ClaimChange]] = {}
    for change in session.scalars(
        select(ClaimChange)
        .where(ClaimChange.kind == "rename", ClaimChange.former_slug.is_not(None))
        .order_by(ClaimChange.decided_at, ClaimChange.id)
    ):
        by_claim.setdefault(change.claim_id, []).append(change)
    first: dict[str, str] = {}
    runs: list[list[Record]] = []
    for claim_id, changes in by_claim.items():
        slugs = [change.former_slug for change in changes] + [now_slug[claim_id]]
        first[now_slug[claim_id]] = str(slugs[0])
        for change, before, after in zip(changes, slugs, slugs[1:], strict=False):
            if before == after:
                continue
            runs.append(
                [
                    Record(
                        "action",
                        key_of("rename", before, when(change.decided_at)),
                        body(
                            action="rename",
                            slug=before,
                            new_slug=after,
                            decided_by=change.decided_by.value,
                            at=when(change.decided_at),
                        ),
                    )
                ]
            )
    return first, runs


def _merged_publications(session: Session) -> list[Record]:
    return [
        Record(
            "action",
            key_of("publish", claim.slug),
            body(action="publish", slug=claim.slug, at=when(claim.published_at)),
        )
        for claim in session.scalars(
            select(Claim)
            .where(Claim.merged_into_id.is_not(None), Claim.published_at.is_not(None))
            .order_by(Claim.id)
        )
    ]


def runs_of(
    session: Session,
    payloads: Path,
    report: BuildReport,
    on_kind: Callable[[str, int, float], None] = lambda *_: None,
    hot_only: bool = False,
) -> Iterator[list[Record]]:
    """The build's runs in the order they are merged, as the records are read: every
    claim under its first slug, the renames, then everything else in runs of
    `RUN_RECORDS`. `on_kind` is told each kind's count and seconds as it is done."""

    def keep_payload(payload: Payload) -> None:
        if payload.inline:
            return
        held = payloads / payload.r2_key
        if held.exists():
            return
        held.parent.mkdir(parents=True, exist_ok=True)
        held.write_bytes(payload.text.encode())
        report.payload_objects += 1
        report.payload_bytes += payload.bytes

    counts = Gathered(records=[], repeated=report.repeated, unnamed=report.unnamed)
    first, rename_runs = _renames(session)
    run: list[Record] = []
    read: Counter[str] = Counter()
    began: dict[str, float] = {}
    told: set[str] = set()

    def tell() -> None:
        for kind, at in began.items():
            if kind not in told and kind != "payload":
                told.add(kind)
                on_kind(kind, read[kind], time.monotonic() - at)

    in_claims = True
    held: Record | None = None
    for record in stream(session, counts, keep_payload=keep_payload, hot_only=hot_only):
        report.state[f"{record.kind}\t{record.key}"] = body_sha256(record)
        # A payload goes with the record after it (`gather`): hot when that record is.
        if record.kind == "payload":
            held = record
        else:
            if record.kind in HOT_KINDS:
                report.hot_state[f"{record.kind}\t{record.key}"] = report.state[
                    f"{record.kind}\t{record.key}"
                ]
                if held is not None and record.body.get("payload_sha256") == held.key:
                    report.hot_state[f"payload\t{held.key}"] = report.state[f"payload\t{held.key}"]
            held = None
        read[record.kind] += 1
        if record.kind not in began:
            tell()
            began[record.kind] = time.monotonic()
        if in_claims and record.kind != "claim":
            in_claims = False
            yield run
            yield from rename_runs
            # With the first records after the claims, which the merges are among: a
            # publication is applied before a merge of the same run, and in any later
            # run the merged slug already names the claim that stayed.
            run = _merged_publications(session)
        if record.kind == "claim":
            slug = first.get(record.key, record.key)
            record = Record("claim", slug, record.body | {"slug": slug})
        run.append(record)
        if len(run) >= RUN_RECORDS and not in_claims:
            yield run
            run = []
    if in_claims:
        # Nothing but claims: there is no merge, and so no merged claim's publication.
        yield run
        yield from rename_runs
        run = []
    yield run
    tell()
    if "payload" in began:
        on_kind("payload", read["payload"], time.monotonic() - began["payload"])


def merge_run(
    db: sqlite3.Connection,
    run: str,
    records: list[Record],
    *,
    merge: list[str],
    ingest: dict[str, str],
    now: datetime,
) -> dict[str, int]:
    """Register, stage and merge one run as the ingest service does, all in one
    transaction, so a run either is merged with its registration or leaves no trace; what
    it added. A run the merge refuses is undone and raised, never left registered."""
    counts = Counter(record.kind for record in records)
    db.execute("BEGIN")
    try:
        db.execute(
            ingest["register_run"],
            (run, "migration", "build", None, "build", now.isoformat(), None, None),
        )
        db.execute(ingest["state_steps"], (run, "{}"))
        db.execute(ingest["state_counts"], (run, json.dumps(counts)))
        for start in range(0, len(records), CHUNK_RECORDS):
            chunk = [record.staged() for record in records[start : start + CHUNK_RECORDS]]
            db.execute(ingest["stage"], (run, json.dumps(chunk)))
        for statement in merge:
            db.execute(statement, (run,) if "?1" in statement else ())
        (status,) = db.execute("SELECT status FROM run WHERE id = ?", (run,)).fetchone()
        if status != "merged":
            raise sqlite3.IntegrityError(f"the run ended {status}, not merged")
        added = dict(
            db.execute("SELECT kind, added FROM merge_report WHERE run_id = ?", (run,)).fetchall()
        )
        db.execute("DELETE FROM stg WHERE run_id = ?", (run,))
        db.execute("COMMIT")
    except sqlite3.Error as error:
        short = [
            f"{kind}: {stated} handed over, {resolved} with a parent found"
            for kind, stated, resolved in db.execute(
                "SELECT t.kind, t.records, coalesce(m.resolved, 0) FROM run_stated t"
                " LEFT JOIN merge_report m ON m.run_id = t.run_id AND m.kind = t.kind"
                " WHERE t.run_id = ? AND t.records <> coalesce(m.resolved, 0)",
                (run,),
            )
        ]
        db.execute("ROLLBACK")
        raise BuildFailed(
            f"The store's merge undid run {run}: {error}. {'; '.join(short)}"
        ) from error
    return added


def build(
    session: Session,
    path: Path,
    *,
    payloads: Path,
    store_sql: Path,
    now: datetime,
    on_kind: Callable[[str, int, float], None] = lambda *_: None,
    hot_only: bool = False,
    build_id: str | None = None,
) -> BuildReport:
    """Make `path` a store file of everything the store keeps of what Postgres holds now.
    The session is only read. A file already at `path` is replaced."""
    report = BuildReport()
    if build_id is not None:
        report.build_id = build_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    merge = statements(store_sql / "merge.sql")
    ingest = named(store_sql / "ingest.sql")
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys = ON")  # D1 enforces foreign keys
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript((store_sql / "schema.sql").read_text())
        for number, records in enumerate(
            runs_of(session, payloads, report, on_kind, hot_only=hot_only)
        ):
            if not records:
                continue
            report.handed.update(record.kind for record in records)
            added = merge_run(
                db,
                f"build-{report.build_id}-{number}",
                records,
                merge=merge,
                ingest=ingest,
                now=now,
            )
            report.added.update(added)
            report.runs += 1
        db.execute("PRAGMA journal_mode = DELETE")
        db.execute("VACUUM")
    finally:
        db.close()
    report.size = path.stat().st_size
    return report


def merged_runs(db: sqlite3.Connection) -> set[str]:
    """The runs a store file holds as merged."""
    return {run for (run,) in db.execute("SELECT id FROM run WHERE status = 'merged'")}


def merge_into(
    path: Path,
    runs: list[tuple[str, list[Record]]],
    *,
    store_sql: Path,
    now: datetime,
) -> tuple[Counter[str], list[str]]:
    """Merge named runs of records into a store file already built, by `store/merge.sql`,
    as the daily job merges a day's bulk records into the bulk file; a run over
    `RUN_RECORDS` is merged as `<name>-<n>`. A run the file already holds as merged is not
    merged again, so a retry merges what is left or fails, and never counts a run it did
    not merge. What the merge added, by kind, and the names of the runs it merged."""
    merge = statements(store_sql / "merge.sql")
    ingest = named(store_sql / "ingest.sql")
    added: Counter[str] = Counter()
    done: list[str] = []
    db = sqlite3.connect(path, isolation_level=None)
    try:
        # As in D1: the bulk file holds the hot rows bulk rows hang from (`REFERENCE`).
        db.execute("PRAGMA foreign_keys = ON")
        # A downloaded bulk build may predate the current merge schema.
        migrations = (
            ("work_entry", "reason", "0008_work_entry_waits.sql"),
            ("claim", "drafting_trial_ids", "0009_registry_claim_origin.sql"),
            ("claim", "registry_candidate_trial_ids", "0010_registry_candidate_trial_ids.sql"),
        )
        for table, column, filename in migrations:
            schema_check = "SELECT 1 FROM pragma_table_info(?) WHERE name = ?"
            if db.execute(schema_check, (table, column)).fetchone():
                continue
            db.execute("BEGIN IMMEDIATE")
            if not db.execute(schema_check, (table, column)).fetchone():
                migration = store_sql / "ingest/migrations" / filename
                for statement in migration.read_text().split(";"):
                    if statement.strip():
                        db.execute(statement)
            db.commit()
        held = merged_runs(db)
        for name, records in runs:
            for number, start in enumerate(range(0, max(len(records), 1), RUN_RECORDS)):
                part = f"{name}-{number}"
                chunk = records[start : start + RUN_RECORDS]
                if part in held or not chunk:
                    continue
                added.update(merge_run(db, part, chunk, merge=merge, ingest=ingest, now=now))
                done.append(part)
    finally:
        db.close()
    return added, done


def run_name(prefix: str, *parts: str) -> str:
    """A run's name made from what it holds, so the same records give the same run."""
    return f"{prefix}-" + hashlib.sha256("\n".join(parts).encode()).hexdigest()[:24]


def base_of(path: Path, runs: list[tuple[str, list[Record]]]) -> str:
    """What a delta is applied on top of: the merged runs of the file, other than the
    delta's own, by checksum. A restore applies a delta only on a file that has the same."""
    names = {name for name, _ in runs}
    held = sorted(run for run in merged_runs_of(path) if run.rsplit("-", 1)[0] not in names)
    return hashlib.sha256("\n".join(held).encode()).hexdigest()


DELTA_VERSION = 2


def write_delta(path: Path, runs: list[tuple[str, list[Record]]], *, base: str) -> None:
    """A day's bulk records as one object beside the last bulk build: gzipped JSON lines,
    a head line naming the base it applies on and its runs, then each record with its run.
    Written to a temporary name and moved into place, so a delta is whole or absent."""
    temporary = path.with_name(path.name + ".part")
    with gzip.open(temporary, "wt", encoding="utf-8") as stream:
        head = {"delta": DELTA_VERSION, "base": base, "runs": [name for name, _ in runs]}
        stream.write(json.dumps(head) + "\n")
        for name, records in runs:
            for record in records:
                line = {"run": name, **record.staged()}
                stream.write(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def read_delta(path: Path) -> tuple[str, list[tuple[str, list[Record]]]]:
    """A delta's base and its runs, in order."""
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        head = json.loads(stream.readline())
        if head.get("delta") != DELTA_VERSION:
            raise BuildFailed(f"{path} is not a delta this pipeline writes.")
        by_run: dict[str, list[Record]] = {name: [] for name in head["runs"]}
        for line in stream:
            if line.strip():
                value = json.loads(line)
                by_run[value.pop("run")].append(Record(**value))
    return head["base"], list(by_run.items())


def parts_of(name: str, records: list[Record]) -> list[str]:
    """The names a run is merged under (`merge_into`): none for a run with no records."""
    return [f"{name}-{number}" for number in range((len(records) + RUN_RECORDS - 1) // RUN_RECORDS)]


def apply_delta(path: Path, delta: Path, *, store_sql: Path, now: datetime) -> list[str]:
    """Replay a delta into a downloaded bulk file under its own run names: runs the file
    already holds are skipped, and a delta whose base is not the file's is refused, so a
    delta applied out of order or twice changes nothing it should not. A replay stopped
    part way through a run of many parts is finished by applying the delta again. The runs
    merged."""
    base, runs = read_delta(delta)
    held = merged_runs_of(path)
    if runs and all(part in held for name, records in runs for part in parts_of(name, records)):
        return []  # applied before
    if base_of(path, runs) != base:
        raise BuildFailed(
            f"{delta.name} applies on another state of the bulk file: apply the deltas"
            " before it first, in order."
        )
    return merge_into(path, runs, store_sql=store_sql, now=now)[1]


def merge_day(
    file: Path,
    records: list[Record],
    state: dict[str, str],
    *,
    delta: Path,
    store_sql: Path,
    now: datetime,
    save_state: Callable[[dict[str, str]], None] = lambda _: None,
) -> tuple[Any, Counter[str]]:
    """The daily job's merge into the bulk file: the records new or changed since `state`,
    as one run, written as the day's delta; `state` is brought up to date and saved.

    The run is named by the file's merged runs and the records chosen, and written to
    `<file>.pending.json` with its records before it is merged. A merge that finds a run
    pending settles it first: merged in the file already, its records are taken as merged;
    not, the same run is merged; either way it goes into this day's delta too, and the
    state is saved, before what is left is worked out. So a crash after a merge and before
    the state was saved never merges those records again under another name, even when
    records have arrived since."""
    from thenwhat.store.push import (
        check_belongs,
        clear_pending,
        increment,
        pending_path,
        read_pending,
        state_of,
        write_pending,
    )

    pending = pending_path(file)
    belongs = {"build": build_id_of(file) or ""}
    held = read_pending(pending)
    if held is not None:
        check_belongs(pending, held[2], belongs)
    # The day's delta so far: this merge adds to it, never replaces it. Checked before the
    # file is touched, so a delta that is not the file's is refused, not added to.
    runs = _day_so_far(file, delta, held[:2] if held is not None else None)
    added: Counter[str] = Counter()

    def keep(name: str, records: list[Record]) -> None:
        # Into the day's delta: a run already there is not written twice, and a run with
        # nothing in it only while there is nothing else.
        nonlocal runs
        if (not records and runs) or any(have == name for have, _ in runs):
            return
        runs = [run for run in runs if run[1]]
        runs.append((name, records))
        write_delta(delta, runs, base=base_of(file, runs))

    if held is not None:
        name, settled, _ = held
        more, _ = merge_into(file, [(name, settled)], store_sql=store_sql, now=now)
        added.update(more)
        # In the delta before the pending file goes: else a stop between them loses it.
        keep(name, settled)
        state.update(state_of(settled))
        save_state(state)
        clear_pending(pending)
    chosen = increment(records, state, actions=True)
    content = sorted(f"{k}={v}" for k, v in state_of(chosen.records).items())
    # The same edit can recur after a record returns to an earlier value. Its previous
    # contents would give both edits the same name, but their merge histories differ.
    name = run_name("bulk", base_of(file, []), *content)
    write_pending(pending, name, chosen.records, belongs)
    more, _ = merge_into(file, [(name, chosen.records)], store_sql=store_sql, now=now)
    added.update(more)
    keep(name, chosen.records)
    state.update(state_of(chosen.records))
    save_state(state)
    clear_pending(pending)
    return chosen, added


def _day_so_far(
    file: Path, delta: Path, pending: tuple[str, list[Record]] | None
) -> list[tuple[str, list[Record]]]:
    """The runs of the day's delta already written, if it is this file's: each of its runs
    merged in the file, and the file holding nothing else since its base but the pending
    run. Anything else is refused before the file is touched."""
    if not delta.exists():
        return []
    base, runs = read_delta(delta)
    held = merged_runs_of(file)
    missing = [
        part for name, records in runs for part in parts_of(name, records) if part not in held
    ]
    if missing:
        raise BuildFailed(
            f"{delta} holds runs {file.name} has not merged ({', '.join(missing)}): it is"
            " another file's delta. Move it aside or merge into the file it was made from."
        )
    if base_of(file, runs + ([pending] if pending is not None else [])) != base:
        raise BuildFailed(
            f"{delta} was made on another state of {file.name}: it is another file's or"
            " another day's delta. Move it aside before merging."
        )
    return runs


def merged_runs_of(path: Path) -> set[str]:
    """The runs a store file at `path` holds as merged."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return merged_runs(db)
    finally:
        db.close()


def build_id_of(path: Path) -> str | None:
    """The build a store file was made by (`BUILD_ID_SQL`), or None."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = db.execute(BUILD_ID_SQL).fetchone()
    finally:
        db.close()
    return row[0] if row else None
