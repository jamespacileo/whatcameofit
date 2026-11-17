"""The live view: what runs are doing now, read by another process from the day's files.
Scenario names are from openspec processing-metrics (change one-work-runner)."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from measure_support import write
from thenwhat.cli import app
from thenwhat.measure import spans as measure
from thenwhat.measure.events import RUN_ENDED
from thenwhat.measure.files import BEAT, EVERY_SECONDS
from thenwhat.measure.live import (
    ALIVE_SECONDS,
    REDRAW_SECONDS,
    LiveView,
    Stored,
    kept,
    lines_of,
    view_of,
    watch,
)
from thenwhat.measure.spans import STARTED, Event, Span

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
PROCESS = "a1b2c3d4e5f6"


def read(started: datetime, **changes: Any) -> Span:
    fields: dict[str, Any] = {
        "step": "link_read",
        "step_version": 1,
        "writer": "mini",
        "trace": "example.org/a",
        "batch": 1,
        "started_at": started,
        "ended_at": started + timedelta(seconds=2),
        "ran_seconds": 2.0,
        "outcome_class": "final",
        "run": "run-1",
    }
    return Span(**(fields | changes))


def event(kind: str, at: datetime, **values: Any) -> Event:
    return Event(kind, at, "mini", values)


def view(lines: list[Span | Event], **paused: datetime) -> LiveView:
    return view_of(lines, NOW, paused=paused, spent_usd=Decimal("3.21"), ceiling_usd=Decimal("13"))


def test_nothing_running_says_so_and_how_the_last_run_ended():
    """Scenario: Nothing is running"""
    earlier = NOW - timedelta(hours=2)
    shown = view(
        [
            read(earlier),
            event(
                RUN_ENDED,
                earlier + timedelta(seconds=5),
                run="run-1",
                step="link_read",
                why="nothing_due",
                counts={"done": 1, "still_due": 0},
            ),
        ]
    )

    assert shown.idle is True
    assert shown.last_ended is not None and shown.last_ended.why == "nothing_due"
    words = "\n".join(lines_of(shown, Path("/measure")))
    assert "Nothing has been recorded in the last fifteen minutes." in words
    assert "The last run, of link_read, ended at 2026-11-20 07:00:05 UTC: nothing was due" in words


def test_a_finished_record_reaches_the_view(tmp_path: Path):
    """Scenario: A measurement reaches the view"""
    write(tmp_path, read(NOW - timedelta(seconds=3)), writer="mini")
    drawn: list[LiveView] = []

    watch(
        tmp_path,
        stored=lambda moment: Stored({}, Decimal(0)),
        ceiling_usd=Decimal(13),
        draw=drawn.append,
        now=lambda: NOW,
        sleep=lambda seconds: None,
        once=True,
    )

    [shown] = drawn
    one_minute = next(window for window in shown.windows if window.minutes == 1)
    assert (one_minute.step, one_minute.records) == ("link_read", 1)
    # Written within a second of finishing, read within the next redraw.
    assert EVERY_SECONDS + REDRAW_SECONDS <= 5


def test_the_largest_wait_is_named():
    """Scenario: Reads held up by one outlet's pacing"""
    lines: list[Span | Event] = [
        read(
            NOW - timedelta(seconds=50),
            ran_seconds=2.0,
            waited={"outlet_turn": 30.0, "reader": 6.0},
            trace=f"example.org/{worker}",
        )
        for worker in range(4)
    ]

    [one, five, fifteen] = view(lines).windows

    assert one.largest_wait == five.largest_wait == fifteen.largest_wait == "outlet_turn"
    assert dict(one.waiting_shares) == {
        "outlet_turn": pytest.approx(30 / 38),
        "reader": pytest.approx(6 / 38),
    }
    assert one.running_share == pytest.approx(2 / 38)


def test_rate_and_cost_while_a_run_works():
    """Scenario: Cost while a run works"""
    lines: list[Span | Event] = [
        read(NOW - timedelta(seconds=290 - number), inner_cost_usd=Decimal("0.0011"))
        for number in range(200)
    ]

    five = next(window for window in view(lines).windows if window.minutes == 5)

    assert five.records / five.minutes == 40
    assert five.finished_a_minute == {"done": 40}
    assert five.cost_a_minute == Decimal("0.044")
    assert five.cost_a_record == Decimal("0.0011")


def started(at: datetime, *, number: int, process: str = PROCESS) -> Event:
    return event(
        STARTED,
        at,
        process=process,
        id=f"{process}-{number}",
        run="run-1",
        step="link_read",
        trace=f"example.org/{number}",
        batch=1,
    )


def test_a_record_stuck_in_hand_is_shown_as_the_oldest():
    """Scenario: A record stuck in hand"""
    lines = [
        started(NOW - timedelta(minutes=4), number=1),
        started(NOW - timedelta(seconds=20), number=2),
        read(NOW - timedelta(seconds=20), id=f"{PROCESS}-2"),
        event(BEAT, NOW - timedelta(seconds=10), process=PROCESS),
    ]

    shown = view(kept(lines, NOW))

    oldest = shown.oldest_in_hand
    assert oldest is not None
    assert (oldest.step, oldest.records, oldest.oldest_seconds) == ("link_read", 1, 240.0)
    assert "Oldest in hand: link_read, for 4m 0s." in "\n".join(lines_of(shown, Path("/m")))


def test_a_record_left_by_a_process_that_stopped_is_not_in_hand_for_ever():
    """A run that crashed writes no end: its records leave the count in hand once its
    process has been silent for longer than it ever is while alive."""
    silent = NOW - timedelta(seconds=ALIVE_SECONDS + 1)
    lines = [started(silent - timedelta(minutes=1), number=1), event(BEAT, silent, process=PROCESS)]

    shown = view(kept(lines, NOW))

    assert shown.in_hand == []
    assert shown.left_in_hand == 1


@pytest.fixture
def run_live(session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session

    monkeypatch.setattr("thenwhat.cli.measure.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("MEASURE_DIR", str(tmp_path))
    monkeypatch.setenv("MEASURE_KEEP_DAYS", "30")
    monkeypatch.setenv("MEASURE_LOOKUP_KEEP_DAYS", "7")
    runner = CliRunner()
    yield lambda *arguments: runner.invoke(app, ["measure", *arguments])
    measure.use(None)


def test_measure_live_draws_the_view_once(run_live, tmp_path: Path):
    now = datetime.now(UTC)
    write(tmp_path, read(now - timedelta(seconds=30)), writer="mini")

    result = run_live("--live", "--once")

    assert result.exit_code == 0, result.output
    assert "link_read" in result.output
    assert "Model spend this month: $0.00 of $" in result.output
    # It changes nothing: the day's file is as it was.
    assert len(list(tmp_path.iterdir())) == 1


def test_measure_live_refuses_without_a_folder_to_watch(run_live, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEASURE_DIR")

    result = run_live("--live", "--once")

    assert result.exit_code == 1
    assert "MEASURE_DIR is not set, so there is nothing to watch." in result.output
