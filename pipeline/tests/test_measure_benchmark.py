"""Measuring costs the work almost nothing. Behavior: openspec processing-metrics,
"Measuring costs the work almost nothing" (change one-work-runner).

A benchmark: it times a step over RECORDS records twice, one record a transaction as
the runner works, and runs for minutes. It is left
out of an ordinary run; run it with `make benchmark`.
"""

import time
from collections.abc import Iterator
from pathlib import Path
from statistics import median
from typing import Any

import pytest
from sqlalchemy import Engine, event, insert, text
from sqlalchemy.orm import Session

from backfill_support import NOW, Client, QuietStep, same_session
from thenwhat.db.models import RegistryTrial
from thenwhat.measure import spans as measure
from thenwhat.measure.files import FileWriter, days_held, read_day
from thenwhat.work.runner import run_step

# How many records the step works through with measuring off, and again with it on.
RECORDS = 50_000
# They are worked through as passes over the same slice of records, each pass with
# measuring off and then on (or on, then off), so that the two passes of a part meet the
# same load on the database's server, which other checkouts' tests share. Each pass is
# a step of a name of its own, whose ledger starts empty. The search for the next due
# record slows as finished records pile up in a step's scope, and the step's cost is
# what is measured here, not that search, so the scope stays one slice.
SLICE = 100
# With measuring on, the same records may take no more than a twentieth longer.
ALLOWED = 1.05


def add_slice(session: Session) -> None:
    session.execute(
        insert(RegistryTrial),
        [
            {
                "registry_name": "bench",
                "external_id": f"B{number:04d}",
                "title": "A synthetic trial",
                "conditions": ["condition"],
                "interventions": [],
                "phases": ["PHASE3"],
                "search_name": f"drug {number}",
                "search_indication": "condition",
                "raw_payload": {},
                "fetched_at": NOW,
            }
            for number in range(SLICE)
        ],
    )


@pytest.fixture
def statements(engine: Engine) -> Iterator[list[str]]:
    """Every statement sent to the database while the test runs."""
    sent: list[str] = []

    def count(*arguments: Any) -> None:
        sent.append(arguments[2])

    event.listen(engine, "before_cursor_execute", count)
    yield sent
    event.remove(engine, "before_cursor_execute", count)


class OneWriter(FileWriter):
    """The writer of a whole run, which measuring is turned on and off around: it is
    closed once, at the end, as a run's is."""

    def close(self) -> None:
        pass

    def close_at_last(self) -> None:
        super().close()


@pytest.mark.benchmark
def test_screening_a_large_backlog_costs_almost_nothing_to_measure(
    session: Session, tmp_path: Path, statements: list[str]
):
    """Scenario: Screening a large backlog"""
    add_slice(session)
    writer = OneWriter(tmp_path, writer="bench")
    recorder = measure.Recorder(out=writer, writer="bench")
    # Seconds each pass took, with measuring off and on.
    took: dict[bool, list[float]] = {False: [], True: []}
    sent = {False: 0, True: 0}
    finished = {False: 0, True: 0}
    try:
        for part in range(RECORDS // SLICE):
            for measuring in (False, True) if part % 2 == 0 else (True, False):
                name = f"bench-{part}-{'on' if measuring else 'off'}"
                measure.use(recorder if measuring else None)
                before = len(statements)
                began = time.perf_counter()
                report = run_step(
                    same_session(session),
                    QuietStep(name, registry="bench"),
                    Client(),
                    now=lambda: NOW,
                    attempt_limit=1,
                )
                took[measuring].append(time.perf_counter() - began)
                sent[measuring] += len(statements) - before
                finished[measuring] += report.done
            # What the session holds of the finished passes is not needed again. The
            # planner's view of the tables is kept current, outside the timing, as
            # autovacuum keeps the working database's: without it the search for due
            # records scans the ledger, and slows as the parts add to it.
            session.expunge_all()
            if part % 50 == 0:
                session.execute(text("ANALYZE work_entry"))
                session.execute(text("ANALYZE registry_trial"))
    finally:
        measure.use(None)
        writer.close_at_last()

    assert finished == {False: RECORDS, True: RECORDS}
    assert sum(len(list(read_day(tmp_path, day))) for day in days_held(tmp_path)) == RECORDS
    # No statement is made for a measurement.
    assert sent[True] == sent[False]
    off, on = sum(took[False]), sum(took[True])
    # Each part's two passes ran one after the other over the same records, so their
    # ratio is the cost of measuring. The test database's server is shared, and a burst
    # of its load can fall on either pass of a part: the median part is the one asked.
    ratio = median(on_part / off_part for off_part, on_part in zip(*took.values(), strict=True))
    print(
        f"\n{RECORDS:,} records: {off:.1f}s unmeasured, {on:.1f}s measured, {on / off - 1:+.1%};"
        f" median part {ratio - 1:+.1%}"
    )
    assert ratio <= ALLOWED
