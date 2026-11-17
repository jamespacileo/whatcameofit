"""One measurement of one step: a span, and the other lines a day's file holds.
Behavior: openspec processing-metrics.

The work ledger's runner opens the span around each record (or each batch) and closes
it with the outcome's class and reason, so a step run by it is measured without its
code saying so. Work outside the runner (a decision inside a step, a claim's own
command) opens its own with `measured` or `measuring`. While a span is open, the places
every step passes through (a model call's cost, a request to a source, a wait for a
turn) add to it, so no step counts its own tokens, requests or waits. When nothing is
recording, all of this does nothing.

A span holds the step and what it worked on: an article's address key or a claim's
slug. It never holds anything about a reader.

Beside finished spans a recorder hands on two other kinds of line, each an `Event`: a
start line when a span opens with none around it, so another process can see what is in
hand, and the events of a run (`measure.events`). Both are held to an allow-list as a
span is.
"""

import itertools
import threading
import time as system_time
import uuid
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import wraps
from typing import Any, Protocol

# Outcomes a step's own code does not give.
FAILED = "failed"
BATCH_RETRY = "batch_retry"
DONE = "done"

# What a span may hold. Anything else handed in is refused, so a field that could carry
# something about a reader cannot be added by passing it along.
FIELDS = frozenset(
    {
        "step",
        "step_version",
        "writer",
        "trace",
        "traces",
        "batch",
        "started_at",
        "ended_at",
        "ran_seconds",
        "waited",
        "outcome",
        "outcome_class",
        "outcomes",
        "reason",
        "error_kind",
        "reused",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "inner_cost_usd",
        "requests",
        "rows_written",
        "id",
        "run",
    }
)

# The cause a worker's wait is measured under when measurements cannot be written as
# fast as they are made, and the work waits for them.
WRITER_WAIT = "measure_writer"


@dataclass(slots=True)
class Span:
    step: str
    step_version: int
    writer: str
    # What the step worked on: an address key, or "claim:<slug>". None for a batch.
    trace: str | None
    # How many records one call covered.
    batch: int
    started_at: datetime
    # Time spent working, with time spent waiting taken out.
    ran_seconds: float = 0.0
    # Seconds waited before or during the work, by what was waited on.
    waited: dict[str, float] = field(default_factory=dict)
    outcome: str = DONE
    # The kind of failure, never its message: a message can quote what was read.
    error_kind: str | None = None
    # Whether a stored result answered the step in place of the work.
    reused: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal(0)
    # What the measurements opened inside this one cost. It is theirs in any total;
    # it is kept here so that what a whole step costs for a record can be told.
    inner_cost_usd: Decimal = Decimal(0)
    # Requests sent, by source.
    requests: dict[str, int] = field(default_factory=dict)
    rows_written: int = 0
    # For a call that covered several records: what each of them was.
    traces: list[str] = field(default_factory=list)
    # The run it belongs to, when the work ledger's runner opened it or one around it.
    run: str | None = None
    # The class of its outcome (final, later, needs_fix or failed) and its reason's code,
    # as the runner settled them. For a batch: records by outcome, and in `outcome` the
    # one most of them had.
    outcome_class: str | None = None
    reason: str | None = None
    outcomes: dict[str, int] = field(default_factory=dict)
    # Which start line this span ends. Only a span with none around it has one.
    id: str | None = None
    ended_at: datetime | None = None

    @property
    def waited_seconds(self) -> float:
        return sum(self.waited.values())

    @property
    def ended(self) -> datetime:
        """When it finished. A line written before spans said so is placed by its own
        times, which leave out what was measured inside it."""
        if self.ended_at is not None:
            return self.ended_at
        return self.started_at + timedelta(seconds=self.ran_seconds + self.waited_seconds)

    def records_by_outcome(self) -> dict[str, int]:
        if self.outcome == BATCH_RETRY:
            return {}
        return dict(self.outcomes) if self.outcomes else {self.outcome: self.batch}

    def as_record(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "step_version": self.step_version,
            "writer": self.writer,
            "trace": self.trace,
            "batch": self.batch,
            "started_at": self.started_at.isoformat(),
            "ran_seconds": self.ran_seconds,
            "waited": dict(self.waited),
            "outcome": self.outcome,
            "error_kind": self.error_kind,
            "reused": self.reused,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": str(self.cost_usd),
            "inner_cost_usd": str(self.inner_cost_usd),
            "requests": dict(self.requests),
            "rows_written": self.rows_written,
            "traces": list(self.traces),
            "run": self.run,
            "outcome_class": self.outcome_class,
            "reason": self.reason,
            "outcomes": dict(self.outcomes),
            "id": self.id,
            "ended_at": self.ended_at.isoformat() if self.ended_at is not None else None,
        }


