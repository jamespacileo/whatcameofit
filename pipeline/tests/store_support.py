"""Taking the same export twice: from the test database, and from a SQLite file of the
truth store's schema filled from it through the store's own merge."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from thenwhat.export.build import build_export
from thenwhat.export.compare import canonical_bytes, compare
from thenwhat.export.store_copy import CopyReport, copy_to_store
from thenwhat.export.store_records import StoreRecords

STORE_SQL = Path(__file__).resolve().parents[2] / "store"


def store_of(session: Session, folder: Path, now: datetime) -> tuple[StoreRecords, CopyReport]:
    """A store file holding what the session holds, opened for an export."""
    session.flush()
    report = copy_to_store(
        session, folder / "store.db", store_sql=STORE_SQL, payloads=folder / "objects", now=now
    )
    return StoreRecords(folder / "store.db", payloads=folder / "objects"), report


def both_exports(
    session: Session, folder: Path, now: datetime, **settings: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The export from the store file, then the export from the database. In that order:
    the second stores the statuses and published times it derives."""
    records, _ = store_of(session, folder, now)
    try:
        from_store = json.loads(build_export(records, now=now, **settings).model_dump_json())
    finally:
        records.close()
    from_database = json.loads(build_export(session, now=now, **settings).model_dump_json())
    return from_database, from_store


def assert_same_export(
    session: Session, folder: Path, now: datetime, **settings: Any
) -> dict[str, Any]:
    """Hold the two exports to be the same, byte for byte in canonical form, and return
    the database's."""
    from_database, from_store = both_exports(session, folder, now, **settings)
    comparison = compare(from_database, from_store)
    assert comparison.same, "\n".join(comparison.lines())
    assert canonical_bytes(from_database) == canonical_bytes(from_store)
    return from_database
