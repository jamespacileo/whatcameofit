"""The shape of a step: one kind of processing applied to one kind of record.
Behavior: openspec work-ledger."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import DuplicateStep, UnknownStep
from thenwhat.domain import WorkOutcome

# What a step gives as its source when it asks none: it reads the database only.
NO_SOURCE = "none"
# What a step gives as its source when it calls a model in place of asking a source.
MODEL = "model"

# Which door a step's model calls go through, and so which prices apply.
DECISION_DOOR = "decision"
TEXT_DOOR = "text"


@dataclass(frozen=True, slots=True)
class ModelSpend:
    """What one record costs a step that calls a model, as an estimate for the plan."""

    input_tokens: int
    output_tokens: int = 0
    door: str = DECISION_DOOR


@dataclass(frozen=True, slots=True)
class Failed:
    """A step's answer for a record it could not finish, when what it wrote about the
    failure must be kept: a logged decision, a recorded cost. A failure that is raised
    undoes what the step wrote; this one does not."""

    error: str


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

    def run(self, session: Session, record: Any, client: Any) -> "WorkOutcome | Failed":
        """Process one record and store its result in the session. Done or nothing found;
        a failure is raised, or returned as `Failed` to keep what was written."""
        ...


class BatchStep(Step, Protocol):
    """A step that can process several records in one call."""

    batch_size: int

    def run_many(
        self, session: Session, records: Sequence[Any], client: Any
    ) -> "Sequence[WorkOutcome | Failed]":
        """Process the records together and give each one's outcome, in order. A failure
        is raised, and the records are then processed one at a time with `run`."""
        ...


def asks_a_source(step: Step) -> bool:
    """Whether the step's requests go to a source that has an allowance."""
    return step.source not in (NO_SOURCE, MODEL)


def model_spend_of(step: Step) -> ModelSpend | None:
    """The step's estimate of a record's model cost, or None when it calls no model."""
    return getattr(step, "model_spend", None)


def batch_size_of(step: Step) -> int:
    """How many records the step takes in one call: one unless it declares more."""
    return max(int(getattr(step, "batch_size", 1)), 1)


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
