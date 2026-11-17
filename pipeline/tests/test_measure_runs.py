"""What the runner measures and what a run records as it happens. Scenario names are
from openspec processing-metrics (change one-work-runner)."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from backfill_support import (
    NOW,
    SITE_BUSY,
    Client,
    QuietStep,
    ReasonedStep,
    add_trials,
    same_session,
)
from measure_support import Kept
from thenwhat.config import SourceAllowance
from thenwhat.db.models import RegistryTrial
from thenwhat.domain import WorkOutcome
from thenwhat.measure import spans as measure
from thenwhat.measure.events import RUN_ENDED, RUN_STARTED, SOURCE_PAUSED
from thenwhat.measure.files import FileWriter, read_day
from thenwhat.measure.report import gather
from thenwhat.measure.spans import FIELDS
from thenwhat.work.allowance import Allowances
from thenwhat.work.errors import ModelUnreachable
from thenwhat.work.outcome import Later
from thenwhat.work.runner import run_step


@pytest.fixture
def kept():
    out = Kept()
    measure.use(measure.Recorder(out=out, writer="test", now=lambda: NOW))
    yield out
    measure.use(None)


class Source(Client):
    """A source client as the real ones are: what it is asked is counted in the
    measurement that is open, by the client, not by the step."""

    def ask(self) -> None:
        self.requests_made += 1
        measure.add_wait("demo-source", 2.0)
        measure.add_request("demo-source")
        measure.add_model(100, 10, Decimal("0.001"))


class BrandNewStep(QuietStep):
    """A step declared after the runner was written. Nothing in it is about measuring."""

    def run(self, session: Session, record: RegistryTrial, client: Client) -> WorkOutcome:
        assert isinstance(client, Source)
        client.ask()
        return super().run(session, record, client)


def test_a_step_added_later_is_measured(session: Session, kept: Kept):
    """Scenario: A step added later"""
    add_trials(session, 3)

    run_step(
        same_session(session), BrandNewStep("brand_new"), Source(), now=lambda: NOW, attempt_limit=1
    )

    assert [span.step for span in kept.spans] == ["brand_new"] * 3
    for span in kept.spans:
        assert span.ran_seconds >= 0 and span.waited == {"demo-source": 2.0}
        assert span.requests == {"demo-source": 1}
        assert span.cost_usd == Decimal("0.001")
        assert (span.outcome, span.outcome_class, span.reason) == ("done", "final", None)
    # One run: every record's measurement names it, and its events do too.
    runs = {span.run for span in kept.spans}
    assert len(runs) == 1 and None not in runs
    assert {event.values["run"] for event in kept.events} == runs


def test_a_record_put_off_says_so_with_its_reason(session: Session, kept: Kept):
    """Scenario: A record put off"""
    [trial] = add_trials(session, 1)
    step = ReasonedStep()
    step.answers[trial.external_id] = lambda: Later(
        SITE_BUSY, NOW + timedelta(hours=1), {"status": 503}
    )

    run_step(same_session(session), step, Client(), now=lambda: NOW, attempt_limit=1)

    [span] = kept.spans
    assert (span.outcome, span.outcome_class, span.reason) == ("later", "later", "site_busy")


def test_a_measurement_holds_its_run_class_and_reason_and_nothing_unlisted():
    """A measurement may hold the run, its outcome's class and its reason, and still
    nothing outside its list."""
    assert {"run", "outcome_class", "reason"} <= FIELDS
    assert not {"user_agent", "ip", "address", "text", "url"} & FIELDS


def test_a_run_stopped_by_a_quota_says_so(session: Session, kept: Kept):
    """Scenario: A run stopped by a quota"""
    trials = add_trials(session, 5)
    step = ReasonedStep()

    def quota_used_up():
        raise ModelUnreachable("The model's quota is used up.")

    step.answers[trials[2].external_id] = quota_used_up

    report = run_step(
        same_session(session), step, Client(), now=lambda: NOW, attempt_limit=1, limit=10
    )

    started, ended = kept.events
    assert started.kind == RUN_STARTED
    assert (started.values["step"], started.values["limit"], started.values["workers"]) == (
        "reasoned",
        10,
        1,
    )
    assert (ended.kind, ended.at, ended.values["why"]) == (RUN_ENDED, NOW, "cannot_ask")
    assert ended.values["counts"]["done"] == report.done == 2
    assert ended.values["counts"]["still_due"] == report.remaining_due == 3


def test_a_paused_source_is_recorded_with_its_time(session: Session, kept: Kept, fake_time):
    """Scenario: A source is paused"""
    allowances = Allowances(
        same_session(session),
        {"registry.example": SourceAllowance(requests=10, period_hours=24, interval_seconds=0)},
        fake_time,
    )

    allowances.refused("registry.example", retry_after_seconds=7200)

    [paused] = kept.events
    assert paused.kind == SOURCE_PAUSED
    assert paused.values == {
        "source": "registry.example",
        "until": (fake_time.now() + timedelta(hours=2)).isoformat(),
    }


def test_measurements_that_cannot_be_written_are_counted_and_said(session: Session, tmp_path: Path):
    """Scenario: The folder cannot be written"""
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where the folder should be")
    folder = blocked / "measure"
    said: list[str] = []
    out = FileWriter(folder, writer="test", now=lambda: NOW, say=said.append)
    measure.use(measure.Recorder(out=out, writer="test", now=lambda: NOW))
    add_trials(session, 3)
    try:
        report = run_step(
            same_session(session), QuietStep(), Client(), now=lambda: NOW, attempt_limit=1
        )
        # The folder can be written again: the next line written says what was not.
        blocked.unlink()
        measure.event("made_due", step="quiet", reason="failed", records=0)
    finally:
        measure.use(None)

    assert (report.done, report.not_written) == (3, 3)
    assert list(read_day(folder, NOW.date())) == []
    assert gather(session, folder, NOW.date(), NOW.date()).measurements_not_written == 3
    assert said == [], "it was said in the files, so nothing is left to say on stderr"


def test_measurements_never_written_are_said_as_the_process_ends(tmp_path: Path):
    """When the folder cannot be written again before the process ends, the process
    says so: a measurement is never lost without being said."""
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where the folder should be")
    said: list[str] = []
    out = FileWriter(blocked / "measure", writer="test", now=lambda: NOW, say=said.append)
    measure.use(measure.Recorder(out=out, writer="test", now=lambda: NOW))
    try:
        with measure.measured("link_read"):
            pass
    finally:
        measure.use(None)

    [words] = said
    assert "could not be written" in words and "1 measurement" in words
