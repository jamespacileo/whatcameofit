"""The readings command: wiring only. The checks and the step are tested in
test_record_readings.py. Scenario names are from openspec record-readings."""

import copy
from collections.abc import Generator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.models.function import FunctionModel
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from test_record_readings import (
    ANSWER,
    NOW,
    OTHER_TRIAL,
    OUTCOMES,
    SLUG,
    TRIAL,
    Scripted,
    reads,
    store_record,
    stored,
    study_with,
)
from thenwhat.cli import app
from thenwhat.db.models import Claim
from thenwhat.llm.client import Llm, LlmSettings

pytest_plugins = ["test_record_readings"]


@pytest.fixture
def model() -> Scripted:
    return Scripted(copy.deepcopy(ANSWER))


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, model: Scripted):
    """Invoke the CLI on the test session with a scripted model."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    def configure(**prices: Any) -> None:
        values = {"input_usd_per_mtok": Decimal("3"), "monthly_budget_usd": Decimal("10")}
        values |= prices
        settings = LlmSettings("test:scripted-model", output_usd_per_mtok=Decimal("15"), **values)
        monkeypatch.setattr(
            "thenwhat.cli.extract.make_llm",
            lambda s: Llm(s, settings, model=FunctionModel(model.respond), now=lambda: NOW),
        )

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    configure()
    runner = CliRunner()

    def invoke(*arguments: str, **prices: Any) -> Result:
        if prices:
            configure(**prices)
        return runner.invoke(app, list(arguments), env={"COLUMNS": "200"})

    return invoke


def output(result: Result) -> str:
    return " ".join(result.output.split())


def test_readings_reads_the_trials_of_the_named_claim(run, session: Session, claim: Claim):
    result = run("readings", SLUG)

    assert result.exit_code == 0, result.output
    assert "1 trial(s) read, 0 unchanged" in output(result)
    assert "4 reading(s) stored, 0 refused by rule" in output(result)
    assert len(stored(session)) == 4


def test_readings_without_claims_or_all_explains_and_exits_1(run, model: Scripted):
    result = run("readings")

    assert result.exit_code == 1
    assert "--all" in output(result)
    assert model.shown == []


def test_all_reads_every_published_claim_and_a_second_run_asks_nothing(
    run, model: Scripted, claim: Claim
):
    """Scenario: Second run with nothing changed"""
    run("readings", "--all")

    result = run("readings", "--all")

    assert result.exit_code == 0, result.output
    assert "0 trial(s) read, 1 unchanged and not read again" in output(result)
    assert len(model.shown) == 1


def test_the_command_stops_at_the_spend_ceiling_says_so_and_exits_1(
    run,
    session: Session,
    model: Scripted,
    claim: Claim,
    fixture_json,
    monkeypatch: pytest.MonkeyPatch,
):
    """Scenario: Spend ceiling reached"""
    store_record(session, claim, study_with(fixture_json, OUTCOMES, trial_id=OTHER_TRIAL))
    # One trial at a time, so the ceiling is looked at between the two.
    monkeypatch.setenv("READINGS_AT_ONCE", "1")

    result = run("readings", SLUG, input_usd_per_mtok=Decimal("1000000"))

    assert result.exit_code == 1
    assert "monthly ceiling of $10" in output(result)
    assert f"Not read: {OTHER_TRIAL}." in output(result)
    # What was read before the ceiling is kept.
    assert [trial_read.trial_id for trial_read in reads(session)] == [TRIAL]


def test_a_refused_reading_is_counted_with_its_reason(run, model: Scripted, claim: Claim):
    """Scenario: Words not in the record"""
    model.answers[0]["outcomes"][0]["follow_up"]["words"] = "about a month"

    result = run("readings", SLUG)

    assert result.exit_code == 0, result.output
    assert "1 refused by rule (words not in record: 1)" in output(result)
