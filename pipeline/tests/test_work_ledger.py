"""The work ledger and the runner, on a real database. Scenario names are from openspec
work-ledger."""

import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from backfill_support import (
    NOW,
    Client,
    DemoStep,
    ModelStep,
    QuietStep,
    add_trials,
    committed_sessions,
    remove_committed,
    same_session,
)
from thenwhat.config import Settings
from thenwhat.db.models import ArticleLead, LlmUsage, RegistryTrial, WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.work import runner
from thenwhat.work.errors import DuplicateStep, UnknownStep
from thenwhat.work.ledger import count, mark_changed
from thenwhat.work.runner import run_step
from thenwhat.work.spend import ceiling_check
from thenwhat.work.steps import asks_a_source, by_name, find_step

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


def test_a_failed_record_rolls_back_and_is_the_only_one_retried(session: Session):
    """Scenarios: One record fails, Stopped between records, A record is processed twice"""
    trials = add_trials(session, 3)
    step = DemoStep()
    step.fails = {"T0001"}

    report = run(session, step)

    assert (report.done, report.failed, report.remaining_due) == (2, 1, 1)
    assert report.errors == ["RuntimeError: could not process T0001"]
    before, failed, after = entries(session, step)
    assert before.outcome is after.outcome is WorkOutcome.DONE
    assert (failed.record_id, failed.outcome, failed.attempts, failed.error) == (
        trials[1].id,
        WorkOutcome.FAILED,
        1,
        report.errors[0],
    )
    assert set(session.scalars(select(ArticleLead.registry_trial_id))) == {
        trials[0].id,
        trials[2].id,
    }
    entry_id = failed.id

    retry = DemoStep()
    recovered = run(session, retry)

    assert retry.ran == ["T0001"]
    assert (recovered.done, recovered.failed, recovered.remaining_due) == (1, 0, 0)
    before, retried, after = entries(session, retry)
    assert before.attempts == after.attempts == 1
    assert (retried.id, retried.outcome, retried.attempts, retried.error) == (
        entry_id,
        WorkOutcome.DONE,
        2,
        None,
    )
    assert sorted(session.scalars(select(ArticleLead.registry_trial_id))) == [
        trial.id for trial in trials
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


# --- runs ----------------------------------------------------------------------------


def test_a_restart_skips_both_kinds_of_finished_record(engine: Engine):
    """Scenarios: Limited run, Restart, Finished records are skipped"""
    registry = "restart-registry"
    open_session = committed_sessions(engine)
    first_step = DemoStep("restart", registry=registry)
    resumed_step = DemoStep("restart", registry=registry)
    try:
        with open_session() as session:
            trials = add_trials(session, 6, registry=registry)
            expected = [trial.external_id for trial in trials]

        # Any four of the six include both kinds of finished record.
        first_step.finds_nothing = resumed_step.finds_nothing = set(expected[3:])
        first = run_step(
            open_session, first_step, Client(), now=lambda: NOW, attempt_limit=LIMIT, limit=4
        )
        assert first.processed == 4
        assert first.done > 0 and first.nothing_found > 0
        unfinished = set(expected) - set(first_step.ran)

        resumed = run_step(
            open_session, resumed_step, Client(), now=lambda: NOW, attempt_limit=LIMIT
        )

        assert sorted(resumed_step.ran) == sorted(unfinished)
        assert first.remaining_due == 2
        assert (resumed.processed, resumed.remaining_due) == (2, 0)
        with open_session() as session:
            assert [entry.attempts for entry in entries(session, resumed_step)] == [1] * 6
    finally:
        remove_committed(engine, registry=registry, step=first_step.name, source=first_step.source)


def test_provider_stop_is_shared_before_another_worker_takes_more_work(engine):
    from concurrent.futures import ThreadPoolExecutor

    from thenwhat.work.errors import SourceStop

    registry, name = "provider-stop-registry", "provider-stop-step"
    open_session = committed_sessions(engine)
    both_claimed = threading.Barrier(2, timeout=10)
    finish = threading.Event()

    class Step(DemoStep):
        def run(self, session, record, client):
            if not finish.is_set():
                both_claimed.wait()
                if client is unavailable:
                    raise SourceStop("provider unavailable")
                assert finish.wait(10)
            return super().run(session, record, client)

    step, unavailable = Step(name, registry=registry), Client()
    try:
        with open_session() as session:
            add_trials(session, 5, registry=registry)
        with (
            runner.measured_run(name, limit=None, workers=2) as shared,
            ThreadPoolExecutor(2) as pool,
        ):

            def worker(client):
                return run_step(
                    open_session, step, client, now=lambda: NOW, attempt_limit=LIMIT, run=shared
                )

            stopped, sibling = pool.submit(worker, unavailable), pool.submit(worker, Client())
            try:
                assert stopped.result(timeout=12).stopped == "provider unavailable"
            finally:
                finish.set()
            assert sibling.result(timeout=12).done == 1
        with open_session() as session:
            assert count(session, step, LIMIT).due == 4
            [completed] = entries(session, step)
            assert completed.attempts == 1 and completed.outcome == WorkOutcome.DONE
    finally:
        remove_committed(engine, registry=registry, step=name, source=step.source)


@pytest.mark.parametrize("batch_size", [1, 2], ids=["single", "batch"])
def test_two_overlapping_runs_process_each_record_once(engine: Engine, batch_size: int):
    """Scenarios: Two processes, Two runs and batches"""
    registry, name = "overlapping-registry", "overlapping-step"
    open_session = committed_sessions(engine)
    first_step = ModelStep(name, registry=registry, batch_size=batch_size)
    second_step = ModelStep(name, registry=registry, batch_size=batch_size)
    held, release = threading.Event(), threading.Event()

    def hold_first(_record: RegistryTrial) -> None:
        held.set()
        assert release.wait(15), "the other run did not finish"

    first_step.before = hold_first
    try:
        with open_session() as session:
            add_trials(session, 6, registry=registry)

        with ThreadPoolExecutor(max_workers=2) as workers:
            first = workers.submit(
                run_step, open_session, first_step, Client(), now=lambda: NOW, attempt_limit=LIMIT
            )
            try:
                assert held.wait(10), "the first run did not take its records"
                second = workers.submit(
                    run_step,
                    open_session,
                    second_step,
                    Client(),
                    now=lambda: NOW,
                    attempt_limit=LIMIT,
                )
                assert second.result(timeout=10).done == 6 - batch_size
            finally:
                release.set()
            assert first.result(timeout=10).done == batch_size

        assert sorted(first_step.ran + second_step.ran) == [f"T{number:04d}" for number in range(6)]
        with open_session() as session:
            assert count(session, first_step, LIMIT).done == 6
            assert [entry.attempts for entry in entries(session, first_step)] == [1] * 6
    finally:
        remove_committed(engine, registry=registry, step=name, source=first_step.source)


# --- steps that ask no source, call a model, or take several records ------------------


def test_a_step_that_asks_no_source_runs_and_counts_no_request(session: Session):
    """Scenario: Planning a step that only reads the database"""
    add_trials(session, 5)
    step = QuietStep("quiet")
    client = Client()

    report = run_step(same_session(session), step, client, now=lambda: NOW, attempt_limit=LIMIT)

    assert (report.done, report.remaining_due) == (5, 0)
    assert client.requests_made == 0
    assert not asks_a_source(step)
    assert [entry.requests_used for entry in entries(session, step)] == [0] * 5


def test_a_batch_step_makes_one_call_for_twenty_records(session: Session):
    """Scenario: A batch of twenty"""
    add_trials(session, 100)
    step = ModelStep()

    report = run(session, step)

    assert [len(call) for call in step.calls] == [20] * 5
    assert (report.done, report.remaining_due) == (100, 0)
    assert len(entries(session, step)) == 100


def test_a_failed_batch_rolls_back_before_trying_each_record_alone(session: Session):
    """Scenario: One bad record in a batch"""
    add_trials(session, 20)
    step = ModelStep(call_cost_usd=Decimal("1"))
    step.unanswered = {"T0007"}

    report = run(session, step, limit=20)

    assert (report.done, report.failed) == (19, 1)
    failed = [entry for entry in entries(session, step) if entry.outcome is WorkOutcome.FAILED]
    assert len(failed) == 1
    assert "left an item out" in (failed[0].error or "")
    # One call for the batch, then each record alone.
    assert [len(call) for call in step.calls] == [20] + [1] * 20
    # Each call writes usage before it can fail. Only the successful single calls persist.
    assert list(session.scalars(select(LlmUsage.input_tokens))) == [40] * 19


def test_a_limit_cuts_the_last_batch(session: Session):
    """Scenario: Limited run, for a step that takes several records a call"""
    add_trials(session, 50)
    step = ModelStep()

    report = run(session, step, limit=30)

    assert [len(call) for call in step.calls] == [20, 10]
    assert (report.done, report.remaining_due) == (30, 20)


def test_the_spend_ceiling_stops_a_model_step_and_leaves_records_due(session: Session):
    """Scenario: Ceiling reached during a run"""
    add_trials(session, 100)
    step = ModelStep(call_cost_usd=Decimal("1"))
    settings = Settings(database_url="postgresql+psycopg://unused/unused")
    settings.llm_monthly_budget_usd = Decimal("2")
    check = ceiling_check(settings, lambda: NOW)

    first = run(session, step, before_call=check)
    second = run(session, step, before_call=check)

    # Two calls at one dollar reach the ceiling of two.
    assert (first.done, first.remaining_due) == (40, 60)
    assert "monthly ceiling of $2" in (first.stopped or "")
    assert len(entries(session, step)) == 40
    assert (second.processed, second.remaining_due) == (0, 60)
    assert len(step.calls) == 2


def test_a_run_remembers_only_the_records_that_failed(session: Session, monkeypatch):
    """A run over hundreds of thousands of records must not carry every finished one
    into each query: found on the first real run, which stopped at 66,000 leads."""
    add_trials(session, 60)
    step = ModelStep()
    step.unanswered = {"T0007"}
    remembered: list[int] = []
    real = runner.process_batch

    def watched(*arguments, **options):
        remembered.append(len(options["skip"]))
        return real(*arguments, **options)

    monkeypatch.setattr(runner, "process_batch", watched)

    report = run(session, step)

    assert (report.done, report.failed) == (59, 1)
    # Nothing is remembered until a record fails, and then only that one.
    assert remembered[0] == 0 and max(remembered) == 1
