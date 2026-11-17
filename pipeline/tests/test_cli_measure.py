"""The measure command: wiring, messages and exit codes. The figures are tested in
test_measure.py."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from measure_support import write
from thenwhat.cli import app
from thenwhat.cli.measure import start_measuring
from thenwhat.db.models import MeasureDaily
from thenwhat.measure import spans as measure
from thenwhat.measure.files import LOOKUP
from thenwhat.measure.spans import Span


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.measure.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("MEASURE_DIR", str(tmp_path))
    monkeypatch.setenv("MEASURE_KEEP_DAYS", "30")
    monkeypatch.setenv("MEASURE_LOOKUP_KEEP_DAYS", "7")
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, ["measure", *arguments])

    yield invoke
    measure.use(None)


def made(days_ago: int, **changes) -> Span:
    fields: dict[str, Any] = {
        "step": "link_read",
        "step_version": 1,
        "writer": "mini",
        "trace": "example.org/a",
        "batch": 1,
        "started_at": datetime.now(UTC) - timedelta(days=days_ago),
        "ran_seconds": 6.0,
        "waited": {"reader": 40.0},
        "requests": {"reader": 1},
        "cost_usd": Decimal("0.0065"),
    }
    return Span(**(fields | changes))


def test_measure_reports_time_waiting_and_cost_by_step(run, session: Session, tmp_path: Path):
    """Scenario: A week's report"""
    write(
        tmp_path,
        made(1),
        made(1, step="link_triage", batch=20, waited={}, requests={}, cost_usd=Decimal("0.012")),
        made(0, outcome="failed", ran_seconds=1.0),
        made(12, writer=LOOKUP),
    )

    result = run("--days", "3")

    assert result.exit_code == 0, result.output
    assert "time working 13.0s, waiting 1.3m, model cost $0.0250" in result.output
    assert "link_read [mini]: 2 records (1 done, 1 failed)" in result.output
    assert "link_triage [mini]: 20 records (20 done)" in result.output
    assert "reader: 1.3m" in result.output
    assert "No claim published in this range has measurements." in result.output
    # Yesterday is over, so it is now kept as totals; today is not.
    assert session.scalar(select(func.count()).select_from(MeasureDaily)) == 3
    # A lookup's measurements from twelve days ago are past their seven days.
    assert not list(tmp_path.glob("spans-lookup-*"))
    assert len(list(tmp_path.glob("spans-work-*"))) == 2


def test_measure_says_when_a_range_has_no_measurements(run):
    """Scenario: Before anything is measured"""
    result = run()

    assert result.exit_code == 0, result.output
    assert "No measurements from" in result.output
    assert "$" not in result.output


def test_measure_says_when_nothing_is_being_measured(run, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEASURE_DIR")

    result = run()

    assert result.exit_code == 0, result.output
    assert "MEASURE_DIR is not set, so nothing is being measured." in result.output


def test_measure_refuses_a_day_it_cannot_read(run):
    result = run("--since", "last tuesday")

    assert result.exit_code == 1
    assert "Give days as YYYY-MM-DD." in result.output


def test_measuring_does_not_start_without_its_days(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys
):
    """Single-step measurements are kept for a set number of days, with no default: with
    none set, nothing is measured and the command says why."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("MEASURE_DIR", str(tmp_path))
    monkeypatch.delenv("MEASURE_KEEP_DAYS", raising=False)
    monkeypatch.delenv("MEASURE_LOOKUP_KEEP_DAYS", raising=False)

    start_measuring()

    assert measure.recording() is False
    assert "MEASURE_KEEP_DAYS and MEASURE_LOOKUP_KEEP_DAYS must be set" in capsys.readouterr().err


def test_measuring_starts_when_its_folder_and_days_are_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("MEASURE_DIR", str(tmp_path))
    monkeypatch.setenv("MEASURE_KEEP_DAYS", "30")
    monkeypatch.setenv("MEASURE_LOOKUP_KEEP_DAYS", "7")
    monkeypatch.setenv("MEASURE_WRITER", "mini")
    try:
        start_measuring()
        with measure.measured("link_read", trace="example.org/a"):
            pass
    finally:
        measure.use(None)

    [file] = tmp_path.iterdir()
    assert file.name.startswith("spans-work-")
    assert '"writer":"mini"' in file.read_text()
