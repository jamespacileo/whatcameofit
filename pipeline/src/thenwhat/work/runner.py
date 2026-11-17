"""Working through a step's due records, one record per transaction.
Behavior: openspec work-ledger."""

from collections import Counter
from collections.abc import Callable, Generator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy.orm import Session

from thenwhat.domain import WorkOutcome
from thenwhat.measure import events
from thenwhat.measure import spans as measure
from thenwhat.measure.events import RunEnd
from thenwhat.work.errors import SourceStop, SpendCeilingReached
from thenwhat.work.ledger import PUT_OFF_SPAN, count, due_records, record_outcome, take_due
from thenwhat.work.outcome import Later, NeedsFix, NothingFound, ReasonClass, check_declared
from thenwhat.work.steps import (
    BatchStep,
    CountingClient,
    Deferred,
    Failed,
    Step,
    batch_size_of,
)

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
    # Records put off until a time, and records that wait for something to be fixed:
    # each has an entry that says why, and neither counts an attempt.
    later: int = 0
    needs_fix: int = 0
    remaining_due: int = 0
    # Why the run ended before its records ran out, in words for the operator.
    stopped: str | None = None
    # The error of each record that failed in this run.
    errors: list[str] | None = None
    # Why the run ended, as a code.
    ended: RunEnd | None = None
    # Measurements that could not be written while the run worked.
    not_written: int = 0

    @property
    def processed(self) -> int:
        return self.done + self.nothing_found + self.failed + self.needs_fix


@dataclass(slots=True, eq=False)
class Run:
    """One run of a step as its measurements and events name it: made once for a
    command and shared by its workers, each of which adds its report."""

    id: str
    step: str
    reports: list[RunReport] = field(default_factory=list)
    not_written: int = 0

    def why(self) -> RunEnd:
        """Why the run ended: a source or the ceiling that stopped any worker, else the
        limit, else nothing left due."""
        ends = {report.ended for report in self.reports}
        for why in (RunEnd.SPEND_CEILING, RunEnd.CANNOT_ASK, RunEnd.LIMIT):
            if why in ends:
                return why
        return RunEnd.NOTHING_DUE

    def counts(self, *, finished: bool) -> dict[str, int]:
        """The run's records by what became of them, and, for a run that finished its
        loop, how many stay due."""
        counts = {
            name: sum(getattr(report, name) for report in self.reports)
            for name in ("done", "nothing_found", "later", "needs_fix", "failed", "deferred")
        }
        if finished and self.reports:
            counts["still_due"] = min(report.remaining_due for report in self.reports)
        return counts


@contextmanager
def measured_run(step: str, *, limit: int | None, workers: int) -> Generator[Run]:
    """Record a run's start and its end, with why it ended and its counts. A run ended
    with Ctrl-C is recorded as stopped by the operator, without the records still due,
    which were not counted."""
    run = Run(id=events.new_run(), step=step)
    events.run_started(run.id, step, limit=limit, workers=workers)
    lost_before = measure.not_written()
    why, error_kind = RunEnd.OPERATOR, None
    try:
        yield run
        why = run.why()
    except Exception as failure:
        why, error_kind = RunEnd.FAILED, type(failure).__name__
        raise
    finally:
        # Written out first, so the run can say what could not be.
        run.not_written = measure.flush() - lost_before
        finished = why not in (RunEnd.OPERATOR, RunEnd.FAILED)
        events.run_ended(
            run.id,
            step,
            why=why,
            counts=run.counts(finished=finished),
            not_written=run.not_written,
            error_kind=error_kind,
        )


def process_next(
    session: Session,
    step: Step,
    client: CountingClient,
    *,
    now: datetime,
    attempt_limit: int,
    skip: set[int],
    put_off_span: timedelta = PUT_OFF_SPAN,
    run: str | None = None,
) -> Processed | None:
    """Process one due record that no other run is holding, in the caller's transaction.

    The record's row is locked until the transaction ends, and other runs skip locked
    rows, so no record is processed twice. The step's result and the ledger entry are
    written in the same transaction: both are saved or neither is. A failure undoes
    whatever the step had written and is recorded in the entry. Returns the record's
    id, its outcome and its error, or None when nothing is due. The outcome is None for
    a record that another run finished first.
    """
    taken = take_due(session, step, attempt_limit, size=1, skip=skip, now=now)
    if not taken:
        return None
    record = taken[0]
    if record.id in skip:
        return record.id, None, None
    # Another run may have finished this record between this query's view of the ledger
    # and the moment its row lock was free. The lock is now held, so look again.
    still_due = session.scalar(
        due_records(step, attempt_limit, now=now)
        .where(step.model.id == record.id)
        .with_only_columns(step.model.id)
    )
    if still_due is None:
        return record.id, None, None
    return _process_record(session, step, record, client, now, put_off_span, run)


