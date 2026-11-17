"""`thenwhat work requeue` and the plan's lines for records that wait. Scenario names are
from openspec work-ledger (change one-work-runner)."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from backfill_support import (
    NO_DATE,
    NOT_A_REPORT,
    NOW,
    SITE_BUSY,
    Client,
    ReasonedStep,
    add_trials,
    same_session,
)
from thenwhat.cli import app
from thenwhat.db.models import RegistryTrial, WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.work.allowance import Allowances
from thenwhat.work.ledger import count
from thenwhat.work.outcome import Later, NeedsFix, NothingFound
from thenwhat.work.runner import run_step

LIMIT = 3
Invoke = Callable[..., Result]


@pytest.fixture
def step() -> ReasonedStep:
    return ReasonedStep()


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, fake_time, step: ReasonedStep) -> Invoke:
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.session.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.backfill.steps_for", lambda settings: [step])
    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_allowances",
        lambda settings: Allowances(same_session(session), settings.allowances(), fake_time),
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("CONTACT_EMAIL", "ops@thenwhat.test")
    monkeypatch.setenv(
        "SOURCE_ALLOWANCES",
        '{"demo-source": {"requests": 100, "period_hours": 24, "interval_seconds": 0}}',
    )
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, list(arguments))

    return invoke


def work(session: Session, step: ReasonedStep) -> None:
    run_step(same_session(session), step, Client(), now=lambda: NOW, attempt_limit=LIMIT)


def waiting_trials(
    session: Session, step: ReasonedStep
) -> tuple[list[RegistryTrial], list[RegistryTrial]]:
    """Three trials that need a fix for a missing date, and two put off by a busy site
    with two statuses."""
    trials = add_trials(session, 5)
    undated, busy = trials[:3], trials[3:]
    for trial in undated:
        step.answers[trial.external_id] = lambda: NeedsFix(NO_DATE)
    for trial, status in zip(busy, (503, 429), strict=True):
        step.answers[trial.external_id] = lambda status=status: Later(
            SITE_BUSY, NOW + timedelta(hours=6), {"status": status}
        )
    work(session, step)
    return undated, busy


def stale_ids(session: Session, step: ReasonedStep) -> set[int]:
    return set(
        session.scalars(
            select(WorkEntry.record_id).where(WorkEntry.step == step.name, WorkEntry.stale)
        )
    )


def test_requeue_makes_due_the_records_that_wait_for_one_reason(
    run: Invoke, session: Session, step: ReasonedStep
):
    """Scenario: A parser was fixed"""
    undated, _ = waiting_trials(session, step)

    result = run("work", "requeue", "reasoned", "--reason", "no_date")

    assert result.exit_code == 0, result.output
    assert "3 records of reasoned that wait for 'no_date' are due again" in result.output
    assert "thenwhat backfill run reasoned" in result.output
    assert stale_ids(session, step) == {trial.id for trial in undated}
    assert count(session, step, LIMIT, now=NOW).due == 3


def test_requeue_can_be_narrowed_by_a_value_the_reason_carries(
    run: Invoke, session: Session, step: ReasonedStep
):
    """Scenario: One outlet"""
    _, (first, _second) = waiting_trials(session, step)

    result = run("work", "requeue", "reasoned", "--reason", "site_busy", "--where", "status=503")

    assert result.exit_code == 0, result.output
    assert "1 record of reasoned that waits for 'site_busy', status=503 is due again" in (
        result.output
    )
    assert stale_ids(session, step) == {first.id}


def test_a_dry_run_counts_the_records_and_changes_nothing(
    run: Invoke, session: Session, step: ReasonedStep
):
    waiting_trials(session, step)

    result = run("work", "requeue", "reasoned", "--reason", "no_date", "--dry-run")

    assert result.exit_code == 0, result.output
    assert "3 records of reasoned wait for 'no_date'. Nothing was changed." in result.output
    assert stale_ids(session, step) == set()


def test_requeue_refuses_a_reason_the_step_has_not_declared(
    run: Invoke, session: Session, step: ReasonedStep
):
    """Scenario: An unknown reason"""
    waiting_trials(session, step)

    result = run("work", "requeue", "reasoned", "--reason", "missing")

    assert result.exit_code == 1
    assert "has declared no reason 'missing'" in result.output
    assert "no_date, not_a_report, site_busy" in result.output
    assert stale_ids(session, step) == set()


def test_requeue_refuses_every_record_of_a_final_reason(
    run: Invoke, session: Session, step: ReasonedStep
):
    [trial] = add_trials(session, 1)
    step.answers[trial.external_id] = lambda: NothingFound(NOT_A_REPORT)
    work(session, step)

    result = run("work", "requeue", "reasoned", "--reason", "not_a_report")

    assert result.exit_code == 1
    assert "'not_a_report' is a final reason" in result.output
    assert stale_ids(session, step) == set()


def test_requeue_makes_due_the_records_that_failed_as_often_as_allowed(
    run: Invoke, session: Session, step: ReasonedStep
):
    """Scenario: A record at the limit is made due"""
    stuck, once = add_trials(session, 2)
    step.fails.update({stuck.external_id, once.external_id})
    work(session, step)
    step.fails.discard(once.external_id)
    for _ in range(LIMIT - 1):
        work(session, step)
    assert count(session, step, LIMIT, now=NOW).needs_attention == 1

    result = run("work", "requeue", "reasoned", "--failed")

    assert result.exit_code == 0, result.output
    assert "1 record of reasoned that failed as often as the limit allows is due again" in (
        result.output
    )
    assert stale_ids(session, step) == {stuck.id}
    assert count(session, step, LIMIT, now=NOW).due == 1


def test_requeue_needs_a_reason_or_failed_and_names_an_unknown_step(run: Invoke):
    assert run("work", "requeue", "reasoned").exit_code == 1
    unknown = run("work", "requeue", "missing", "--reason", "no_date")
    assert unknown.exit_code == 1 and "No step is named 'missing'" in unknown.output
    badly = run("work", "requeue", "reasoned", "--reason", "no_date", "--where", "outlet")
    assert badly.exit_code == 1 and "key=value" in badly.output


def test_the_plan_counts_the_records_that_wait_by_reason(
    run: Invoke, session: Session, step: ReasonedStep
):
    """Scenario: Planning with records waiting"""
    waiting_trials(session, step)

    result = run("backfill", "plan")

    assert result.exit_code == 0, result.output
    assert (
        "put off: 2 for 'site_busy' (the site answered <status>); "
        "the first is due 2026-11-20 15:00 UTC"
    ) in result.output
    assert (
        "need a fix: 3 for 'no_date' (the page gives no publication date); make them due "
        "with `thenwhat work requeue reasoned --reason no_date`"
    ) in result.output


def test_a_run_reports_the_records_it_put_off_and_those_that_need_a_fix(
    run: Invoke, session: Session, step: ReasonedStep, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("thenwhat.cli.backfill.make_client", lambda *_: Client())
    monkeypatch.setattr("thenwhat.cli.backfill.open_session", same_session(session))
    waiting_trials(session, step)
    for entry in session.scalars(select(WorkEntry).where(WorkEntry.step == step.name)):
        entry.stale = True
    session.flush()

    result = run("backfill", "run", "reasoned")

    assert result.exit_code == 0, result.output
    assert "2 put off, 3 need a fix; 0 still due." in result.output
    assert {
        entry.outcome for entry in session.scalars(select(WorkEntry).where(~WorkEntry.stale))
    } == {WorkOutcome.LATER, WorkOutcome.NEEDS_FIX}
