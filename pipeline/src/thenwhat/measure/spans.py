"""One measurement of one step: a span. Behavior: openspec processing-metrics.

A step wraps its work in `measured`. While it runs, the places every step passes
through (a model call's cost, a request to a source, a wait for a turn) add to the span
that is open, so no step counts its own tokens, requests or waits. When nothing is
recording, all of this does nothing.

A span holds the step and what it worked on: an article's address key or a claim's
slug. It never holds anything about a reader.
"""

import threading
import time as system_time
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps
from typing import Any

# Outcomes a step's own code does not give.
FAILED = "failed"
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
        "ran_seconds",
        "waited",
        "outcome",
        "error_kind",
        "reused",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "inner_cost_usd",
        "requests",
        "rows_written",
    }
)


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

    @property
    def waited_seconds(self) -> float:
        return sum(self.waited.values())

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["started_at"] = self.started_at.isoformat()
        record["cost_usd"] = str(self.cost_usd)
        record["inner_cost_usd"] = str(self.inner_cost_usd)
        return record


def span_from(record: dict[str, Any]) -> Span:
    unknown = set(record) - FIELDS
    if unknown:
        raise ValueError(f"A span may not hold: {', '.join(sorted(unknown))}.")
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

    def ended(self, outcome: str) -> None:
        self.span.outcome = outcome

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


Sink = Callable[[Span], None]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Recorder:
    """Where finished spans go, and who is writing them."""

    sink: Sink
    writer: str
    clock: Callable[[], float] = system_time.monotonic
    now: Callable[[], datetime] = _utc_now


_recorder: Recorder | None = None
_open: ContextVar[Running | None] = ContextVar("thenwhat_open_span", default=None)


def use(recorder: Recorder | None) -> None:
    """Start recording through this recorder, or stop when given None."""
    global _recorder
    _recorder = recorder


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


@contextmanager
def measured(
    step: str,
    *,
    version: int = 1,
    trace: str | None = None,
    batch: int = 1,
    traces: Sequence[str] = (),
) -> Generator[Running]:
    """Measure the work inside as one span. A step that raises is measured as failed,
    with the kind of error, and the error goes on up.

    Spans may be opened inside one another: a decision inside a read is measured as its
    own span, and the model call it makes and the time it takes are counted in the
    decision's span only. A span opened inside another works on what the outer one
    works on, unless it says otherwise.
    """
    recorder = _recorder
    outer = _open.get()
    if trace is None and not traces and outer is not None:
        trace = outer.span.trace
        traces = outer.span.traces
        batch = outer.span.batch
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
        )
    )
    if recorder is None:
        # Nothing is recording: the step still gets something to speak to.
        yield running
        return
    token = _open.set(running)
    began = recorder.clock()
    try:
        yield running
    except BaseException as failure:
        running.span.outcome = FAILED
        running.span.error_kind = type(failure).__name__
        raise
    finally:
        _open.reset(token)
        took = recorder.clock() - began
        running.span.ran_seconds = max(
            took - running.span.waited_seconds - running.inner_seconds, 0.0
        )
        if outer is not None:
            outer.add_inner(took, running.span.cost_usd + running.span.inner_cost_usd)
        recorder.sink(running.span)


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
