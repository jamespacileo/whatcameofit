"""Outcomes that say whether a record comes back, on a real database. Scenario names are
from openspec work-ledger (change one-work-runner)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import (
    NO_DATE,
    NOT_A_REPORT,
    NOW,
    SITE_BUSY,
    Client,
    DemoStep,
    ReasonedStep,
    add_trials,
    same_session,
)
from thenwhat.db.models import RegistryTrial, WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.work.ledger import count
from thenwhat.work.outcome import (
    Later,
    NeedsFix,
    NothingFound,
    Reason,
    ReasonClass,
    ReasonMisused,
    UndeclaredReason,
    declared,
)
from thenwhat.work.runner import run_step

LIMIT = 3

NEVER_DECLARED = Reason("never_declared", ReasonClass.FINAL, "nothing the step knows")


def run(session: Session, step: DemoStep, *, at: datetime = NOW, **options):
    return run_step(
        same_session(session), step, Client(), now=lambda: at, attempt_limit=LIMIT, **options
    )


def entry_of(session: Session, step: DemoStep, trial: RegistryTrial) -> WorkEntry:
    return session.scalars(
        select(WorkEntry).where(WorkEntry.step == step.name, WorkEntry.record_id == trial.id)
    ).one()


# --- reasons ------------------------------------------------------------------------


def test_a_reason_is_said_in_words_with_its_values():
    assert SITE_BUSY.say({"status": 503}) == "the site answered 503"


def test_a_reason_cannot_be_given_with_an_answer_of_another_class():
    with pytest.raises(ReasonMisused, match="declared as later"):
        NothingFound(SITE_BUSY, {"status": 503})
    with pytest.raises(ReasonMisused, match="declared as needs_fix"):
        Later(NO_DATE, NOW + timedelta(hours=1))
    with pytest.raises(ReasonMisused, match="declared as final"):
        NeedsFix(NOT_A_REPORT)


def test_a_reason_is_refused_without_the_values_its_words_take():
    with pytest.raises(ReasonMisused, match="status"):
        Later(SITE_BUSY, NOW + timedelta(hours=1))


def test_a_code_the_step_has_not_declared_is_refused_and_its_reasons_listed():
    with pytest.raises(UndeclaredReason, match="Its reasons: no_date, not_a_report, site_busy"):
        declared(ReasonedStep(), "missing")


# --- ledger entries -----------------------------------------------------------------


def test_a_record_to_be_tried_later_holds_its_reason_and_its_time(session: Session):
    """Scenario: A record to be tried later"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    until = NOW + timedelta(hours=6)
    step.answers[trial.external_id] = lambda: Later(SITE_BUSY, until, {"status": 503})

    report = run(session, step)

    entry = entry_of(session, step, trial)
    assert entry.outcome is WorkOutcome.LATER
    assert (entry.reason, entry.reason_values) == ("site_busy", {"status": 503})
    assert entry.not_before == until and entry.first_put_off_at == NOW
    assert entry.attempts == 0 and entry.error is None
    assert (report.later, report.processed, report.remaining_due) == (1, 1, 0)


def test_a_handled_record_put_off_counts_towards_the_run_limit(session: Session):
    trials = add_trials(session, 4)
    step = ReasonedStep()
    for trial in trials:
        step.answers[trial.external_id] = lambda: Later(
            SITE_BUSY, NOW + timedelta(hours=1), {"status": 503}
        )

    report = run(session, step, limit=1)

    assert (report.later, report.processed, report.remaining_due) == (1, 1, 3)
    assert step.ran == [trials[0].external_id]
    assert entry_of(session, step, trials[0]).attempts == 0


def test_nothing_found_can_say_why(session: Session):
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    step.answers[trial.external_id] = lambda: NothingFound(NOT_A_REPORT)

    report = run(session, step)

    entry = entry_of(session, step, trial)
    assert (entry.outcome, entry.reason, entry.attempts) == (
        WorkOutcome.NOTHING_FOUND,
        "not_a_report",
        1,
    )
    assert report.nothing_found == 1


def test_a_reason_the_step_did_not_declare_fails_the_record(session: Session):
    """Scenario: A reason the step did not declare"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    step.answers[trial.external_id] = lambda: NothingFound(NEVER_DECLARED)

    report = run(session, step)

    entry = entry_of(session, step, trial)
    assert entry.outcome is WorkOutcome.FAILED and entry.reason is None
    assert entry.error is not None and "never_declared" in entry.error
    assert report.failed == 1


# --- due work -----------------------------------------------------------------------


def test_a_record_whose_time_has_not_come_is_not_taken_and_is_once_it_has(session: Session):
    """Scenario: A record whose time has not come"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    step.answers[trial.external_id] = lambda: Later(
        SITE_BUSY, NOW + timedelta(hours=1), {"status": 503}
    )
    run(session, step)

    again = run(session, step)
    assert step.ran == [trial.external_id] and again.later == 0
    assert count(session, step, LIMIT, now=NOW).due == 0
    assert count(session, step, LIMIT, now=NOW).later == 1

    del step.answers[trial.external_id]
    later = run(session, step, at=NOW + timedelta(hours=2))

    assert later.done == 1
    assert entry_of(session, step, trial).outcome is WorkOutcome.DONE
    assert entry_of(session, step, trial).not_before is None


