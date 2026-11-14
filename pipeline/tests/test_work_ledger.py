"""The work ledger and the runner, on a real database. Scenario names are from openspec
work-ledger."""

import threading

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from backfill_support import (
    NOW,
    Client,
    DemoStep,
    add_trials,
    committed_sessions,
    remove_committed,
    same_session,
)
from thenwhat.backfill.errors import DuplicateStep, UnknownStep
from thenwhat.backfill.ledger import count, mark_changed
from thenwhat.backfill.runner import run_step
from thenwhat.backfill.steps import by_name, find_step
from thenwhat.db.models import ArticleLead, WorkEntry
from thenwhat.domain import WorkOutcome

LIMIT = 3


def run(session: Session, step: DemoStep, **options):
    return run_step(
        same_session(session), step, Client(), now=lambda: NOW, attempt_limit=LIMIT, **options
    )


def entries(session: Session, step: DemoStep) -> list[WorkEntry]:
    return list(
        session.scalars(
            select(WorkEntry)
            .where(WorkEntry.step == step.name, WorkEntry.step_version == step.version)
            .order_by(WorkEntry.record_id)
        )
    )


# --- step declaration ------------------------------------------------------------


def test_two_steps_with_one_name_are_refused():
    """Scenario: Two steps with one name"""
    with pytest.raises(DuplicateStep, match="demo"):
        by_name([DemoStep("demo"), DemoStep("demo")])


def test_an_unknown_step_lists_the_steps_that_exist():
    with pytest.raises(UnknownStep, match="Steps: demo, other"):
        find_step([DemoStep("demo"), DemoStep("other")], "missing")


# --- ledger entries and due work ---------------------------------------------------


def test_a_processed_record_has_one_entry(session: Session):
    """Scenario: A record is processed"""
    [trial] = add_trials(session, 1)
    step = DemoStep()

    report = run(session, step)

    [entry] = entries(session, step)
    assert (report.done, report.remaining_due) == (1, 0)
    assert (entry.record_kind, entry.record_id) == ("registry_trial", trial.id)
    assert (entry.outcome, entry.attempts, entry.requests_used) == (WorkOutcome.DONE, 1, 1)
    assert entry.last_attempt_at == NOW and entry.error is None


def test_finished_records_are_skipped(session: Session):
    """Scenario: Finished records are skipped"""
    add_trials(session, 10)
    step = DemoStep()
    step.finds_nothing = {"T0001", "T0002"}
    run(session, step, limit=9)

    step.ran.clear()
    report = run(session, step)

    assert step.ran == ["T0009"]
    assert count(session, step, LIMIT).due == 0 and report.remaining_due == 0
    assert count(session, step, LIMIT).nothing_found == 2


def test_a_record_whose_input_changed_is_due_again(session: Session):
    """Scenario: A record changed"""
    trials = add_trials(session, 3)
    step = DemoStep()
    run(session, step)

    trials[1].search_name = "another name"
    trials[2].title = "A new title, which the step does not read"
    for trial in trials:
        mark_changed(session, [step], "registry_trial", trial)

    step.ran.clear()
    run(session, step)
    assert step.ran == ["T0001"]
    assert [entry.attempts for entry in entries(session, step)] == [1, 1, 1]


def test_a_record_out_of_scope_is_never_due_and_gets_no_entry(session: Session):
    """Scenario: A record out of scope"""
    add_trials(session, 2, name=None)
    step = DemoStep()

    report = run(session, step)

    assert report.processed == 0 and entries(session, step) == []
    assert count(session, step, LIMIT).in_scope == 0


def test_adding_a_step_leaves_the_first_step_alone(session: Session):
    """Scenario: Adding a step"""
    add_trials(session, 5)
    first, second = DemoStep("first"), DemoStep("second")
    run(session, first)

    assert count(session, second, LIMIT).due == 5
    assert count(session, first, LIMIT).due == 0

    run(session, second)
    assert len(entries(session, first)) == 5 and len(entries(session, second)) == 5
    assert first.ran == second.ran


