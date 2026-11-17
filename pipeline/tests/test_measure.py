"""Measurements: what one step records, how they are kept and added up.
Behavior: openspec processing-metrics."""

import itertools
import json
import threading
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backfill_support import Client, DemoStep, add_trials, same_session
from measure_support import Kept, write
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.db.models import MeasureClaim, MeasureDaily, MeasureRolledDay
from thenwhat.llm.ledger import record_usage
from thenwhat.measure import spans as measure
from thenwhat.measure.files import LOOKUP, FileWriter, days_held, read_day, remove_old
from thenwhat.measure.report import ClaimTook, measured_cost_of_a_record, report_of
from thenwhat.measure.spans import WRITER_WAIT, Span, span_from
from thenwhat.measure.totals import roll, totals_of
from thenwhat.work.runner import run_step

DAY = date(2026, 11, 19)
AT = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


class Ticks:
    """A clock a test moves by hand."""

    def __init__(self) -> None:
        self.at = 0.0

    def __call__(self) -> float:
        return self.at


@pytest.fixture
def ticks() -> Ticks:
    return Ticks()


@pytest.fixture
def recorded(ticks: Ticks):
    """Record spans into a list for the length of a test."""
    kept = Kept()
    measure.use(measure.Recorder(out=kept, writer="test", clock=ticks, now=lambda: AT))
    yield kept.spans
    measure.use(None)


def span(**changes) -> Span:
    fields: dict[str, Any] = {
        "step": "link_read",
        "step_version": 1,
        "writer": "mini",
        "trace": "example.org/a",
        "batch": 1,
        "started_at": AT,
        "ran_seconds": 2.0,
    }
    return Span(**(fields | changes))


# --- one step ------------------------------------------------------------------------


def test_a_step_is_measured_with_its_waiting_kept_apart(recorded, ticks):
    """Scenario: A read that waited on the page reader"""
    with measure.measured("link_read", version=3, trace="example.org/a") as step:
        measure.add_wait("reader", 40.0)
        ticks.at += 46.0
        measure.add_request("reader")
        measure.add_model(3000, 700, Decimal("0.0065"))
        step.wrote(4)
        step.ended("done")

    [made] = recorded
    assert (made.step, made.step_version, made.writer) == ("link_read", 3, "test")
    assert made.waited == {"reader": 40.0}
    assert made.ran_seconds == pytest.approx(6.0)
    assert made.requests == {"reader": 1}
    assert (made.tokens_in, made.tokens_out, made.cost_usd) == (3000, 700, Decimal("0.0065"))
    assert (made.outcome, made.rows_written, made.trace) == ("done", 4, "example.org/a")


def test_a_step_answered_from_stored_work_says_so(recorded):
    """Scenario: A step answered from stored work"""
    with measure.measured("link_triage", trace="example.org/a") as step:
        step.reused()

    [made] = recorded
    assert made.reused is True
    assert (made.tokens_in, made.cost_usd, made.requests) == (0, Decimal(0), {})


def test_a_step_that_fails_is_measured_and_the_failure_goes_on(recorded, ticks):
    """Scenario: A step that fails"""
    with pytest.raises(TimeoutError), measure.measured("link_read"):
        ticks.at += 3.0
        raise TimeoutError("the page said something a span must not repeat")

    [made] = recorded
    assert (made.outcome, made.error_kind) == ("failed", "TimeoutError")
    assert made.ran_seconds == pytest.approx(3.0)
    assert "must not repeat" not in json.dumps(made.as_record())


def test_what_is_measured_inside_a_step_is_counted_once(recorded, ticks):
    """A decision inside a read is its own measurement: its time and its model call are
    not also the read's, and it works on what the read works on."""
    with measure.measured("link_read", trace="example.org/a"):
        ticks.at += 2.0
        with measure.measured("decision:same_claim"):
            ticks.at += 5.0
            measure.add_model(500, 0, Decimal("0.0001"))

    inner, outer = recorded
    assert (inner.step, inner.trace) == ("decision:same_claim", "example.org/a")
    assert (inner.ran_seconds, inner.cost_usd) == (pytest.approx(5.0), Decimal("0.0001"))
    assert (outer.ran_seconds, outer.cost_usd) == (pytest.approx(2.0), Decimal(0))
    # The read can still say what the whole of it cost.
    assert outer.inner_cost_usd == Decimal("0.0001")


def test_nothing_is_recorded_when_measuring_is_off():
    measure.use(None)
    with measure.measured("link_read") as step:
        measure.add_model(1, 1, Decimal(1))
        step.ended("done")
    assert measure.recording() is False


def test_a_span_refuses_a_field_it_does_not_have():
    """Scenario: Measurements of a lookup. What a reader's browser sent has no place
    to go."""
    record = span().as_record()
    for name in ("user_agent", "ip", "address", "text"):
        with pytest.raises(ValueError, match="may not hold"):
            span_from(record | {name: "anything"})


