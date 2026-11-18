"""What a build was made from, kept beside it, so a rebuild can leave the bulk tier as it
is when nothing it holds has changed, and a build's id is a function of its data.

A table's watermark is its row count, its largest id and the sum of its rows' `xmin`,
Postgres's id of the transaction that last wrote each row. Any insert, update or delete
changes the count or the sum, once committed: within the transaction that wrote a row,
an update of it keeps the same `xmin`. When it can be wrong: two writes whose `xmin` change
exactly cancels in the sum while the count stays the same (not met in practice), or a
restore of the database that rewrites every row (the sum changes: a needless rebuild,
never a wrong reuse). Postgres keeps `xmin` through `VACUUM FREEZE` since version 9.4.

Only a whole tier is reused, never one kind: the store gives rows its own ids in the
order a build merges them, and bulk rows name hot ones by those ids (a lead its claim
and article). So the bulk file is reused only when no table a bulk record is read from
has changed and the claims and articles it names have the same ids: the same count and
largest id, whatever else about them changed.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# The Postgres tables each tier's records are read from (gather.py).
HOT_SOURCES = (
    "claim",
    "claim_change",
    "source_article",
    "promise",
    "reported_statement",
    "entity",
    "entity_article",
    "entity_match",
    "claim_term",
    "term_record",
    "organisation_record",
    "paper_record",
    "entity_substance",
    "evidence_event",
    "failure_flag",
    "trial_read",
    "reading",
    "decision_log",
    "outlet_icon",
    "link_lead",
)
BULK_SOURCES = (
    "registry_trial",
    "trial_paper",
    "registry_load",
    "article_lead",
    "link_lead",
    "link_share",
    "link_lead_link",
    "link_lead_label",
    "llm_usage",
    "measure_daily",
    "measure_claim",
    "work_entry",
)
# Hot tables whose store ids bulk rows name: their count and largest id must not move.
IDENTITY = ("claim", "source_article")


def watermarks(session: Session, tables: tuple[str, ...]) -> dict[str, list[int]]:
    """Each table's count, largest id (0 for a table without one) and sum of `xmin`."""
    with_id = set(
        session.scalars(
            text(
                "SELECT table_name FROM information_schema.columns"
                " WHERE table_schema = current_schema() AND column_name = 'id'"
            )
        )
    )
    found: dict[str, list[int]] = {}
    for table in dict.fromkeys(tables):
        largest = "coalesce(max(id), 0)" if table in with_id else "0"
        row = session.execute(
            text(f"SELECT count(*), {largest}, coalesce(sum(xmin::text::bigint), 0) FROM {table}")
        ).one()
        found[table] = [int(value) for value in row]
    return found


# The code that forms a record from a row: a build made by other code, a change to what is
# stripped from a payload say, is another build. Read from the files themselves, so no
# version number can be left unbumped.
RECORD_CODE = (
    "store/form.py",
    "store/records.py",
    "store/gather.py",
    "store/tiers.py",
    "store/build.py",
    "sources/people.py",
    "backfill/address.py",
    "db/models.py",
    "domain.py",
)
PACKAGE = Path(__file__).resolve().parents[1]


def sql_digest(store_sql: Path) -> str:
    """The store's schema, merge and staging, and the code that forms its records, by
    checksum: a build made by other SQL or other code is another build, and a rebuild does
    not keep a bulk file made by them."""
    digest = hashlib.sha256()
    for name in ("schema.sql", "merge.sql", "ingest.sql"):
        digest.update((store_sql / name).read_bytes())
    for name in RECORD_CODE:
        digest.update((PACKAGE / name).read_bytes())
    return digest.hexdigest()


def build_id(marks: dict[str, list[int]], digest: str, tier: str) -> str:
    """A build's id, from what it was made from: the same data, SQL and tier give the
    same id, so a later step can skip work already done for it."""
    value = json.dumps({"marks": marks, "sql": digest, "tier": tier}, sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def bulk_unchanged(before: dict[str, Any], now: dict[str, list[int]], digest: str) -> bool:
    """Whether the bulk file a build left can stand for one made now: the same SQL, every
    bulk source's watermark the same, and the claims' and articles' ids where they were."""
    marks = before.get("marks", {})
    return (
        before.get("sql") == digest
        and all(marks.get(table) == now.get(table) for table in BULK_SOURCES)
        and all((marks.get(t) or [None, None])[:2] == now[t][:2] for t in IDENTITY)
    )


def path_of(file: Path) -> Path:
    return file.with_name(file.name + ".watermarks.json")


def read(file: Path) -> dict[str, Any]:
    try:
        return json.loads(path_of(file).read_text())
    except (OSError, ValueError):
        return {}


def write(
    file: Path, marks: dict[str, list[int]], digest: str, build: str, bulk_build: str
) -> None:
    """What a build was made from, its id, and the id of the bulk file beside it: the same
    id, or the build's that made a bulk file this one kept."""
    temporary = path_of(file).with_suffix(".part")
    value = {"build": build, "bulk_build": bulk_build, "sql": digest, "marks": marks}
    temporary.write_text(json.dumps(value, indent=1))
    temporary.replace(path_of(file))