def span_from(record: dict[str, Any]) -> Span:
    unknown = set(record) - FIELDS
    if unknown:
        raise ValueError(f"A span may not hold: {', '.join(sorted(unknown))}.")
    ended_at = record.get("ended_at")
    return Span(
        step=str(record["step"]),
        step_version=int(record["step_version"]),
        writer=str(record["writer"]),
        trace=record.get("trace"),
        batch=int(record.get("batch", 1)),
        started_at=datetime.fromisoformat(record["started_at"]),
        ran_seconds=float(record.get("ran_seconds", 0.0)),
        waited={str(k): float(v) for k, v in record.get("waited", {}).items()},
        outcome=str(record.get("outcome", DONE)),
        error_kind=record.get("error_kind"),
        reused=bool(record.get("reused", False)),
        tokens_in=int(record.get("tokens_in", 0)),
        tokens_out=int(record.get("tokens_out", 0)),
        cost_usd=Decimal(str(record.get("cost_usd", "0"))),
        inner_cost_usd=Decimal(str(record.get("inner_cost_usd", "0"))),
        requests={str(k): int(v) for k, v in record.get("requests", {}).items()},
        rows_written=int(record.get("rows_written", 0)),
        traces=[str(trace) for trace in record.get("traces", [])],
        run=record.get("run"),
        outcome_class=record.get("outcome_class"),
        reason=record.get("reason"),
        outcomes={str(k): int(v) for k, v in (record.get("outcomes") or {}).items()},
        id=record.get("id"),
        ended_at=datetime.fromisoformat(ended_at) if ended_at else None,
    )


# The kind of a span's start line.
STARTED = "started"

# What a line that is not a span may hold, beside its kind, its time and its writer. As
# for a span, anything else is refused.
EVENT_FIELDS = frozenset(
    {
        "process",
        "id",
        "run",
        "step",
        "trace",
        "batch",
        "limit",
        "workers",
        "why",
        "error_kind",
        "counts",
        "source",
        "until",
        "reason",
        "records",
        "not_written",
        "lines",
        "since",
    }
)


@dataclass(frozen=True, slots=True)
class Event:
    """A line of the day's file that is not a measurement: what happened, when, who
    wrote it, and values from the allow-list, each a plain JSON value."""

    kind: str
    at: datetime
    writer: str
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = set(self.values) - EVENT_FIELDS
        if unknown:
            raise ValueError(f"An event may not hold: {', '.join(sorted(unknown))}.")

    def as_record(self) -> dict[str, Any]:
        return {"kind": self.kind, "at": self.at.isoformat(), "writer": self.writer, **self.values}


def event_from(record: dict[str, Any]) -> Event:
    values = {k: v for k, v in record.items() if k not in ("kind", "at", "writer")}
    return Event(
        kind=str(record["kind"]),
        at=datetime.fromisoformat(record["at"]),
        writer=str(record.get("writer", "")),
        values=values,
    )


def line_from(record: dict[str, Any]) -> Span | Event:
    """A line of the day's file as what it is: a line with a kind is an event."""
    return event_from(record) if "kind" in record else span_from(record)


# This process, as start lines and span ids name it: a random token, so that a reader of
# the files can tell a process that has stopped from one still at work. Nothing about
# the machine or a person.
PROCESS = uuid.uuid4().hex[:12]
_ids = itertools.count(1)


def start_line(span: Span) -> Event:
    return Event(
        STARTED,
        span.started_at,
        span.writer,
        {
            "process": PROCESS,
            "id": span.id,
            "run": span.run,
            "step": span.step,
            "trace": span.trace,
            "batch": span.batch,
        },
    )


class Running:
    """A span while its step runs. The step says how it ended; the rest is added by the
    places the work passes through."""

    def __init__(self, span: Span) -> None:
        self.span = span
        # Time spent inside spans opened within this one, which is theirs to report.
        self.inner_seconds = 0.0
        self._lock = threading.Lock()

    def add_inner(self, seconds: float, cost_usd: Decimal = Decimal(0)) -> None:
        """Count time and cost as another measurement's: what is measured inside this
        one, or a step run as its own process, reports its own, so this one must not
        report it again."""
        with self._lock:
            if seconds > 0:
                self.inner_seconds += seconds
            self.span.inner_cost_usd += cost_usd

    def ended(
        self,
        outcome: str,
        *,
        outcome_class: str | None = None,
        reason: str | None = None,
        outcomes: Mapping[str, int] | None = None,
    ) -> None:
        self.span.outcome = outcome
        if outcome_class is not None:
            self.span.outcome_class = outcome_class
        if reason is not None:
            self.span.reason = reason
        if outcomes:
            self.span.outcomes = dict(outcomes)

    def reused(self) -> None:
        self.span.reused = True

    def wrote(self, rows: int) -> None:
        self.span.rows_written += rows

    def add_model(self, tokens_in: int, tokens_out: int, cost_usd: Decimal) -> None:
        with self._lock:
            self.span.tokens_in += tokens_in
            self.span.tokens_out += tokens_out
            self.span.cost_usd += cost_usd

    def add_request(self, source: str, count: int = 1) -> None:
        with self._lock:
            self.span.requests[source] = self.span.requests.get(source, 0) + count

    def add_wait(self, cause: str, seconds: float) -> None:
        if seconds <= 0:
            return
        with self._lock:
            self.span.waited[cause] = self.span.waited.get(cause, 0.0) + seconds


