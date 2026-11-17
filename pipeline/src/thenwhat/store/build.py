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

import json
import sqlite3
import time
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, ClaimChange
from thenwhat.store.form import Payload, Record, body, key_of, when
from thenwhat.store.gather import Gathered, stream
from thenwhat.store.push import body_sha256

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
    for record in stream(session, counts, keep_payload=keep_payload):
        report.state[f"{record.kind}\t{record.key}"] = body_sha256(record)
        read[record.kind] += 1
        if record.kind not in began:
            tell()
            began[record.kind] = time.monotonic()
        if in_claims and record.kind != "claim":
            in_claims = False
            yield run
            run = []
            yield from rename_runs
        if record.kind == "claim":
            slug = first.get(record.key, record.key)
            record = Record("claim", slug, record.body | {"slug": slug})
        run.append(record)
        if len(run) >= RUN_RECORDS and not in_claims:
            yield run
            run = []
    run.extend(_merged_publications(session))
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
    """Register, stage and merge one run as the ingest service does; what it added."""
    counts = Counter(record.kind for record in records)
    db.execute(
        ingest["register_run"],
        (run, "migration", "build", None, "build", now.isoformat(), None, None),
    )
    db.execute(ingest["state_steps"], (run, "{}"))
    db.execute(ingest["state_counts"], (run, json.dumps(counts)))
    for start in range(0, len(records), CHUNK_RECORDS):
        chunk = [record.staged() for record in records[start : start + CHUNK_RECORDS]]
        db.execute(ingest["stage"], (run, json.dumps(chunk)))
    db.execute("BEGIN")
    try:
        for statement in merge:
            db.execute(statement, (run,) if "?1" in statement else ())
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
    added = dict(
        db.execute("SELECT kind, added FROM merge_report WHERE run_id = ?", (run,)).fetchall()
    )
    db.execute("DELETE FROM stg WHERE run_id = ?", (run,))
    return added


def build(
    session: Session,
    path: Path,
    *,
    payloads: Path,
    store_sql: Path,
    now: datetime,
    on_kind: Callable[[str, int, float], None] = lambda *_: None,
) -> BuildReport:
    """Make `path` a store file of everything the store keeps of what Postgres holds now.
    The session is only read. A file already at `path` is replaced."""
    report = BuildReport()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    merge = statements(store_sql / "merge.sql")
    ingest = named(store_sql / "ingest.sql")
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys = ON")  # D1 enforces foreign keys
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript((store_sql / "schema.sql").read_text())
        for number, records in enumerate(runs_of(session, payloads, report, on_kind)):
            if not records:
                continue
            report.handed.update(record.kind for record in records)
            added = merge_run(db, f"build-{number}", records, merge=merge, ingest=ingest, now=now)
            report.added.update(added)
            report.runs += 1
        db.execute("PRAGMA journal_mode = DELETE")
        db.execute("VACUUM")
    finally:
        db.close()
    report.size = path.stat().st_size
    return report