# How a measurement names a record that may not be worked on now.
DEFERRED = "deferred"
# The class a measurement gives each outcome. A deferred record comes back by itself.
_CLASS_OF = {
    WorkOutcome.DONE: ReasonClass.FINAL.value,
    WorkOutcome.NOTHING_FOUND: ReasonClass.FINAL.value,
    WorkOutcome.LATER: ReasonClass.LATER.value,
    WorkOutcome.NEEDS_FIX: ReasonClass.NEEDS_FIX.value,
    WorkOutcome.FAILED: measure.FAILED,
}


def _trace_of(record: Any) -> str | None:
    """What a measurement says a record is: a link lead's address key. Other kinds of
    record are measured without one."""
    key = getattr(record, "url_key", None)
    return key if isinstance(key, str) else None


@dataclass(frozen=True, slots=True)
class _Settled:
    """A step's answer as the ledger records it."""

    outcome: WorkOutcome
    error: str | None = None
    reason: str | None = None
    values: Mapping[str, Any] | None = None
    not_before: datetime | None = None


def _settle(step: Step, answer: Any) -> _Settled:
    """A step's answer as an outcome with its error or its reason. A failure the step
    returns keeps what the step wrote; one it raises does not. An answer with a reason
    the step has not declared is refused, which fails the record."""
    if isinstance(answer, Failed):
        return _Settled(WorkOutcome.FAILED, error=answer.error[:2000])
    if isinstance(answer, NothingFound | Later | NeedsFix):
        check_declared(step, answer)
        code, values = answer.reason.code, answer.values
        if isinstance(answer, Later):
            return _Settled(
                WorkOutcome.LATER, reason=code, values=values, not_before=answer.not_before
            )
        if isinstance(answer, NeedsFix):
            return _Settled(WorkOutcome.NEEDS_FIX, reason=code, values=values)
        return _Settled(WorkOutcome.NOTHING_FOUND, reason=code, values=values)
    return _Settled(answer)


def _record(
    session: Session,
    step: Step,
    record: Any,
    settled: _Settled,
    *,
    requests_used: int,
    now: datetime,
    put_off_span: timedelta,
) -> WorkOutcome:
    """Write the record's entry, and give the outcome it holds: a record put off for too
    long is recorded as needing a fix."""
    return record_outcome(
        session,
        step,
        record,
        settled.outcome,
        requests_used=requests_used,
        now=now,
        error=settled.error,
        reason=settled.reason,
        reason_values=settled.values,
        not_before=settled.not_before,
        put_off_span=put_off_span,
    ).outcome


def _process_record(
    session: Session,
    step: Step,
    record: Any,
    client: CountingClient,
    now: datetime,
    put_off_span: timedelta = PUT_OFF_SPAN,
    run: str | None = None,
) -> Processed:
    """Run the step for one record whose row is held, and write its entry. A failure
    undoes what the step wrote for it and is recorded in the entry. The record's
    measurement ends with the outcome its entry holds, its class and its reason."""
    before = client.requests_made
    with measure.measured(
        step.name, version=step.version, trace=_trace_of(record), run=run
    ) as span:
        try:
            with session.begin_nested():
                answer = step.run(session, record, client)
                if isinstance(answer, Deferred):
                    # Nothing is written for it: it stays due with its attempts unchanged.
                    span.ended(DEFERRED, outcome_class=ReasonClass.LATER.value)
                    return record.id, answer, answer.reason
                settled = _settle(step, answer)
        except SourceStop:
            raise
        except Exception as failure:  # one record's failure must not end the run
            settled = _Settled(
                WorkOutcome.FAILED, error=f"{type(failure).__name__}: {failure}"[:2000]
            )
            span.span.error_kind = type(failure).__name__
        outcome = _record(
            session,
            step,
            record,
            settled,
            requests_used=client.requests_made - before,
            now=now,
            put_off_span=put_off_span,
        )
        span.ended(outcome.value, outcome_class=_CLASS_OF[outcome], reason=settled.reason)
    return record.id, outcome, settled.error


