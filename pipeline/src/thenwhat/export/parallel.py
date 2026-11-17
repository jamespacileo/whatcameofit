"""The comparison the cut-over waits on: the export from the pipeline's database beside
the export from the truth store, for the same claims at the same moment. Behavior:
openspec truth-store, "The two exports are compared".

The database is only read. The export's assembly puts a derived status and a first
published time on the claims it is handed; here those stay in memory and the session is
left for its caller to roll back, so comparing changes nothing in either store.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim
from thenwhat.export.build import build_export
from thenwhat.export.compare import Comparison, compare
from thenwhat.export.records import PostgresRecords
from thenwhat.export.store_copy import CopyReport, copy_to_store
from thenwhat.export.store_records import StoreRecords


class ReadOnlyRecords(PostgresRecords):
    """The database's records for a comparison: optionally only some claims, and with
    nothing the assembly derives stored."""

    def __init__(self, session: Session, only: set[int] | None = None) -> None:
        super().__init__(session)
        self.only = only

    def _kept(self, claims: Iterable[Claim]) -> list[Claim]:
        return [claim for claim in claims if self.only is None or claim.id in self.only]

    def published_claims(self) -> Iterable[Claim]:
        return self._kept(super().published_claims())

    def taken_down(self) -> Iterable[Claim]:
        return self._kept(super().taken_down())

    def moved(self) -> list[tuple[str, Claim]]:
        return [
            (slug, claim)
            for slug, claim in super().moved()
            if self.only is None or claim.id in self.only
        ]

    def done(self) -> None:
        """Nothing is stored: the caller rolls the session back."""


def read_only(session: Session) -> None:
    """Have the database itself refuse any write in this session's transaction, and stop
    the session sending the changes the assembly makes in memory. The transaction reads
    one state of the database throughout, so that the copy and the export that follows
    it see the same records while other work goes on."""
    session.autoflush = False
    session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))


def every_nth(session: Session, every: int) -> list[Claim]:
    """Every `every`-th claim by id, with each claim one of them was merged into and each
    claim merged into one of them, so that an address that moved has both its ends."""
    claims = {claim.id: claim for claim in session.scalars(select(Claim).order_by(Claim.id))}
    chosen = {claim_id for claim_id in claims if claim_id % every == 0}
    grew = True
    while grew:
        grew = False
        for claim in claims.values():
            joined = claim.merged_into_id
            if joined is None or (claim.id in chosen) == (joined in chosen):
                continue
            chosen |= {claim.id, joined}
            grew = True
    return [claims[claim_id] for claim_id in sorted(chosen)]


@dataclass(frozen=True)
class ParallelComparison:
    comparison: Comparison
    # Of the copy the store file was made by; None when a store file was given.
    copy: CopyReport | None
    # Claims without a published time in the store: published by the database's export
    # and not yet by an action the store was told.
    unpublished_in_store: list[str]

    def as_json(self) -> dict[str, Any]:
        return {
            "same": self.comparison.same,
            "claims_in_database_export": self.comparison.claims_first,
            "claims_in_store_export": self.comparison.claims_second,
            "differences": [
                {"part": d.part, "is_claim": d.claim, "places": d.places}
                for d in self.comparison.differences
            ],
            "unpublished_in_store": self.unpublished_in_store,
            "copy": None
            if self.copy is None
            else {
                "runs": self.copy.runs,
                "handed_over": self.copy.handed,
                "added": self.copy.added,
                "sharing_a_natural_key": self.copy.folded,
                "payload_objects": self.copy.payload_objects,
                "notes": self.copy.notes,
            },
        }


def compare_with_store(
    session: Session,
    *,
    now: datetime,
    store: Path | None = None,
    payloads: Path | None = None,
    work: Path | None = None,
    store_sql: Path | None = None,
    every: int = 1,
    **settings: Any,
) -> ParallelComparison:
    """Take both exports as of `now` and compare them.

    With `store`, the store's export is read from that file and compared with the
    database's export of every claim. Without one, a store file is first made in `work`
    from the database through the store's own merge (`store_sql`), of every `every`-th
    claim, and the database's export is of the same claims.

    The session must be one `read_only` was called on.
    """
    copy: CopyReport | None = None
    only: set[int] | None = None
    if store is None:
        assert work is not None and store_sql is not None
        claims = None if every == 1 else every_nth(session, every)
        only = None if claims is None else {claim.id for claim in claims}
        store, payloads = work / "store.db", work / "objects"
        copy = copy_to_store(
            session, store, store_sql=store_sql, payloads=payloads, now=now, claims=claims
        )
    records = StoreRecords(store, payloads=payloads)
    try:
        from_store = build_export(records, now=now, **settings)
    finally:
        records.close()
    from_database = build_export(ReadOnlyRecords(session, only), now=now, **settings)
    return ParallelComparison(
        compare(from_database.model_dump(mode="json"), from_store.model_dump(mode="json")),
        copy,
        records.first_published,
    )