# --- through the places every step passes --------------------------------------------


def test_a_model_calls_cost_reaches_the_step_being_measured(session: Session, recorded):
    with measure.measured("readings"):
        record_usage(
            session,
            purpose="readings",
            model="synthetic-model",
            input_tokens=120,
            output_tokens=30,
            cost_usd=Decimal("0.0004"),
            now=AT,
        )

    [made] = recorded
    assert (made.tokens_in, made.tokens_out, made.cost_usd) == (120, 30, Decimal("0.0004"))


def test_each_record_a_step_runs_is_measured_with_its_outcome(session: Session, recorded):
    trials = add_trials(session, 3)
    step = DemoStep()
    step.fails = {trials[1].external_id}
    step.finds_nothing = {trials[2].external_id}

    run_step(same_session(session), step, Client(), now=lambda: AT, attempt_limit=1)

    assert [made.step for made in recorded] == ["demo", "demo", "demo"]
    assert sorted(made.outcome for made in recorded) == ["done", "failed", "nothing_found"]


# --- kept as files -------------------------------------------------------------------


def test_spans_are_kept_by_day_and_read_back(tmp_path: Path):
    write(
        tmp_path,
        span(
            cost_usd=Decimal("0.5"),
            waited={"reader": 1.5},
            requests={"reader": 2},
            run="a-run",
            outcome="later",
            outcome_class="later",
            reason="site_busy",
        ),
        span(writer=LOOKUP, started_at=AT + timedelta(days=1)),
    )

    assert days_held(tmp_path) == [DAY, DAY + timedelta(days=1)]
    [made] = read_day(tmp_path, DAY)
    assert (made.cost_usd, made.waited, made.requests) == (
        Decimal("0.5"),
        {"reader": 1.5},
        {"reader": 2},
    )
    assert (made.run, made.outcome_class, made.reason) == ("a-run", "later", "site_busy")