class Out(Protocol):
    """Where a recorder's lines go. Handing a line on returns the seconds the caller
    waited to do so: none, unless lines are made faster than they can be written."""

    def finished(self, span: Span) -> float: ...

    def started(self, span: Span) -> float: ...

    def event(self, event: Event) -> float: ...

    def flush(self) -> None:
        """Return once every line handed on so far is written or counted as not."""
        ...

    def not_written(self) -> int:
        """How many measurements could not be written so far."""
        ...

    def close(self) -> None: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Recorder:
    """Where finished spans and other lines go, and who is writing them."""

    out: Out
    writer: str
    clock: Callable[[], float] = system_time.monotonic
    now: Callable[[], datetime] = _utc_now


_recorder: Recorder | None = None
_open: ContextVar[Running | None] = ContextVar("thenwhat_open_span", default=None)


def use(recorder: Recorder | None) -> None:
    """Start recording through this recorder, or stop when given None. What the one
    before it was handed is written first."""
    global _recorder
    before, _recorder = _recorder, recorder
    if before is not None and before is not recorder:
        before.out.close()


def recording() -> bool:
    return _recorder is not None


def add_model(tokens_in: int, tokens_out: int, cost_usd: Decimal) -> None:
    running = _open.get()
    if running is not None:
        running.add_model(tokens_in, tokens_out, cost_usd)


def add_request(source: str, count: int = 1) -> None:
    running = _open.get()
    if running is not None:
        running.add_request(source, count)


def add_wait(cause: str, seconds: float) -> None:
    running = _open.get()
    if running is not None:
        running.add_wait(cause, seconds)


def event(kind: str, **values: Any) -> None:
    """Hand on an event, with the time and the writer, when something is recording."""
    recorder = _recorder
    if recorder is not None:
        recorder.out.event(Event(kind, recorder.now(), recorder.writer, values))


def flush() -> int:
    """Write what has been handed on, and say how many measurements could not be
    written so far in this process."""
    recorder = _recorder
    if recorder is None:
        return 0
    recorder.out.flush()
    return recorder.out.not_written()


def not_written() -> int:
    recorder = _recorder
    return 0 if recorder is None else recorder.out.not_written()


@contextmanager
def measured(
    step: str,
    *,
    version: int = 1,
    trace: str | None = None,
    batch: int = 1,
    traces: Sequence[str] = (),
    run: str | None = None,
) -> Generator[Running]:
    """Measure the work inside as one span. A step that raises is measured as failed,
    with the kind of error, and the error goes on up.

    Spans may be opened inside one another: a decision inside a read is measured as its
    own span, and the model call it makes and the time it takes are counted in the
    decision's span only. A span opened inside another works on what the outer one
    works on, and belongs to its run, unless it says otherwise.
    """
    recorder = _recorder
    outer = _open.get()
    if trace is None and not traces and outer is not None:
        trace = outer.span.trace
        traces = outer.span.traces
        batch = outer.span.batch
    if run is None and outer is not None:
        run = outer.span.run
    started = recorder.now() if recorder is not None else datetime.min
    running = Running(
        Span(
            step=step,
            step_version=version,
            writer=recorder.writer if recorder is not None else "",
            trace=trace,
            batch=batch,
            started_at=started,
            traces=list(traces),
            run=run,
        )
    )
    if recorder is None:
        # Nothing is recording: the step still gets something to speak to.
        yield running
        return
    began = recorder.clock()
    if outer is None:
        # Taken in hand: a line says so, so that another process sees it before it ends.
        running.span.id = f"{PROCESS}-{next(_ids)}"
        running.add_wait(WRITER_WAIT, recorder.out.started(running.span))
    token = _open.set(running)
    try:
        yield running
    except BaseException as failure:
        running.span.outcome = FAILED
        running.span.outcome_class = FAILED
        running.span.error_kind = type(failure).__name__
        raise
    finally:
        _open.reset(token)
        took = recorder.clock() - began
        running.span.ended_at = started + timedelta(seconds=took)
        running.span.ran_seconds = max(
            took - running.span.waited_seconds - running.inner_seconds, 0.0
        )
        if outer is not None:
            outer.add_inner(took, running.span.cost_usd + running.span.inner_cost_usd)
        # A wait to hand it on is added to the span itself by the writer. The outer span
        # spent that time on this one, so it is not the outer one's to report.
        handed = recorder.out.finished(running.span)
        if outer is not None and handed > 0:
            outer.add_inner(handed)


def claim_trace(slug: str) -> str:
    return f"claim:{slug}"


def measuring[**P, R](
    step: str, *, trace_of: Callable[..., str | None] | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Measure every call of a function as one span of this step. `trace_of` is given
    the call's arguments and says what the call works on."""

    def wrap(work: Callable[P, R]) -> Callable[P, R]:
        @wraps(work)
        def measured_work(*args: P.args, **kwargs: P.kwargs) -> R:
            trace = trace_of(*args, **kwargs) if trace_of is not None else None
            with measured(step, trace=trace):
                return work(*args, **kwargs)

        return measured_work

    return wrap
