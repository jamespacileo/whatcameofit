"""What happens to a run, recorded as it happens. Behavior: openspec processing-metrics,
"What happens to a run is recorded as it happens".

Each event is a line in the same day's file as the measurements, with a kind of its own
and the time it happened: a run started, with its step, its limit and its workers; a run
ended, with why and its counts; a source was paused, until when; records were made due,
with the step, the reason and how many. They are written only while something is
recording, as measurements are, and never hold anything about a reader.
"""

import uuid
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum

from thenwhat.measure import spans

RUN_STARTED = "run_started"
RUN_ENDED = "run_ended"
SOURCE_PAUSED = "source_paused"
MADE_DUE = "made_due"
# What records made due because they failed are made due for, in place of a reason.
FAILED = "failed"


class RunEnd(StrEnum):
    """Why a run ended."""

    NOTHING_DUE = "nothing_due"
    LIMIT = "limit"
    # A provider that cannot be asked: an allowance used up, a pause, a model or the page
    # reader out of reach.
    CANNOT_ASK = "cannot_ask"
    SPEND_CEILING = "spend_ceiling"
    OPERATOR = "operator"
    # An error that no record caught ended the run.
    FAILED = "failed"


def new_run() -> str:
    """An identifier for a run, made once for each run, that ties its measurements and
    its events together."""
    return uuid.uuid4().hex[:16]


def run_started(run: str, step: str, *, limit: int | None, workers: int) -> None:
    spans.event(
        RUN_STARTED,
        run=run,
        step=step,
        limit=limit,
        workers=workers,
        process=spans.PROCESS,
    )


def run_ended(
    run: str,
    step: str,
    *,
    why: RunEnd,
    counts: Mapping[str, int],
    not_written: int = 0,
    error_kind: str | None = None,
) -> None:
    values: dict[str, object] = {"run": run, "step": step, "why": why.value, "counts": dict(counts)}
    if not_written:
        values["not_written"] = not_written
    if error_kind is not None:
        values["error_kind"] = error_kind
    spans.event(RUN_ENDED, **values)


def source_paused(source: str, until: datetime) -> None:
    """A source, or an outlet held by the page reader, is not to be asked before
    `until`."""
    spans.event(SOURCE_PAUSED, source=source, until=until.isoformat())


def made_due(step: str, reason: str, records: int) -> None:
    """Records of a step were made due again: those waiting for a reason, or those that
    failed (`FAILED` in place of a reason)."""
    spans.event(MADE_DUE, step=step, reason=reason, records=records)
