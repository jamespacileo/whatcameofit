"""Triage of link leads from their titles. Scenario names are from openspec lead-triage.
Every lead here is synthetic, and the backend is a fake: no model is called."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import Client, same_session
from thenwhat.backfill.link_load import load_links
from thenwhat.backfill.link_readers import HACKER_NEWS, SharedLink
from thenwhat.backfill.link_screen import LinkScreen
from thenwhat.backfill.link_triage import (
    DecisionClient,
    LinkTriage,
    Standing,
    standing_of,
    standings,
)
from thenwhat.backfill.runner import run_step
from thenwhat.db.models import DecisionLog, LinkLead, LlmUsage, WorkEntry
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import (
    HEALTH_OTHER,
    LEAD_TRIAGE,
    NOT_HEALTH,
    TREATMENT_REPORT,
    TRIAGE_OPTIONS,
)
from thenwhat.domain import ScreenOutcome, WorkOutcome

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
WHEN = datetime(2019, 5, 4, 10, 30, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW

    def sleep(self, seconds: float) -> None:  # pragma: no cover - never slept
        raise AssertionError("triage does not wait")

    def monotonic(self) -> float:  # pragma: no cover - never read
        return 0.0


class Headlines:
    """A decision backend that scores a headline by a word in it, counts its calls, and
    gives no answer for a headline that holds 'unanswerable'."""

    name = "fake"

    def __init__(self, session: Session, call_cost_usd: str = "0") -> None:
        self.session = session
        self.calls: list[list[str]] = []
        self.call_cost = Decimal(call_cost_usd)

    def _answer(self, text: str) -> BackendAnswer | None:
        if "unanswerable" in text:
            return None
        score = 0.9 if "trial" in text else 0.5 if "health" in text else 0.05
        rest = (1 - score) / 2
        choice = TREATMENT_REPORT if score > 0.5 else NOT_HEALTH
        return BackendAnswer(
            choice, {TREATMENT_REPORT: score, HEALTH_OTHER: rest, NOT_HEALTH: rest}
        )

    def _spend(self) -> None:
        if self.call_cost:
            self.session.add(
                LlmUsage(
                    purpose="decision:lead_triage",
                    model="synthetic-model",
                    input_tokens=100,
                    output_tokens=0,
                    cost_usd=self.call_cost,
                    created_at=NOW,
                )
            )

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.calls.append([state])
        self._spend()
        answer = self._answer(state)
        if answer is None:
            raise ValueError("no answer")
        return answer

    def answer_many(self, step, intro, question, items, options):
        assert (step, options) == (LEAD_TRIAGE, TRIAGE_OPTIONS)
        self.calls.append(list(items))
        self._spend()
        return [self._answer(text) for text in items]


def add_leads(
    session: Session, titles: list[str], *, outlet: str = "www.bbc.com"
) -> list[LinkLead]:
    posts = [
        SharedLink(
            url=f"https://{outlet}/news/health-{number}",
            community=HACKER_NEWS,
            shared_at=WHEN,
            score=10,
            title=title,
            item_number=number,
        )
        for number, title in enumerate(titles)
    ]
    load_links(same_session(session), HACKER_NEWS, posts, steps=[])
    run_step(same_session(session), LinkScreen(), Client(), now=lambda: NOW, attempt_limit=3)
    return list(session.scalars(select(LinkLead).order_by(LinkLead.id)))


def triage(session: Session, backend: Headlines, step: LinkTriage | None = None):
    return run_step(
        same_session(session),
        step or LinkTriage(Clock()),
        DecisionClient(lambda _: backend),
        now=lambda: NOW,
        attempt_limit=3,
    )


def log(session: Session) -> list[DecisionLog]:
    return list(session.scalars(select(DecisionLog).order_by(DecisionLog.id)))


# --- scoring -----------------------------------------------------------------------


def test_leads_in_scope_are_scored_twenty_to_a_call_with_a_log_entry_each(session: Session):
    """Scenario: A headline about a trial result"""
    leads = add_leads(session, [f"A trial result number {n}" for n in range(45)])
    backend = Headlines(session)

    report = triage(session, backend)

    assert [len(call) for call in backend.calls] == [20, 20, 5]
    assert (report.done, report.remaining_due) == (45, 0)
    assert all(lead.triage_score == pytest.approx(0.9) for lead in leads)
    assert all(lead.triage_version == 1 for lead in leads)
    entries = log(session)
    assert len(entries) == 45
    assert {entry.step for entry in entries} == {LEAD_TRIAGE}
    assert entries[0].input_ref == f"link_lead:{leads[0].id}"


def test_the_decision_is_shown_the_title_the_outlet_and_the_year_only(session: Session):
    """Scenario: Triage of ten thousand leads"""
    add_leads(session, ["A trial result"])
    backend = Headlines(session)

    triage(session, backend)

    # The test suite fails any connection, so finishing shows no outlet was asked.
    assert backend.calls == [["Headline: A trial result\nOutlet: bbc.com\nYear shared: 2019"]]


def test_a_lead_out_of_scope_is_never_triaged(session: Session):
    """Scenario: A lead out of scope"""
    [unlisted] = add_leads(session, ["A trial result"], outlet="github.com")
    backend = Headlines(session, call_cost_usd="1")

    report = triage(session, backend)

    assert unlisted.screen_outcome is ScreenOutcome.UNLISTED_OUTLET
    assert (report.processed, backend.calls, unlisted.triage_score) == (0, [], None)
    assert session.scalars(select(LlmUsage)).all() == []


def test_a_lead_the_backend_gives_no_answer_for_has_no_score(session: Session):
    """Scenario: The backend declines a question"""
    titles = [f"A trial result {n}" for n in range(19)] + ["An unanswerable headline"]
    leads = add_leads(session, titles)
    backend = Headlines(session, call_cost_usd="0.01")

    report = triage(session, backend)

    assert (report.done, report.failed, report.remaining_due) == (19, 1, 1)
    assert leads[-1].triage_score is None
    assert all(lead.triage_score == pytest.approx(0.9) for lead in leads[:-1])
    # One call for the batch, then the unanswered lead alone. Nothing is asked twice.
    assert [len(call) for call in backend.calls] == [20, 1]
    # Both calls stay paid for and logged: nothing was rolled back.
    assert len(session.scalars(select(LlmUsage)).all()) == 2
    failures = [entry for entry in log(session) if entry.error]
    assert {entry.input_ref for entry in failures} == {f"link_lead:{leads[-1].id}"}
    entry = session.scalars(
        select(WorkEntry).where(
            WorkEntry.step == "link_triage", WorkEntry.record_id == leads[-1].id
        )
    ).one()
    assert entry.outcome is WorkOutcome.FAILED and entry.error


# --- thresholds --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "pass_above", "reject_below", "expected"),
    [
        (None, 0.7, 0.2, Standing.NOT_SCORED),
        (0.9, None, None, Standing.UNDECIDED),
        (0.9, 0.7, None, Standing.UNDECIDED),
        (0.7, 0.7, 0.2, Standing.PASSED),
        (0.69, 0.7, 0.2, Standing.HELD),
        (0.2, 0.7, 0.2, Standing.HELD),
        (0.19, 0.7, 0.2, Standing.REJECTED),
    ],
)
def test_a_lead_stands_by_its_score_and_the_two_thresholds(
    score, pass_above, reject_below, expected
):
    assert standing_of(score, pass_above, reject_below) is expected


def test_with_no_threshold_set_every_scored_lead_is_undecided(session: Session):
    """Scenario: Thresholds not set"""
    add_leads(session, ["A trial result", "Some health news", "A football match"])
    triage(session, Headlines(session))

    assert standings(session, None, None) == {Standing.UNDECIDED: 3}
    assert standings(session, 0.7, None) == {Standing.UNDECIDED: 3}


def test_a_lowered_threshold_passes_more_leads_and_triages_nothing_again(session: Session):
    """Scenarios: A threshold is changed, A rejected lead"""
    leads = add_leads(session, ["A trial result", "Some health news", "A football match"])
    backend = Headlines(session)
    triage(session, backend)
    logged = len(log(session))

    strict = standings(session, 0.7, 0.2)
    loose = standings(session, 0.4, 0.2)

    assert strict == {Standing.PASSED: 1, Standing.HELD: 1, Standing.REJECTED: 1}
    assert loose == {Standing.PASSED: 2, Standing.REJECTED: 1}
    assert len(log(session)) == logged and len(backend.calls) == 1
    # The rejected lead and its score are kept.
    assert leads[2].triage_score == pytest.approx(0.05)


# --- versions ----------------------------------------------------------------------


def test_raising_the_version_scores_every_lead_again_and_keeps_the_earlier_log(
    session: Session,
):
    """Scenario: The question is reworded"""
    leads = add_leads(session, ["A trial result", "Some health news"])
    triage(session, Headlines(session))
    reworded = LinkTriage(Clock())
    reworded.version = 2

    report = triage(session, Headlines(session), reworded)

    assert report.done == 2
    assert all(lead.triage_version == 2 for lead in leads)
    assert len(log(session)) == 4
