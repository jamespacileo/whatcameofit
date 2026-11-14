"""Working through a step's due records, one record per transaction.
Behavior: openspec work-ledger."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from thenwhat.backfill.errors import SourceStop
from thenwhat.backfill.ledger import count, due_records, record_outcome
from thenwhat.backfill.steps import CountingClient, Step
from thenwhat.domain import WorkOutcome

OpenSession = Callable[[], AbstractContextManager[Session]]


@dataclass(slots=True)
class RunReport:
    done: int = 0
    nothing_found: int = 0
    failed: int = 0
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
) -> tuple[int, WorkOutcome | None, str | None] | None:
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
        query = query.where(step.model.id.not_in(skip))
    record = session.scalars(
        query.limit(1).with_for_update(skip_locked=True, of=step.model)
    ).first()
    if record is None:
        return None
    # Another run may have finished this record between this query's view of the ledger
    # and the moment its row lock was free. The lock is now held, so look again.
    still_due = session.scalar(
        due_records(step, attempt_limit)
        .where(step.model.id == record.id)
        .with_only_columns(step.model.id)
    )
    if still_due is None:
        return record.id, None, None
    before = client.requests_made
    error: str | None = None
    try:
        with session.begin_nested():
            outcome = step.run(session, record, client)
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


def run_step(
    open_session: OpenSession,
    step: Step,
    client: CountingClient,
    *,
    now: Callable[[], datetime],
    attempt_limit: int,
    limit: int | None = None,
) -> RunReport:
    """Process due records until none is due, the limit is reached or the source may
    not be asked. Each record is its own transaction, so a run can be stopped anywhere
    and started again without repeating a finished record."""
    report = RunReport(errors=[])
    tried: set[int] = set()
    while limit is None or report.processed < limit:
        try:
            with open_session() as session:
                processed = process_next(
                    session, step, client, now=now(), attempt_limit=attempt_limit, skip=tried
                )
        except SourceStop as stop:
            report.stopped = str(stop)
            break
        if processed is None:
            break
        record_id, outcome, error = processed
        tried.add(record_id)
        if outcome is None:
            continue
        if outcome is WorkOutcome.DONE:
            report.done += 1
        elif outcome is WorkOutcome.NOTHING_FOUND:
            report.nothing_found += 1
        else:
            report.failed += 1
            if error and report.errors is not None:
                report.errors.append(error)
    with open_session() as session:
        report.remaining_due = count(session, step, attempt_limit).due
    return report
