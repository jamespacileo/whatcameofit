"""Entity and resolve commands: wiring, messages and exit codes only.

The rules are tested in test_resolution.py and test_decide.py.
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
from thenwhat.db.models import DecisionLog, EntityMatch
from thenwhat.decide.core import BackendAnswer
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"


class Trials:
    def search_trials(self, intervention: str) -> list[SourceRecord]:
        payload = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}
        return [SourceRecord("clinicaltrials.gov", "NCT00000001", "https://x.test", payload, NOW)]


class Dois:
    def work(self, doi: str) -> SourceRecord | None:
        return None


class Backend:
    name = "fake"

    def __init__(self, broken: bool = False) -> None:
        self.broken = broken

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        if self.broken:
            raise RuntimeError("no model")
        rest = 0.2 / (len(options) - 1)
        return BackendAnswer(options[0], {o: 0.8 if o == options[0] else rest for o in options})


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.resolve.make_registries", lambda s: (Trials(), Dois()))
    monkeypatch.setattr("thenwhat.cli.resolve.make_backend", lambda s: Backend())
    add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth in mice",
        vertical="dental-regeneration",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
    )
    runner = CliRunner()

    def invoke(*arguments: str, broken_backend: bool = False) -> Result:
        if broken_backend:
            monkeypatch.setattr("thenwhat.cli.resolve.make_backend", lambda s: Backend(broken=True))
        return runner.invoke(app, list(arguments))

    return invoke


def names(session: Session) -> list[str]:
    from thenwhat.claims.entry import find_claim

    claim = find_claim(session, SLUG)
    assert claim is not None
    return [entity.name for entity in entities_of(session, claim)]


def test_entity_add_adds_the_entity(run, session: Session):
    result = run(
        "entity", "add", SLUG, "--type", "paper", "--name", "A paper", "--doi", "10.1000/x"
    )

    assert result.exit_code == 0, result.output
    assert "A paper" in names(session)


def test_entity_add_refusal_explains_and_exits_1(run):
    result = run("entity", "add", SLUG, "--type", "intervention", "--name", "Another drug")

    assert result.exit_code == 1
    assert "entity synonym" in result.output


def test_entity_synonym_records_the_name(run, session: Session):
    result = run("entity", "synonym", SLUG, "EX-1 antibody", "TRG-999")

    assert result.exit_code == 0, result.output
    assert "TRG-999" in result.output


def test_entity_origin_paper_marks_the_paper(run, session: Session):
    run("entity", "add", SLUG, "--type", "paper", "--name", "A paper")

    result = run("entity", "origin-paper", SLUG, "A paper")

    assert result.exit_code == 0, result.output
    assert "Origin paper" in result.output


def test_resolve_stores_pending_candidates_and_suggests_a_stage(run, session: Session):
    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "1 new candidate match" in result.output and "NCT00000001" in result.output
    assert "Suggested evidence stage: in_vitro" in result.output
    assert len(session.scalars(select(EntityMatch)).all()) == 1


def test_resolve_of_an_unknown_claim_explains_and_exits_1(run):
    result = run("resolve", "no-such-claim")

    assert result.exit_code == 1
    assert "No claim has the slug" in result.output


def test_resolve_with_a_failing_backend_keeps_the_failure_on_record(run, session: Session):
    result = run("resolve", SLUG, broken_backend=True)

    assert result.exit_code == 1
    assert "No candidates were stored" in result.output
    assert session.scalars(select(EntityMatch)).all() == []
    assert [entry.error is not None for entry in session.scalars(select(DecisionLog))] == [True]