def test_a_burst_of_finished_records_is_written_whole(tmp_path: Path):
    """Scenario: A burst of finished records. Records finish far faster than a writer
    that holds only eight lines writes them, in two processes at once: the work waits
    for them, the wait is measured, and every one is written, whole."""
    steps = itertools.count()

    def clock() -> float:
        return float(next(steps))

    writers = [
        FileWriter(tmp_path, writer="mini", capacity=8, every=3600.0, clock=clock) for _ in range(2)
    ]

    def finish(writer: FileWriter, worker: int) -> None:
        for number in range(500):
            writer.finished(span(trace=f"example.org/{worker}/{number}"))

    workers = [
        threading.Thread(target=finish, args=(writers[worker % 2], worker)) for worker in range(4)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    for writer in writers:
        writer.close()

    made = list(read_day(tmp_path, DAY))
    assert len({made.trace for made in made}) == len(made) == 2000
    assert any(WRITER_WAIT in made.waited for made in made)


def test_single_measurements_are_removed_after_their_days(tmp_path: Path):
    """Scenario: Looking into yesterday, and a lookup's shorter time"""
    today = DAY + timedelta(days=40)
    for age in (1, 8, 31):
        started = datetime.combine(today - timedelta(days=age), AT.time(), tzinfo=UTC)
        write(tmp_path, span(started_at=started), span(writer=LOOKUP, started_at=started))

    removed = remove_old(tmp_path, today=today, keep_days=30, lookup_keep_days=7)

    assert len(removed) == 3
    left = sorted(path.name for path in tmp_path.iterdir())
    assert left == [
        f"spans-lookup-{today - timedelta(days=1)}.jsonl",
        f"spans-work-{today - timedelta(days=8)}.jsonl",
        f"spans-work-{today - timedelta(days=1)}.jsonl",
    ]


# --- added up ------------------------------------------------------------------------


def test_a_thousand_spans_become_a_few_totals():
    """Scenario: A million leads in a month"""
    made = [span(step="link_triage", cost_usd=Decimal("0.001"), batch=20) for _ in range(600)]
    made += [span(outcome="failed", waited={"reader": 2.0}) for _ in range(400)]

    totals = totals_of(made)

    assert len(totals) == 2
    triage = totals[("link_triage", 1, "mini", "done")]
    assert (triage.spans, triage.records, triage.cost_usd) == (600, 12000, Decimal("0.600"))
    failed = totals[("link_read", 1, "mini", "failed")]
    assert (failed.spans, failed.waited_by_cause) == (400, {"reader": 800.0})


def claim_with_article(session: Session):
    claim = add_claim(
        session,
        slug="ex-1-tooth-agenesis",
        headline="A synthetic headline",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
        summary="A synthetic summary.",
    )
    add_article(
        session,
        claim.slug,
        url="https://news.example.org/2021/teeth?utm_source=x",
        outlet="The Example",
        title="A synthetic headline",
        published_date=date(2021, 3, 1),
    )
    session.flush()
    return claim


def test_a_finished_day_is_added_once_and_today_is_left(session: Session, tmp_path: Path):
    """Scenarios: A million leads in a month, Asking about one published claim"""
    claim = claim_with_article(session)
    write(
        tmp_path,
        # A triage call for twenty leads, one of them the claim's article.
        span(
            step="link_triage",
            trace=None,
            batch=20,
            traces=["news.example.org/2021/teeth", "other.example/b"],
            ran_seconds=4.0,
            cost_usd=Decimal("0.02"),
        ),
        span(trace="news.example.org/2021/teeth", ran_seconds=6.0, waited={"reader": 30.0}),
        span(step="registry_search", trace=f"claim:{claim.slug}", cost_usd=Decimal("0.003")),
        span(trace="unrelated.example/x"),
        span(started_at=AT + timedelta(days=1)),
    )
    today = DAY + timedelta(days=1)

    first = roll(session, tmp_path, today=today, now=AT)
    again = roll(session, tmp_path, today=today, now=AT)

    assert (first.days, first.spans, again.days) == ([DAY], 4, [])
    assert session.scalar(select(func.count()).select_from(MeasureDaily)) == 3
    assert list(session.scalars(select(MeasureRolledDay.day))) == [DAY]
    took = session.scalars(select(MeasureClaim)).one()
    assert took.claim_id == claim.id
    assert took.spans == 3
    # A twentieth of the triage call, the read, and the registry search.
    assert took.ran_seconds == pytest.approx(4.0 / 20 + 6.0 + 2.0)
    assert took.waited_seconds == pytest.approx(30.0)
    assert took.cost_usd == Decimal("0.004")


# --- reported ------------------------------------------------------------------------


def test_the_report_gives_each_steps_share_and_what_a_claim_took():
    """Scenario: A week's report"""
    totals = totals_of(
        [
            span(step="link_triage", ran_seconds=1.0, cost_usd=Decimal("0.03"), reused=True),
            span(step="link_triage", ran_seconds=1.0, cost_usd=Decimal("0.03")),
            span(ran_seconds=6.0, waited={"reader": 12.0}, cost_usd=Decimal("0.02")),
            span(outcome="failed", ran_seconds=0.0, waited={"reader": 2.0}),
        ]
    )
    claims = [
        ClaimTook(3600.0, 10.0, 30.0, Decimal("0.02")),
        ClaimTook(7200.0, 20.0, 60.0, Decimal("0.06")),
        ClaimTook(600.0, 5.0, 5.0, Decimal("0.01")),
    ]

    report = report_of(DAY, DAY, totals, claims)

    read, triage = report.steps
    assert (read.step, read.records, read.outcomes) == ("link_read", 2, {"done": 1, "failed": 1})
    assert read.share_of_time == pytest.approx(20 / 22)
    assert (triage.share_of_cost, triage.reused_share) == (pytest.approx(0.75), 0.5)
    assert report.waited_on == [("reader", 14.0)]
    assert report.total_cost_usd == Decimal("0.08")
    assert report.claims is not None
    assert (report.claims.median_cost_usd, report.claims.worst_cost_usd) == (
        Decimal("0.02"),
        Decimal("0.06"),
    )
    assert report.claims.worst_elapsed_seconds == 7200.0


def test_a_range_with_no_measurements_gives_an_empty_report():
    """Scenario: Before anything is measured"""
    assert report_of(DAY, DAY, {}, []).empty is True


# --- used in a plan ------------------------------------------------------------------


def daily(session: Session, day: date, *, records: int, cost: str, inner: str = "0") -> None:
    session.add(
        MeasureDaily(
            day=day,
            step="link_triage",
            step_version=1,
            writer="mini",
            outcome="done",
            spans=records // 20,
            records=records,
            reused=0,
            ran_seconds=1.0,
            waited_seconds=0.0,
            waited_by_cause={},
            requests_by_source={},
            tokens_in=0,
            tokens_out=0,
            cost_usd=Decimal(cost),
            inner_cost_usd=Decimal(inner),
            rows_written=0,
        )
    )


def test_a_week_of_measurements_gives_a_records_measured_cost(session: Session):
    today = DAY + timedelta(days=10)
    for back in range(1, 8):
        # The step's own measurement carries no model cost: the decision inside does.
        daily(session, today - timedelta(days=back), records=1000, cost="0", inner="0.60")
    session.flush()

    measured = measured_cost_of_a_record(session, "link_triage", today=today)

    assert measured is not None
    assert (measured.days, measured.per_record) == (7, Decimal("0.0006"))


def test_fewer_days_than_a_week_gives_no_measured_cost(session: Session):
    today = DAY + timedelta(days=10)
    for back in range(1, 4):
        daily(session, today - timedelta(days=back), records=1000, cost="0.60")
    session.flush()

    assert measured_cost_of_a_record(session, "link_triage", today=today) is None
    assert measured_cost_of_a_record(session, "link_read", today=today) is None
