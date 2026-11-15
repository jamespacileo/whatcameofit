"""Working through a step's due records, one record per transaction.
Behavior: openspec work-ledger."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlalchemy.orm import Session

from thenwhat.backfill.errors import SourceStop
from thenwhat.backfill.ledger import count, due_records, record_outcome
from thenwhat.backfill.steps import (
    BatchStep,
    CountingClient,
    Deferred,
    Failed,
    Step,
    batch_size_of,
)
from thenwhat.domain import WorkOutcome

OpenSession = Callable[[], AbstractContextManager[Session]]
# How many failures' errors a run's report carries. The ledger keeps every one.
ERRORS_KEPT = 50
# A record's id, its outcome and its error. The outcome is None for a record that
# another run finished first, and Deferred for one that may not be worked on now.
Processed = tuple[int, WorkOutcome | Deferred | None, str | None]


@dataclass(slots=True)
class RunReport:
    done: int = 0
    nothing_found: int = 0
    failed: int = 0
    # Records the source said could not be asked for now: no outcome, no attempt.
    deferred: int = 0
    remaining_due: int = 0
    # Why the run ended before its records ran out, in words for the operator.
    stopped: str | None = None
    # The error of each record that failed in this run.
    errors: list[str] | None = None

    @property
    def processed(self) -> int:
        return self.done + self.nothing_found + self.failed


def process_next(
    session: Session,
    step: Step,
    client: CountingClient,
    *,
    now: datetime,
    attempt_limit: int,
    skip: set[int],
) -> Processed | None:
    """Process one due record that no other run is holding, in the caller's transaction.

    The record's row is locked until the transaction ends, and other runs skip locked
    rows, so no record is processed twice. The step's result and the ledger entry are
    written in the same transaction: both are saved or neither is. A failure undoes
    whatever the step had written and is recorded in the entry. Returns the record's
    id, its outcome and its error, or None when nothing is due. The outcome is None for
    a record that another run finished first.
    """
    query = due_records(step, attempt_limit)
    if skip:
        query = query.where(step.model.id.not_in(skip.copy()))
    record = session.scalars(
        query.limit(1).with_for_update(skip_locked=True, of=step.model)
    ).first()
    if record is None:
        return None
    if record.id in skip:
        return record.id, None, None
    # Another run may have finished this record between this query's view of the ledger
    # and the moment its row lock was free. The lock is now held, so look again.
    still_due = session.scalar(
        due_records(step, attempt_limit)
        .where(step.model.id == record.id)
        .with_only_columns(step.model.id)
    )
    if still_due is None:
        return record.id, None, None
    return _process_record(session, step, record, client, now)


def _outcome_of(answer: "WorkOutcome | Failed") -> tuple[WorkOutcome, str | None]:
    """A step's answer as an outcome and its error. A failure the step returns keeps
    what the step wrote; one it raises does not."""
    if isinstance(answer, Failed):
        return WorkOutcome.FAILED, answer.error[:2000]
    return answer, None


def _process_record(
    session: Session, step: Step, record: Any, client: CountingClient, now: datetime
) -> Processed:
    """Run the step for one record whose row is held, and write its entry. A failure
    undoes what the step wrote for it and is recorded in the entry."""
    before = client.requests_made
    error: str | None = None
    try:
        with session.begin_nested():
            answer = step.run(session, record, client)
            if isinstance(answer, Deferred):
                # Nothing is written for it: it stays due with its attempts unchanged.
                return record.id, answer, answer.reason
            outcome, error = _outcome_of(answer)
    except SourceStop:
        raise
    except Exception as failure:  # one record's failure must not end the run
        outcome = WorkOutcome.FAILED
        error = f"{type(failure).__name__}: {failure}"[:2000]
    record_outcome(
        session,
        step,
        record,
        outcome,
        requests_used=client.requests_made - before,
        now=now,
        error=error,
    )
    return record.id, outcome, error


def process_batch(
    session: Session,
    step: Step,
    client: CountingClient,
    *,
    now: datetime,
    attempt_limit: int,
    skip: set[int],
    size: int,
) -> list[Processed] | None:
    """Process up to `size` due records in one call of the step, in the caller's
    transaction, so their results and entries are saved together or not at all.

    The records' rows are held as one record's is. When the call fails, whatever it
    wrote is undone and the same records are processed one at a time, so that only a
    record that fails alone has a failure recorded. Returns what became of each record,
    or None when nothing is due.
    """
    query = due_records(step, attempt_limit)
    if skip:
        query = query.where(step.model.id.not_in(skip.copy()))
    records = list(
        session.scalars(query.limit(size).with_for_update(skip_locked=True, of=step.model))
    )
    if not records:
        return None
    still_due = set(
        session.scalars(
            due_records(step, attempt_limit)
            .where(step.model.id.in_([record.id for record in records]))
            .with_only_columns(step.model.id)
        )
    )
    held = [record for record in records if record.id in still_due and record.id not in skip]
    processed: list[Processed] = [
        (record.id, None, None)
        for record in records
        if record.id not in still_due or record.id in skip
    ]
    if not held:
        return processed
    before = client.requests_made
    try:
        with session.begin_nested():
            outcomes = list(cast(BatchStep, step).run_many(session, held, client))
            if len(outcomes) != len(held):
                raise ValueError(f"The step answered for {len(outcomes)} of {len(held)} records.")
    except SourceStop:
        raise
    except Exception:  # the call failed as a whole: find the record that fails alone
        processed.extend(_process_record(session, step, record, client, now) for record in held)
        return processed
    used = client.requests_made - before
    for place, (record, answer) in enumerate(zip(held, outcomes, strict=True)):
        outcome, error = _outcome_of(answer)
        # A call's requests cannot be split between its records: the first carries them.
        record_outcome(
            session,
            step,
            record,
            outcome,
            requests_used=used if place == 0 else 0,
            now=now,
            error=error,
        )
        processed.append((record.id, outcome, error))
    return processed


def run_step(
    open_session: OpenSession,
    step: Step,
    client: CountingClient,
    *,
    now: Callable[[], datetime],
    attempt_limit: int,
    limit: int | None = None,
    before_call: Callable[[Session], None] | None = None,
    tried: set[int] | None = None,
) -> RunReport:
    """Process due records until none is due, the limit is reached or the source may
    not be asked. Each call of the step is its own transaction, so a run can be stopped
    anywhere and started again without repeating a finished record.

    `before_call` runs ahead of each call and may raise a `SourceStop`, which ends the
    run with the records still due: a model step's spend ceiling is checked this way.
    """
    report = RunReport(errors=[])
    if tried is None:
        tried = set()
    size = batch_size_of(step)
    while limit is None or report.processed < limit:
        try:
            with open_session() as session:
                if before_call is not None:
                    before_call(session)
                if size == 1:
                    one = process_next(
                        session, step, client, now=now(), attempt_limit=attempt_limit, skip=tried
                    )
                    processed = None if one is None else [one]
                else:
                    room = size if limit is None else min(size, limit - report.processed)
                    processed = process_batch(
                        session,
                        step,
                        client,
                        now=now(),
                        attempt_limit=attempt_limit,
                        skip=tried,
                        size=room,
                    )
                # Remember retryable records before releasing their row locks, so
                # another worker in this run cannot pick them immediately.
                for record_id, outcome, _ in processed or []:
                    if isinstance(outcome, Deferred) or outcome is WorkOutcome.FAILED:
                        tried.add(record_id)
        except SourceStop as stop:
            report.stopped = str(stop)
            break
        if processed is None:
            break
        for record_id, outcome, error in processed:
            if outcome is None:
                continue
            if isinstance(outcome, Deferred):
                # Not picked again in this run, so the run goes on with other records.
                tried.add(record_id)
                report.deferred += 1
                continue
            if outcome is WorkOutcome.DONE:
                report.done += 1
            elif outcome is WorkOutcome.NOTHING_FOUND:
                report.nothing_found += 1
            else:
                # A failed record stays due, so this run must not pick it again. A
                # finished one is no longer due and needs no remembering: a run over
                # hundreds of thousands of records would otherwise carry them all into
                # every query.
                tried.add(record_id)
                report.failed += 1
                if error and report.errors is not None and len(report.errors) < ERRORS_KEPT:
                    report.errors.append(error)
    with open_session() as session:
        report.remaining_due = count(session, step, attempt_limit).due
    return report
