"""Review commands: wiring, messages and exit codes only. Rules: test_review.py."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entry import add_article, add_claim
from thenwhat.cli import app
from thenwhat.db.models import Claim, EvidenceEvent
from thenwhat.domain import ClaimStatus, EventType, EvidenceStage, ReviewState, TrialPhase
from thenwhat.events.manual import add_manual_event

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, list(arguments), env={"COLUMNS": "200"})

    return invoke


@pytest.fixture
def claim(session: Session) -> Claim:
    claim = add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth in mice",
        vertical="dental-regeneration",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
    )
    add_article(
        session,
        SLUG,
        url="https://news.example.org/teeth",
        outlet="Example News",
        title="t",
        published_date=date(2018, 3, 10),
    )
    return claim


@pytest.fixture
def event(session: Session, claim: Claim) -> EvidenceEvent:
    return add_manual_event(
        session,
        SLUG,
        type=EventType.TRIAL_REGISTERED,
        event_date=date(2024, 9, 1),
        source_url="https://registry.example/NCT1",
        summary="Phase 1 trial registered.",
        external_id="NCT1",
        trial_phases=[TrialPhase.PHASE_1],
        now=NOW,
    )


def test_review_list_shows_items_with_kind_id_and_source(run, claim: Claim, event: EvidenceEvent):
    result = run("review", "list")

    assert result.exit_code == 0, result.output
    assert f"claim {claim.id}" in result.output and f"event {event.id}" in result.output
    assert "https://registry.example/NCT1" in result.output


def test_review_list_says_when_the_queue_is_empty(run):
    result = run("review", "list")

    assert result.exit_code == 0
    assert "The review queue is empty." in result.output


def test_review_approve_approves_and_updates_status(run, claim: Claim, event: EvidenceEvent):
    result = run("review", "approve", "event", str(event.id))

    assert result.exit_code == 0, result.output
    assert event.review_state is ReviewState.APPROVED
    assert claim.current_status is ClaimStatus.TRIAL_REGISTERED


def test_review_reject_rejects(run, event: EvidenceEvent):
    result = run("review", "reject", "event", str(event.id))

    assert result.exit_code == 0, result.output
    assert event.review_state is ReviewState.REJECTED


def test_review_approve_of_an_unknown_item_explains_and_exits_1(run):
    result = run("review", "approve", "match", "999999")

    assert result.exit_code == 1
    assert "There is no match with id 999999" in result.output


def test_review_flag_failure_flags_the_trial(run, claim: Claim, event: EvidenceEvent):
    run("review", "approve", "event", str(event.id))

    result = run(
        "review",
        "flag-failure",
        SLUG,
        "--trial",
        "NCT1",
        "--event",
        str(event.id),
        "--source-url",
        "https://registry.example/NCT1/results",
    )

    assert result.exit_code == 0, result.output
    assert claim.current_status is ClaimStatus.FAILED


def test_review_flag_failure_without_a_source_explains_and_exits_1(run, event: EvidenceEvent):
    run("review", "approve", "event", str(event.id))

    result = run(
        "review",
        "flag-failure",
        SLUG,
        "--trial",
        "NCT1",
        "--event",
        str(event.id),
        "--source-url",
        "",
    )

    assert result.exit_code == 1
    assert "source link" in result.output


def test_review_stage_sets_the_evidence_stage(run, claim: Claim):
    result = run("review", "stage", SLUG, "animal")

    assert result.exit_code == 0, result.output
    assert claim.evidence_stage is EvidenceStage.ANIMAL
