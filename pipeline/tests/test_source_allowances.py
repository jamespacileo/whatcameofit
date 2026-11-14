"""Request allowances shared by every process that asks a source. Scenario names are
from openspec source-allowances."""

from datetime import timedelta

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from backfill_support import (
    Client,
    DemoStep,
    add_trials,
    committed_sessions,
    remove_committed,
    same_session,
)
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.errors import AllowanceUsedUp, NoAllowance, SourcePaused
from thenwhat.backfill.ledger import count
from thenwhat.backfill.runner import run_step
from thenwhat.config import DEFAULT_ALLOWANCES, Settings, SourceAllowance
from thenwhat.db.models import WorkEntry

SOURCE = "demo-source"
THREE_A_DAY = {SOURCE: SourceAllowance(requests=3, period_hours=24, interval_seconds=5)}


def allowances(session: Session, fake_time, configured=THREE_A_DAY) -> Allowances:
    return Allowances(same_session(session), configured, fake_time)


# --- configuration -------------------------------------------------------------------


def test_a_source_with_no_allowance_is_refused_by_name(session: Session, fake_time):
    """Scenario: A source with no allowance"""
    with pytest.raises(NoAllowance, match="'unknown-source'.*SOURCE_ALLOWANCES"):
        allowances(session, fake_time).claim("unknown-source")


def test_allowances_come_from_settings_over_the_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv(
        "SOURCE_ALLOWANCES",
        '{"mediacloud": {"requests": 10, "period_hours": 1, "interval_seconds": 2}}',
    )

    configured = Settings().allowances()

    assert configured["mediacloud"].requests == 10
    assert configured["clinicaltrials.gov"] == DEFAULT_ALLOWANCES["clinicaltrials.gov"]


# --- shared count and spacing ----------------------------------------------------------


def test_processes_share_one_count_and_keep_their_requests_apart(engine: Engine, fake_time):
    """Scenarios: Four processes, Two processes one source, Restart within a period"""
    source = "shared-count-source"
    configured = {source: SourceAllowance(requests=3, period_hours=24, interval_seconds=5)}
    open_session = committed_sessions(engine)
    try:
        first = Allowances(open_session, configured, fake_time)
        second = Allowances(open_session, configured, fake_time)

        first.claim(source)
        second.claim(source)
        assert fake_time.slept == [5.0]

        # A process started later sees what the others used.
        restarted = Allowances(open_session, configured, fake_time)
        restarted.claim(source)
        with pytest.raises(AllowanceUsedUp, match="3 requests"):
            first.claim(source)

        with open_session() as session:
            status = restarted.status(session, source)
        assert (status.used, status.left) == (3, 0)
    finally:
        remove_committed(engine, registry="none", step="none", source=source)


def test_the_allowance_is_restored_when_the_period_ends(session: Session, fake_time):
    shared = allowances(session, fake_time)
    for _ in range(3):
        shared.claim(SOURCE)
    with pytest.raises(AllowanceUsedUp):
        shared.claim(SOURCE)

    fake_time.advance(timedelta(hours=24))
    shared.claim(SOURCE)

    assert shared.status(session, SOURCE).used == 1


# --- used up and refused ---------------------------------------------------------------


def claiming_step(shared: Allowances) -> DemoStep:
    step = DemoStep()
    step.before = lambda record: shared.claim(SOURCE)
    return step


def test_running_out_mid_run_ends_the_run_and_leaves_records_due(session: Session, fake_time):
    """Scenario: Running out mid-run"""
    add_trials(session, 5)
    shared = allowances(session, fake_time)
    step = claiming_step(shared)

    report = run_step(same_session(session), step, Client(), now=fake_time.now, attempt_limit=3)

    assert (report.done, report.failed, report.remaining_due) == (3, 0, 2)
    assert report.stopped is not None and "restored at 2026-01-02" in report.stopped
    assert len(session.scalars(select(WorkEntry)).all()) == 3


def test_a_refusal_pauses_the_source_and_counts_no_attempt(
    session: Session, engine: Engine, fake_time
):
    """Scenarios: Refused by the source, Refusals do not count as failures"""
    # The allowance has its own transactions, as it does in a real run, so that what it
    # records survives the undoing of the record that was refused.
    source = "refusing-source"
    configured = {source: SourceAllowance(requests=3, period_hours=24, interval_seconds=5)}
    open_session = committed_sessions(engine)
    shared = Allowances(open_session, configured, fake_time)
    add_trials(session, 3)
    step = DemoStep()

    def refuse_the_second(record) -> None:
        shared.claim(source)
        if record.external_id == "T0001":
            raise shared.refused(source, retry_after_seconds=600)

    try:
        step.before = refuse_the_second
        report = run_step(same_session(session), step, Client(), now=fake_time.now, attempt_limit=3)

        assert (report.done, report.failed, report.remaining_due) == (1, 0, 2)
        assert report.stopped is not None and "asked too often" in report.stopped
        assert count(session, step, 3).failed == 0
        with open_session() as other:
            assert shared.status(other, source).paused_until is not None
        with pytest.raises(SourcePaused):
            shared.claim(source)

        # Once the pause has passed the source is asked again and the run continues
        # until the allowance, of which the refused request used one, is spent.
        fake_time.advance(timedelta(seconds=601))
        step.before = lambda record: shared.claim(source)
        resumed = run_step(
            same_session(session), step, Client(), now=fake_time.now, attempt_limit=3
        )
        assert resumed.done == 1 and "used up" in (resumed.stopped or "")
    finally:
        remove_committed(engine, registry="none", step="none", source=source)


def test_a_refusal_with_no_stated_delay_uses_the_configured_pause(session: Session, fake_time):
    shared = allowances(session, fake_time)
    shared.claim(SOURCE)

    shared.refused(SOURCE)

    assert shared.status(session, SOURCE).paused_until == fake_time.now() + timedelta(minutes=60)
