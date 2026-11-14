"""Storing the index record a paper's facts are read from. Behavior: openspec
paper-facts ("The stored record holds no abstract and no author") and source-clients
("Stored paper records are refreshed when old").

A paper is known by its DOI, else by its PubMed number, else by the index's own
identifier. One row per paper, whichever of them it was asked for by.
"""

from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import PaperRecord
from thenwhat.events.paper_facts import doi_of, pubmed_id_of, reduced
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.europepmc import EuropePmc

# Follow-up events name a paper with no DOI as "<index source>:<number>".
PUBMED_SOURCE = "MED:"
PUBMED_PREFIX = "pmid:"


class PaperIndex(Protocol):
    def paper(self, doi: str) -> SourceRecord | None: ...
    def paper_by_pubmed_id(self, pubmed_id: str) -> SourceRecord | None: ...


def paper_reference(external_id: str) -> tuple[str | None, str | None]:
    """The DOI and the PubMed number in an identifier a match or an event holds."""
    if external_id.startswith("10."):
        return external_id.lower(), None
    for prefix in (PUBMED_SOURCE, PUBMED_PREFIX):
        number = external_id.removeprefix(prefix)
        if number != external_id and number.isdigit():
            return None, number
    return None, None


def stored_paper(
    session: Session,
    *,
    doi: str | None = None,
    pubmed_id: str | None = None,
    identifier: str | None = None,
) -> PaperRecord | None:
    """The stored record of a paper known by any of these."""
    for column, value in (
        (PaperRecord.identifier, doi.lower() if doi else None),
        (PaperRecord.pubmed_id, pubmed_id),
        (PaperRecord.identifier, identifier),
    ):
        if value:
            row = session.scalars(select(PaperRecord).where(column == value)).first()
            if row is not None:
                return row
    return None


def keep_paper(
    session: Session,
    index: PaperIndex,
    *,
    now: datetime,
    max_age: timedelta,
    doi: str | None = None,
    pubmed_id: str | None = None,
    identifier: str | None = None,
    held: SourceRecord | None = None,
) -> PaperRecord | None:
    """Make sure the paper's record is stored and no older than `max_age`.

    A stored record that is young enough causes no request. `held` is a record of the
    paper already in hand, such as the one a follow-up event keeps: it is stored when
    nothing is, and asked for again only once it is old. A paper the index does not
    hold is stored with no payload, so that it is not asked for on every fetch.
    """
    row = stored_paper(session, doi=doi, pubmed_id=pubmed_id, identifier=identifier)
    if row is not None and now - row.fetched_at <= max_age:
        return row
    newer = held is not None and (row is None or held.fetched_at > row.fetched_at)
    if held and newer and (now - held.fetched_at <= max_age or not (doi or pubmed_id)):
        return _store(session, row, held, doi=doi, pubmed_id=pubmed_id, identifier=identifier)
    if doi:
        record = index.paper(doi)
    elif pubmed_id:
        record = index.paper_by_pubmed_id(pubmed_id)
    else:
        return row
    if record is None:
        return _store_not_held(session, row, doi=doi, pubmed_id=pubmed_id, now=now)
    return _store(session, row, record, doi=doi, pubmed_id=pubmed_id, identifier=identifier)


def note_paper(
    session: Session,
    *,
    doi: str,
    record: SourceRecord | None,
    now: datetime,
    max_age: timedelta,
) -> PaperRecord:
    """Store what the index has just answered for this DOI, unless a stored record is
    still young enough: the record, or that the index does not hold the paper."""
    row = stored_paper(session, doi=doi)
    if row is not None and now - row.fetched_at <= max_age:
        return row
    if record is None:
        return _store_not_held(session, row, doi=doi, pubmed_id=None, now=now)
    return _store(session, row, record, doi=doi, pubmed_id=None, identifier=None)


def _store(
    session: Session,
    row: PaperRecord | None,
    record: SourceRecord,
    *,
    doi: str | None,
    pubmed_id: str | None,
    identifier: str | None,
) -> PaperRecord:
    payload = reduced(record.payload)
    number = pubmed_id_of(payload) or pubmed_id
    if row is None:
        # The record may be one already stored under its other identifier.
        row = stored_paper(session, doi=doi_of(payload), pubmed_id=number)
    if row is None:
        row = PaperRecord(
            identifier=(doi.lower() if doi else None)
            or doi_of(payload)
            or (f"{PUBMED_PREFIX}{number}" if number else None)
            or identifier
            or record.external_id,
            source_name=record.source_name,
        )
        session.add(row)
    row.source_name = record.source_name
    row.pubmed_id = number
    row.payload = payload
    row.fetched_at = record.fetched_at
    session.flush()
    return row


def _store_not_held(
    session: Session,
    row: PaperRecord | None,
    *,
    doi: str | None,
    pubmed_id: str | None,
    now: datetime,
) -> PaperRecord:
    if row is None:
        row = PaperRecord(
            identifier=doi.lower() if doi else f"{PUBMED_PREFIX}{pubmed_id}",
            source_name=EuropePmc.name,
            pubmed_id=pubmed_id,
        )
        session.add(row)
    row.payload = None
    row.fetched_at = now
    session.flush()
    return row