def test_raising_the_version_makes_every_record_due_and_keeps_old_entries(session: Session):
    """Scenario: Version raised"""
    add_trials(session, 4)
    old = DemoStep("demo", version=1)
    run(session, old)

    new = DemoStep("demo", version=2)

    assert count(session, new, LIMIT).due == 4
    assert len(entries(session, old)) == 4


# --- failures ----------------------------------------------------------------------


def test_one_failure_does_not_stop_the_run(session: Session):
    """Scenario: One record fails"""
    add_trials(session, 10)
    step = DemoStep()
    step.fails = {"T0004"}

    report = run(session, step)

    assert (report.done, report.failed) == (9, 1)
    assert report.errors == ["RuntimeError: could not process T0004"]
    failed = [entry for entry in entries(session, step) if entry.outcome is WorkOutcome.FAILED]
    assert [entry.error for entry in failed] == ["RuntimeError: could not process T0004"]
    assert report.remaining_due == 1


def test_a_failure_leaves_none_of_the_steps_partial_result(session: Session):
    """Scenario: Stopped between records"""
    add_trials(session, 2)
    step = DemoStep()
    step.fails = {"T0001"}

    run(session, step)

    urls = list(session.scalars(select(ArticleLead.url)))
    assert urls == ["https://news.example.org/demo/T0000"]
    assert [entry.outcome for entry in entries(session, step)] == [
        WorkOutcome.DONE,
        WorkOutcome.FAILED,
    ]


def test_a_record_that_keeps_failing_is_skipped_after_the_attempt_limit(session: Session):
    """Scenario: Attempt limit reached"""
    add_trials(session, 1)
    step = DemoStep()
    step.fails = {"T0000"}

    for _ in range(LIMIT + 1):
        run(session, step)

    [entry] = entries(session, step)
    counts = count(session, step, LIMIT)
    assert entry.attempts == LIMIT and len(step.ran) == LIMIT
    assert (counts.due, counts.failed, counts.needs_attention) == (0, 1, 1)


def test_a_failed_record_that_then_succeeds_updates_its_entry(session: Session):
    """Scenario: A record is processed twice"""
    add_trials(session, 1)
    step = DemoStep()
    step.fails = {"T0000"}
    run(session, step)

    step.fails = set()
    run(session, step)

    [entry] = entries(session, step)
    assert (entry.outcome, entry.attempts, entry.error) == (WorkOutcome.DONE, 2, None)


# --- runs ----------------------------------------------------------------------------


def test_a_limited_run_reports_what_remains_and_a_restart_repeats_nothing(session: Session):
    """Scenarios: Limited run, Restart"""
    add_trials(session, 10)
    step = DemoStep()

    first = run(session, step, limit=4)
    second = run(session, step)

    assert (first.processed, first.remaining_due) == (4, 6)
    assert (second.processed, second.remaining_due) == (6, 0)
    assert sorted(step.ran) == [f"T{number:04d}" for number in range(10)]


def test_two_runs_at_once_process_each_record_once(engine: Engine):
    """Scenario: Two processes"""
    registry, name = "two-runs-registry", "two-runs-step"
    open_session = committed_sessions(engine)
    step = DemoStep(name, registry=registry)
    reports = []
    try:
        with open_session() as session:
            add_trials(session, 100, registry=registry)

        def work() -> None:
            reports.append(
                run_step(open_session, step, Client(), now=lambda: NOW, attempt_limit=LIMIT)
            )

        threads = [threading.Thread(target=work) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(step.ran) == [f"T{number:04d}" for number in range(100)]
        assert sum(report.done for report in reports) == 100
        with open_session() as session:
            assert count(session, step, LIMIT).done == 100
    finally:
        remove_committed(engine, registry=registry, step=name, source=step.source)
