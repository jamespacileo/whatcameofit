"""Reading a stored term record: its label and definition, by the source it came from.
One function per source, so that a record of one source is never read as another's.
"""

from collections.abc import Callable
from dataclasses import dataclass

from thenwhat.db.models import TermRecord
from thenwhat.sources import mesh, opentargets
from thenwhat.sources.base import SourceRecord


@dataclass(frozen=True, slots=True)
class RecordText:
    label: str
    # The source's own words, exactly as given, or None when it gives none.
    definition: str | None
    # The version of the vocabulary the record was read from, when the source has one.
    version: str | None


class UnknownRecordSource(Exception):
    """A stored record is of a source no reader exists for."""


def _mesh(record: SourceRecord) -> RecordText:
    """A MeSH descriptor or supplementary record: a descriptor's definition is its
    preferred concept's scope note, a supplementary record's its own note."""
    term = mesh.describe(record)
    return RecordText(term.label, term.definition, term.version)


def _target(record: SourceRecord) -> RecordText:
    """An Open Targets target: the gene's symbol and its first function description. A
    drug's record gives the drug's name as the source writes it and no definition."""
    if opentargets.DRUG_IDENTIFIER.match(record.external_id):
        return RecordText(opentargets.describe_drug(record).name, None, None)
    target = opentargets.describe(record)
    return RecordText(target.symbol, target.definition, None)


READERS: dict[str, Callable[[SourceRecord], RecordText]] = {
    mesh.Mesh.name: _mesh,
    opentargets.OpenTargets.name: _target,
}


def read_record(record: TermRecord) -> RecordText:
    """The label and definition of a stored record, read as its own source writes it."""
    reader = READERS.get(record.source_name)
    if reader is None:
        raise UnknownRecordSource(
            f"No reader exists for a term record of the source '{record.source_name}'."
        )
    return reader(
        SourceRecord(
            record.source_name, record.external_id, record.url, record.payload, record.fetched_at
        )
    )
