"""Fetch and event commands: wiring, messages and exit codes only.

The rules are tested in test_fetch_events.py and test_trial_events.py.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import add_claim
from thenwhat.cli import app
from thenwhat.db.models import EntityMatch, EvidenceEvent
from thenwhat.domain import Decider, ReviewState
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"
NCT = "NCT02586935"


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, fixture_json):
    study = fixture_json("clinicaltrials/study_NCT02586935.json")

    class Trials:
        def fetch_trial(self, nct_id: str) -> SourceRecord | None:
            url = f"https://clinicaltrials.gov/study/{nct_id}"
            return SourceRecord("clinicaltrials.gov", nct_id, url, study, NOW)

    class Nothing:
        def paper(self, doi: str) -> None:
            return None

        def citing_papers(self, paper: SourceRecord) -> list[SourceRecord]:
            return []

        def notices(self, doi: str) -> list:
            return []

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr(
        "thenwhat.cli.events.make_evidence_sources", lambda s: (Trials(), Nothing(), Nothing())
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    claim = add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth in mice",
        vertical="dental-regeneration",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
    )
    match = EntityMatch(
        entity_id=entities_of(session, claim)[0].id,
        source_name="clinicaltrials.gov",
        external_id=NCT,
        score=0.9,
    )
    record_decision(match, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.add(match)
    session.flush()
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, list(arguments))

    return invoke


def test_fetch_records_events_and_shows_the_status(run, session: Session):
    result = run("fetch", SLUG)

    assert result.exit_code == 0, result.output
    assert "Recorded 3 new events" in result.output and "0 await review" in result.output
    assert "Status: phase_2" in result.output
    assert len(session.scalars(select(EvidenceEvent)).all()) == 3


def test_fetch_of_an_unknown_claim_explains_and_exits_1(run):
    result = run("fetch", "no-such-claim")

    assert result.exit_code == 1
    assert "No claim has the slug" in result.output


EVENT = [
    "event",
    "add",
    SLUG,
    "--type",
    "regulatory_decision",
    "--date",
    "2026-03-01",
    "--source-url",
    "https://regulator.example/notices/1",
    "--summary",
    "Regulator approved the product.",
]


def test_event_add_stores_a_pending_event(run, session: Session):
    result = run(*EVENT, "--outcome", "approved")

    [event] = session.scalars(select(EvidenceEvent)).all()
    assert result.exit_code == 0, result.output
    assert "pending review" in result.output
    assert event.review_state is ReviewState.PENDING


def test_event_add_for_a_trial_takes_identifier_and_phases(run, session: Session):
    result = run(
        "event",
        "add",
        SLUG,
        "--type",
        "trial_registered",
        "--date",
        "2024-09-01",
        "--source-url",
        "https://jrct.example/jRCT2051240089",
        "--summary",
        "Phase 1 trial registered in Japan.",
        "--source-name",
        "jRCT",
        "--id",
        "jRCT2051240089",
        "--phase",
        "phase_1",
        "--phase",
        "phase_2",
    )

    [event] = session.scalars(select(EvidenceEvent)).all()
    assert result.exit_code == 0, result.output
    assert (event.source_name, event.trial_phases) == ("jRCT", ["phase_1", "phase_2"])


def test_event_add_refusal_explains_and_exits_1(run, session: Session):
    result = run(*EVENT)

    assert result.exit_code == 1
    assert "outcome" in result.output
    assert session.scalars(select(EvidenceEvent)).all() == []
