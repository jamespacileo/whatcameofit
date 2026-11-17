"""The work ledger: which step is finished for which record, and what is still due.
Behavior: openspec work-ledger."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, func, not_, or_, select
from sqlalchemy.orm import Session

from thenwhat.db.models import WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.work.steps import Step

FINISHED = (WorkOutcome.DONE, WorkOutcome.NOTHING_FOUND)


def fingerprint(inputs: dict[str, Any]) -> str:
    """A hash of what a step read from a record."""
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, default=str).encode()).hexdigest()


def _entry_of(step: Step) -> ColumnElement[bool]:
    return and_(
        WorkEntry.record_kind == step.record_kind,
        WorkEntry.record_id == step.model.id,
        WorkEntry.step == step.name,
        WorkEntry.step_version == step.version,
    )


def _is_due(attempt_limit: int) -> ColumnElement[bool]:
    return or_(
        WorkEntry.id.is_(None),
        WorkEntry.stale,
        and_(WorkEntry.outcome == WorkOutcome.FAILED, WorkEntry.attempts < attempt_limit),
    )


def _first_of(step: Step) -> ColumnElement[bool] | None:
    """The condition of the records a step wants before every other, if it names one."""
    first = getattr(step, "first", None)
    return first() if first is not None else None


def _due(step: Step, attempt_limit: int, *, first_leads: bool) -> Select[Any]:
    order = getattr(step, "order", None)
    first = _first_of(step) if first_leads else None
    return (
        select(step.model)
        .outerjoin(WorkEntry, _entry_of(step))
        .where(step.scope(), _is_due(attempt_limit))
        # A step may say which due records come first; the record's id settles the rest.
        .order_by(
            *(() if first is None else (first.desc(),)),
            *(order() if order is not None else ()),
            step.model.id,
        )
    )


def due_records(step: Step, attempt_limit: int) -> Select[Any]:
    """The records in the step's scope with no finished entry at its current version, or
    whose input changed since. A record that failed stays due until its attempts run out."""
    return _due(step, attempt_limit, first_leads=True)


# Set on a step once a run has found fewer of its first records due than it asked for.
_FIRST_RAN_OUT = "_first_ran_out"


def take_due(
    session: Session, step: Step, attempt_limit: int, *, size: int, skip: set[int]
) -> list[Any]:
    """Up to `size` due records that no other run holds, in the step's order, their rows
    held until the transaction ends.

    The records a step wants first are asked for on their own, and the rest by id. Asked
    for as one list, every due record had to be weighed and sorted before each pick:
    nine seconds for twenty of 145,000 due headlines, measured on 2026-11-16. Once the
    first records run out the step is not asked for them again in this run: one that
    becomes due later takes its turn by id.
    """

    def held(query: Select[Any], limit: int) -> list[Any]:
        if skip:
            query = query.where(step.model.id.not_in(skip.copy()))
        return list(
            session.scalars(query.limit(limit).with_for_update(skip_locked=True, of=step.model))
        )

    rest = _due(step, attempt_limit, first_leads=False)
    first = _first_of(step)
    if first is None or getattr(step, _FIRST_RAN_OUT, False):
        return held(rest, size)
    found = held(rest.where(first), size)
    if len(found) < size:
        setattr(step, _FIRST_RAN_OUT, True)
        others = rest.where(not_(first), step.model.id.not_in([one.id for one in found]))
        found += held(others, size - len(found))
    return found


@dataclass(frozen=True, slots=True)
class StepCounts:
    in_scope: int
    done: int
    nothing_found: int
    failed: int
    due: int
    # Failed as often as the limit allows: skipped until someone looks.
    needs_attention: int

    @property
    def processed(self) -> int:
        return self.done + self.nothing_found


def count(session: Session, step: Step, attempt_limit: int) -> StepCounts:
    """Where a step stands. Entries are counted through their record, so an entry whose
    record is gone or out of scope is never counted as work done."""
    current = and_(WorkEntry.id.is_not(None), WorkEntry.stale.is_(False))

    def tally(condition: ColumnElement[bool]) -> Any:
        return func.count().filter(condition)

    row = session.execute(
        select(
            func.count(),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.DONE)),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.NOTHING_FOUND)),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.FAILED)),
            tally(_is_due(attempt_limit)),
            tally(
                and_(
                    current,
                    WorkEntry.outcome == WorkOutcome.FAILED,
                    WorkEntry.attempts >= attempt_limit,
                )
            ),
        )
        .select_from(step.model)
        .outerjoin(WorkEntry, _entry_of(step))
        .where(step.scope())
    ).one()
    return StepCounts(*row)


def find_entry(session: Session, step: Step, record: Any) -> WorkEntry | None:
    return session.scalars(
        select(WorkEntry).where(
            WorkEntry.record_kind == step.record_kind,
            WorkEntry.record_id == record.id,
            WorkEntry.step == step.name,
            WorkEntry.step_version == step.version,
        )
    ).one_or_none()


def record_outcome(
    session: Session,
    step: Step,
    record: Any,
    outcome: WorkOutcome,
    *,
    requests_used: int,
    now: datetime,
    error: str | None = None,
) -> WorkEntry:
    """Write the one entry a record has for a step at its version. A second attempt
    updates it. An entry made for an earlier input starts its attempts again."""
    entry = find_entry(session, step, record)
    if entry is None:
        entry = WorkEntry(
            record_kind=step.record_kind,
            record_id=record.id,
            step=step.name,
            step_version=step.version,
            attempts=0,
            requests_used=0,
        )
        session.add(entry)
    elif entry.stale:
        entry.attempts = 0
        entry.requests_used = 0
    entry.outcome = outcome
    entry.attempts += 1
    entry.requests_used += requests_used
    entry.fingerprint = fingerprint(step.inputs(record))
    entry.stale = False
    entry.error = error if outcome is WorkOutcome.FAILED else None
    entry.last_attempt_at = now
    session.flush()
    return entry


def mark_changed(session: Session, steps: Sequence[Step], record_kind: str, record: Any) -> None:
    """Call after a record's fields change. Each step that read a field which is now
    different has its entry marked stale, so the record is due for that step again.
    A step whose inputs are unchanged is left alone."""
    for step in steps:
        if step.record_kind != record_kind:
            continue
        entry = find_entry(session, step, record)
        if entry is not None and entry.fingerprint != fingerprint(step.inputs(record)):
            entry.stale = True
    session.flush()
