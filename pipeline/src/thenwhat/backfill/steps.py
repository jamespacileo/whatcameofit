"""The shape of a step: one kind of processing applied to one kind of record.
Behavior: openspec work-ledger."""

from collections.abc import Sequence
from typing import Any, Protocol

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import DuplicateStep, UnknownStep
from thenwhat.domain import WorkOutcome


class CountingClient(Protocol):
    """What a step asks its source through. It counts its own requests so the ledger
    can record how many a record used, whether or not the step finished."""

    requests_made: int


class Step(Protocol):
    name: str
    # Raising this makes every record in scope due again for this step only.
    version: int
    # The kind of record and its table. The ledger names a record by kind and id.
    record_kind: str
    model: type[Any]
    source: str
    requests_per_record: int

    def scope(self) -> ColumnElement[bool]:
        """Which records the step applies to, as a query condition."""
        ...

    def inputs(self, record: Any) -> dict[str, Any]:
        """The fields the step reads. The record is due again when they change."""
        ...

    def run(self, session: Session, record: Any, client: Any) -> WorkOutcome:
        """Process one record and store its result in the session. Done or nothing found;
        a failure is raised."""
        ...


def by_name(steps: Sequence[Step]) -> dict[str, Step]:
    """The steps by name. Refuses when two share one."""
    named: dict[str, Step] = {}
    for step in steps:
        if step.name in named:
            raise DuplicateStep(f"Two steps are named '{step.name}'. Each step needs its own name.")
        named[step.name] = step
    return named


def find_step(steps: Sequence[Step], name: str) -> Step:
    named = by_name(steps)
    if name not in named:
        known = ", ".join(sorted(named)) or "none"
        raise UnknownStep(f"No step is named '{name}'. Steps: {known}.")
    return named[name]