def process_batch(
    session: Session,
    step: Step,
    client: CountingClient,
    *,
    now: datetime,
    attempt_limit: int,
    skip: set[int],
    size: int,
    put_off_span: timedelta = PUT_OFF_SPAN,
    run: str | None = None,
) -> list[Processed] | None:
    """Process up to `size` due records in one call of the step, in the caller's
    transaction, so their results and entries are saved together or not at all.

    The records' rows are held as one record's is. When the call fails, whatever it
    wrote is undone and the same records are processed one at a time, so that only a
    record that fails alone has a failure recorded. Returns what became of each record,
    or None when nothing is due.
    """
    records = take_due(session, step, attempt_limit, size=size, skip=skip, now=now)
    if not records:
        return None
    still_due = set(
        session.scalars(
            due_records(step, attempt_limit, now=now)
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
    traces = [trace for record in held if (trace := _trace_of(record)) is not None]
    # One call answers for all of them, so it is one measurement that names each.
    with measure.measured(
        step.name, version=step.version, batch=len(held), traces=traces, run=run
    ) as span:
        try:
            with session.begin_nested():
                outcomes = list(cast(BatchStep, step).run_many(session, held, client))
                if len(outcomes) != len(held):
                    raise ValueError(
                        f"The step answered for {len(outcomes)} of {len(held)} records."
                    )
                answers = [_settle(step, answer) for answer in outcomes]
        except SourceStop:
            raise
        except Exception as failure:  # the call failed as a whole
            span.ended(measure.FAILED, outcome_class=measure.FAILED)
            span.span.error_kind = type(failure).__name__
            answers = None
        if answers is not None:
            used = client.requests_made - before
            recorded: list[WorkOutcome] = []
            for place, (record, settled) in enumerate(zip(held, answers, strict=True)):
                # A call's requests cannot be split between its records: the first
                # carries them.
                outcome = _record(
                    session,
                    step,
                    record,
                    settled,
                    requests_used=used if place == 0 else 0,
                    now=now,
                    put_off_span=put_off_span,
                )
                recorded.append(outcome)
                processed.append((record.id, outcome, settled.error))
            by_outcome = Counter(recorded)
            most = by_outcome.most_common(1)[0][0]
            reasons = {settled.reason for settled in answers}
            span.ended(
                most.value,
                outcome_class=_CLASS_OF[most],
                reason=reasons.pop() if len(reasons) == 1 else None,
                outcomes={outcome.value: n for outcome, n in by_outcome.items()},
            )
    if answers is None:
        # Find the record that fails alone, each measured as its own.
        processed.extend(
            _process_record(session, step, record, client, now, put_off_span, run)
            for record in held
        )
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
    put_off_span: timedelta = PUT_OFF_SPAN,
    run: Run | None = None,
) -> RunReport:
    """Process due records until none is due, the limit is reached or the source may
    not be asked. Each call of the step is its own transaction, so a run can be stopped
    anywhere and started again without repeating a finished record.

    `before_call` runs ahead of each call and may raise a `SourceStop`, which ends the
    run with the records still due: a model step's spend ceiling is checked this way.

    Every record is measured as part of `run`. A command whose workers share one run
    makes it with `measured_run`; without one, this call is a run of its own and records
    its start and its end.
    """
    if run is None:
        with measured_run(step.name, limit=limit, workers=1) as own:
            report = run_step(
                open_session,
                step,
                client,
                now=now,
                attempt_limit=attempt_limit,
                limit=limit,
                before_call=before_call,
                tried=tried,
                put_off_span=put_off_span,
                run=own,
            )
        report.not_written = own.not_written
        return report
    report = RunReport(errors=[])
    run.reports.append(report)
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
                        session,
                        step,
                        client,
                        now=now(),
                        attempt_limit=attempt_limit,
                        skip=tried,
                        put_off_span=put_off_span,
                        run=run.id,
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
                        put_off_span=put_off_span,
                        run=run.id,
                    )
                # Remember retryable records before releasing their row locks, so
                # another worker in this run cannot pick them immediately.
                for record_id, outcome, _ in processed or []:
                    if isinstance(outcome, Deferred) or outcome is WorkOutcome.FAILED:
                        tried.add(record_id)
        except SourceStop as stop:
            report.stopped = str(stop)
            report.ended = (
                RunEnd.SPEND_CEILING if isinstance(stop, SpendCeilingReached) else RunEnd.CANNOT_ASK
            )
            break
        if processed is None:
            report.ended = RunEnd.NOTHING_DUE
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
            elif outcome is WorkOutcome.LATER:
                # Not due until its time has passed, so the run does not pick it again
                # before then, and may once it has.
                report.later += 1
            elif outcome is WorkOutcome.NEEDS_FIX:
                report.needs_fix += 1
            else:
                # A failed record stays due, so this run must not pick it again. A
                # finished one is no longer due and needs no remembering: a run over
                # hundreds of thousands of records would otherwise carry them all into
                # every query.
                tried.add(record_id)
                report.failed += 1
                if error and report.errors is not None and len(report.errors) < ERRORS_KEPT:
                    report.errors.append(error)
    else:
        report.ended = RunEnd.LIMIT
    with open_session() as session:
        report.remaining_due = count(session, step, attempt_limit, now=now()).due
    return report