def test_a_record_that_needs_a_fix_is_not_taken_until_its_input_changes(session: Session):
    """Scenario: A record that needs a fix"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    step.answers[trial.external_id] = lambda: NeedsFix(NO_DATE)

    first = run(session, step)
    again = run(session, step, at=NOW + timedelta(days=90))

    entry = entry_of(session, step, trial)
    assert (entry.outcome, entry.reason, entry.attempts) == (WorkOutcome.NEEDS_FIX, "no_date", 0)
    assert (first.needs_fix, again.needs_fix) == (1, 0) and len(step.ran) == 1
    counts = count(session, step, LIMIT, now=NOW)
    assert (counts.due, counts.needs_fix) == (0, 1)

    entry.stale = True
    session.flush()
    del step.answers[trial.external_id]
    assert run(session, step).done == 1


# --- failed records -----------------------------------------------------------------


def test_a_record_put_off_three_times_has_no_attempt_counted(session: Session):
    """Scenario: A record put off three times"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    for hour in range(3):
        at = NOW + timedelta(hours=2 * hour)
        step.answers[trial.external_id] = lambda at=at: Later(
            SITE_BUSY, at + timedelta(hours=1), {"status": 503}
        )
        assert run(session, step, at=at).later == 1

    entry = entry_of(session, step, trial)
    assert entry.attempts == 0 and entry.first_put_off_at == NOW
    assert count(session, step, LIMIT, now=NOW + timedelta(hours=6)).due == 1


def test_a_record_at_the_limit_that_is_made_due_may_fail_as_often_again(session: Session):
    """Scenario: A record at the limit is made due"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    step.fails.add(trial.external_id)
    for _ in range(LIMIT):
        run(session, step)
    entry = entry_of(session, step, trial)
    assert entry.attempts == LIMIT and count(session, step, LIMIT, now=NOW).due == 0

    entry.stale = True
    session.flush()

    assert count(session, step, LIMIT, now=NOW).due == 1
    run(session, step)
    assert entry_of(session, step, trial).attempts == 1


# --- put off too long ---------------------------------------------------------------


def test_a_record_put_off_for_one_reason_past_the_span_needs_a_fix(session: Session):
    """Scenario: An outlet that never comes back"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    span = timedelta(days=30)

    def busy(at: datetime) -> Later:
        return Later(SITE_BUSY, at + timedelta(hours=6), {"status": 503})

    step.answers[trial.external_id] = lambda: busy(NOW)
    run(session, step, put_off_span=span)
    late = NOW + timedelta(days=31)
    step.answers[trial.external_id] = lambda: busy(late)

    report = run(session, step, at=late, put_off_span=span)

    entry = entry_of(session, step, trial)
    assert (entry.outcome, entry.reason) == (WorkOutcome.NEEDS_FIX, "site_busy")
    assert entry.not_before is None and entry.reason_values == {"status": 503}
    assert report.needs_fix == 1
    assert run(session, step, at=late + timedelta(days=1), put_off_span=span).processed == 0


def test_a_record_put_off_for_a_new_reason_starts_its_span_again(session: Session):
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    other = Reason("reader_busy", ReasonClass.LATER, "the reader is busy")
    step.reasons = (*ReasonedStep.reasons, other)
    step.answers[trial.external_id] = lambda: Later(
        SITE_BUSY, NOW + timedelta(hours=1), {"status": 503}
    )
    run(session, step)
    late = NOW + timedelta(days=31)
    step.answers[trial.external_id] = lambda: Later(other, late + timedelta(hours=1))

    run(session, step, at=late, put_off_span=timedelta(days=30))

    entry = entry_of(session, step, trial)
    assert (entry.outcome, entry.reason, entry.first_put_off_at) == (
        WorkOutcome.LATER,
        "reader_busy",
        late,
    )


# --- a step that depends on another -------------------------------------------------


def test_a_step_waits_for_the_step_it_depends_on(session: Session):
    """Scenario: A step waiting for another"""
    one, two = add_trials(session, 2)
    search = ReasonedStep("search")
    decide = ReasonedStep("decide")
    decide.after = (search,)
    search.fails.add(two.external_id)

    assert count(session, decide, LIMIT, now=NOW).due == 0
    assert run(session, decide).processed == 0

    run(session, search)
    report = run(session, decide)

    assert decide.ran == [one.external_id]
    assert (report.done, report.remaining_due) == (1, 0)
    assert count(session, decide, LIMIT, now=NOW).in_scope == 2


def test_a_step_waits_again_when_the_earlier_step_is_due_again(session: Session):
    """Scenario: The earlier step is due again"""
    [trial] = add_trials(session, 1)
    search = ReasonedStep("search")
    decide = ReasonedStep("decide")
    decide.after = (search,)
    run(session, search)
    run(session, decide)
    for entry in session.scalars(select(WorkEntry).where(WorkEntry.record_id == trial.id)):
        entry.stale = True
    session.flush()

    assert count(session, search, LIMIT, now=NOW).due == 1
    assert count(session, decide, LIMIT, now=NOW).due == 0

    # The search finishes again, this time with nothing found: finished all the same.
    search.answers[trial.external_id] = lambda: NothingFound(NOT_A_REPORT)
    assert run(session, search).nothing_found == 1
    assert count(session, decide, LIMIT, now=NOW).due == 1


def test_a_step_does_not_wait_for_an_earlier_version_of_the_step_it_depends_on(
    session: Session,
):
    add_trials(session, 1)
    run(session, ReasonedStep("search", version=1))
    decide = ReasonedStep("decide")
    decide.after = (ReasonedStep("search", version=2),)

    assert count(session, decide, LIMIT, now=NOW).due == 0
