"""The work ledger: which step is finished for which record, and what is still due.
Behavior: openspec work-ledger."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Integer,
    Select,
    and_,
    any_,
    bindparam,
    exists,
    func,
    not_,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session, aliased

from thenwhat.db.models import WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.work.steps import Step

FINISHED = (WorkOutcome.DONE, WorkOutcome.NOTHING_FOUND)
# How long a record may be put off for one reason before it is said to need a fix.
PUT_OFF_SPAN = timedelta(days=30)


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


def _is_due(attempt_limit: int, now: datetime | None = None) -> ColumnElement[bool]:
    """No entry, a stale one, a failure with attempts left, or a record put off whose
    time has passed. One that needs a fix is not due until it is made due. With no time
    given, the database's own clock says whether a put-off record's time has passed."""
    return or_(
        WorkEntry.id.is_(None),
        WorkEntry.stale,
        and_(WorkEntry.outcome == WorkOutcome.FAILED, WorkEntry.attempts < attempt_limit),
        and_(
            WorkEntry.outcome == WorkOutcome.LATER,
            WorkEntry.not_before <= (func.now() if now is None else now),
        ),
    )


def steps_before(step: Step) -> Sequence[Step]:
    """The steps that must have finished for a record before this one is due for it."""
    return tuple(getattr(step, "after", ()))


def _earlier_finished(step: Step) -> list[ColumnElement[bool]]:
    """One condition for each step this one depends on: the record has an entry for it,
    at that step's current version, that is finished and not stale. An entry is marked
    stale when the record's input for that step changes, so a record whose earlier step
    is due again waits for it."""
    conditions: list[ColumnElement[bool]] = []
    for earlier in steps_before(step):
        entry = aliased(WorkEntry)
        conditions.append(
            exists().where(
                entry.record_kind == earlier.record_kind,
                entry.record_id == step.model.id,
                entry.step == earlier.name,
                entry.step_version == earlier.version,
                entry.outcome.in_(FINISHED),
                entry.stale.is_(False),
            )
        )
    return conditions


def _first_of(step: Step) -> ColumnElement[bool] | None:
    """The condition of the records a step wants before every other, if it names one."""
    first = getattr(step, "first", None)
    return first() if first is not None else None


def _due(
    step: Step, attempt_limit: int, *, first_leads: bool, now: datetime | None = None
) -> Select[Any]:
    order = getattr(step, "order", None)
    first = _first_of(step) if first_leads else None
    return (
        select(step.model)
        .outerjoin(WorkEntry, _entry_of(step))
        .where(step.scope(), _is_due(attempt_limit, now), *_earlier_finished(step))
        # A step may say which due records come first; the record's id settles the rest.
        .order_by(
            *(() if first is None else (first.desc(),)),
            *(order() if order is not None else ()),
            step.model.id,
        )
    )


def due_records(step: Step, attempt_limit: int, *, now: datetime | None = None) -> Select[Any]:
    """The records in the step's scope with no finished entry at its current version, or
    whose input changed since. A record that failed stays due until its attempts run
    out, one put off is due once its time has passed, and one that needs a fix is not
    due. A record is due only when every step this one depends on has finished for it."""
    return _due(step, attempt_limit, first_leads=True, now=now)


# Set on a step once a run has found fewer of its first records due than it asked for.
_FIRST_RAN_OUT = "_first_ran_out"


def take_due(
    session: Session,
    step: Step,
    attempt_limit: int,
    *,
    size: int,
    skip: set[int],
    now: datetime | None = None,
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

    rest = _due(step, attempt_limit, first_leads=False, now=now)
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
    # Put off: comes back by itself. Needs a fix: waits to be made due.
    later: int = 0
    needs_fix: int = 0

    @property
    def processed(self) -> int:
        return self.done + self.nothing_found


def count(
    session: Session,
    step: Step,
    attempt_limit: int,
    *,
    now: datetime | None = None,
    changed_inputs: ColumnElement[bool] | None = None,
) -> StepCounts:
    """Where a step stands. Entries are counted through their record, so an entry whose
    record is gone or out of scope is never counted as work done."""
    current = and_(WorkEntry.id.is_not(None), WorkEntry.stale.is_(False))

    due = _is_due(attempt_limit, now)
    if changed_inputs is not None:
        current = and_(current, not_(changed_inputs))
        due = or_(due, changed_inputs)

    def tally(condition: ColumnElement[bool]) -> Any:
        return func.count().filter(condition)

    row = session.execute(
        select(
            func.count(),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.DONE)),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.NOTHING_FOUND)),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.FAILED)),
            tally(and_(due, *_earlier_finished(step))),
            tally(
                and_(
                    current,
                    WorkEntry.outcome == WorkOutcome.FAILED,
                    WorkEntry.attempts >= attempt_limit,
                )
            ),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.LATER)),
            tally(and_(current, WorkEntry.outcome == WorkOutcome.NEEDS_FIX)),
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
    reason: str | None = None,
    reason_values: Mapping[str, Any] | None = None,
    not_before: datetime | None = None,
    put_off_span: timedelta = PUT_OFF_SPAN,
) -> WorkEntry:
    """Write the one entry a record has for a step at its version. A second attempt
    updates it. An entry made for an earlier input starts its attempts again.

    An outcome of later or needs a fix counts no attempt. A record put off for one
    reason for longer than the span is recorded as needing a fix for that reason."""
    if outcome is WorkOutcome.LATER and (not_before is None or not_before <= now):
        raise ValueError("A record put off needs a time that has not yet come.")
    if outcome in (WorkOutcome.LATER, WorkOutcome.NEEDS_FIX) and not reason:
        raise ValueError("A record that is put off or needs a fix needs a reason.")
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
    first_put_off_at: datetime | None = None
    if outcome is WorkOutcome.LATER:
        same = entry.outcome is WorkOutcome.LATER and entry.reason == reason and not entry.stale
        first_put_off_at = (entry.first_put_off_at if same else None) or now
        if now - first_put_off_at > put_off_span:
            outcome, not_before = WorkOutcome.NEEDS_FIX, None
    if outcome not in (WorkOutcome.LATER, WorkOutcome.NEEDS_FIX):
        entry.attempts += 1
    entry.outcome = outcome
    entry.reason = reason
    entry.reason_values = dict(reason_values) if reason_values else None
    entry.not_before = not_before if outcome is WorkOutcome.LATER else None
    entry.first_put_off_at = first_put_off_at
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


@dataclass(frozen=True, slots=True)
class Waiting:
    """How many of a step's records wait for one reason, and until when the first of
    those put off is due."""

    outcome: WorkOutcome
    reason: str
    records: int
    first_due_at: datetime | None


def waiting(session: Session, step: Step) -> list[Waiting]:
    """The step's records that are put off or need a fix, by class and reason: those put
    off first, then the reason most records wait for."""
    rows = session.execute(
        select(WorkEntry.outcome, WorkEntry.reason, func.count(), func.min(WorkEntry.not_before))
        .select_from(step.model)
        .join(WorkEntry, _entry_of(step))
        .where(
            step.scope(),
            WorkEntry.stale.is_(False),
            WorkEntry.outcome.in_((WorkOutcome.LATER, WorkOutcome.NEEDS_FIX)),
        )
        .group_by(WorkEntry.outcome, WorkEntry.reason)
        .order_by(WorkEntry.outcome, func.count().desc(), WorkEntry.reason)
    )
    return [
        Waiting(outcome, reason or "", records, first) for outcome, reason, records, first in rows
    ]


def requeue(
    session: Session,
    step: Step,
    *,
    reason: str | None = None,
    values: Mapping[str, Any] | None = None,
    failed: bool = False,
    attempt_limit: int | None = None,
    dry_run: bool = False,
) -> list[int]:
    """Make due the step's records whose entry holds this reason, or, with `failed`,
    those that failed as often as the limit allows. `values` narrows a reason to the
    entries that carry each of them: one outlet, one status. Returns the records' ids.

    The entries are marked stale, as the ledger marks a record whose input changed: each
    stays, with its last attempt, until the record is worked on again, and its attempts
    then start from none. Asks nothing and, with `dry_run`, changes nothing."""
    if (reason is None) == (not failed):
        raise ValueError("Records are made due by a reason or as failed, one of the two.")
    wanted = [WorkEntry.stale.is_(False)]
    if failed:
        wanted.append(WorkEntry.outcome == WorkOutcome.FAILED)
        if attempt_limit is not None:
            wanted.append(WorkEntry.attempts >= attempt_limit)
    else:
        wanted.append(WorkEntry.reason == reason)
        if values:
            wanted.append(WorkEntry.reason_values.contains(dict(values)))
    # Lock the same records first as a worker taking a batch. The step can then
    # clear its lead outcomes in this transaction without racing the next retry.
    candidates = (
        select(WorkEntry.id, WorkEntry.record_id)
        .join(step.model, _entry_of(step))
        .where(*wanted)
        .order_by(WorkEntry.record_id)
    )
    if dry_run:
        return [row.record_id for row in session.execute(candidates)]
    entry_ids = list(session.scalars(candidates.with_for_update(of=step.model)))
    if not entry_ids:
        return []
    # A worker could have finished while the record lock was being acquired.
    changed = session.scalars(
        update(WorkEntry)
        .where(
            WorkEntry.id == any_(bindparam("entry_ids", entry_ids, type_=ARRAY(Integer))), *wanted
        )
        .values(stale=True, attempts=0)
        .returning(WorkEntry.record_id)
    )
    return sorted(changed)
