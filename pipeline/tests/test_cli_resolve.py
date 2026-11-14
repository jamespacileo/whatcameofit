"""Entity and resolve commands: wiring, messages and exit codes only.

The rules are tested in test_resolution.py and test_decide.py.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import add_claim
from thenwhat.cli import app
from thenwhat.cli.resolve import Research
from thenwhat.db.models import DecisionLog, EntityMatch
from thenwhat.decide.core import BackendAnswer
from thenwhat.domain import Decider
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.openalex import OpenAlex

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"


class Trials:
    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        payload = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}
        return [SourceRecord("clinicaltrials.gov", "NCT00000001", "https://x.test", payload, NOW)]

    def search_phrase(self, phrase: str, condition: str | None) -> list[SourceRecord]:
        return []


class Dois:
    def work(self, doi: str) -> SourceRecord | None:
        return None


class Papers:
    def search_papers(
        self, terms: list[str], condition: str, limit: int = 20
    ) -> list[SourceRecord]:
        payload = {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1000/found",
            "title": "EX-1 antibody in tooth agenesis",
            "publication_year": 2019,
            "type": "article",
        }
        return [
            SourceRecord("openalex", "10.1000/found", "https://doi.org/10.1000/found", payload, NOW)
        ]

    def paper(self, external_id: str) -> SourceRecord | None:
        return None


class Nothing:
    """Europe PMC, the trial registry and ROR, with nothing to say."""

    def trial_numbers(self, *, doi: str | None = None, pubmed_id: str | None = None) -> list[str]:
        return []

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        return None

    def organisations(self, name: str) -> list[SourceRecord]:
        return []


def research(papers: Papers | OpenAlex | None = None) -> Research:
    return Research(papers=papers, numbers=Nothing(), registry=Nothing(), organisations=Nothing())


class Backend:
    name = "fake"

    def __init__(self, broken: bool = False) -> None:
        self.broken = broken

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        if self.broken:
            raise RuntimeError("no model")
        rest = 0.2 / (len(options) - 1)
        return BackendAnswer(options[0], {o: 0.8 if o == options[0] else rest for o in options})


@pytest.fixture(autouse=True)
def rules_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Approval by rule is on by default. These tests are about what happens without it,
    unless one turns it on."""
    monkeypatch.setenv("MATCH_ACCEPT_ABOVE", "0")
    monkeypatch.setenv("APPROVE_DRAFTS_BY_RULE", "false")


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    # The command reads its settings; the database itself is the test session above.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.delenv("MATCH_REJECT_BELOW", raising=False)
    monkeypatch.setattr("thenwhat.cli.resolve.make_registries", lambda s: (Trials(), Dois()))
    monkeypatch.setattr("thenwhat.cli.resolve.make_backend", lambda s: Backend())
    monkeypatch.setattr("thenwhat.cli.resolve.make_research", lambda s: research())
    add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
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


def test_entity_phrase_records_the_search_phrase(run, session: Session):
    result = run("entity", "phrase", SLUG, "EX-1 antibody", "tooth regrowth antibody")

    assert result.exit_code == 0, result.output
    assert "tooth regrowth antibody" in result.output


def test_entity_phrase_refuses_a_generic_word(run, session: Session):
    result = run("entity", "phrase", SLUG, "EX-1 antibody", "the device")

    assert result.exit_code == 1
    assert "what kind of thing" in result.output


def test_entity_phrases_gives_a_claim_search_phrases(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    def respond(messages, info) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"search_phrases": ["tooth regrowth"]})]
        )

    settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    monkeypatch.setattr(
        "thenwhat.cli.extract.make_llm",
        lambda s: Llm(s, settings, model=FunctionModel(respond), now=lambda: NOW),
    )

    result = run("entity", "phrases", SLUG)

    assert result.exit_code == 0, result.output
    assert "tooth regrowth" in result.output and "1 of 1" in result.output


def test_entity_phrases_refuses_without_claims_or_missing(run, session: Session):
    result = run("entity", "phrases")

    assert result.exit_code == 1
    assert "--missing" in result.output


def test_entity_people_lists_and_delete_people_removes_the_marked(run, session: Session):
    run("entity", "add", SLUG, "--type", "person", "--name", "Rae Reporter")
    run("entity", "add", SLUG, "--type", "person", "--name", "Ada Example")

    listed = run("entity", "people")
    reporter = next(line for line in listed.output.splitlines() if "Rae Reporter" in line)
    result = run("entity", "delete-people", reporter.split()[0])

    assert SLUG in reporter
    assert result.exit_code == 0, result.output
    assert "Rae Reporter" not in names(session)
    assert "Ada Example" in names(session)


def test_entity_delete_people_refuses_an_entity_that_is_not_a_person(run, session: Session):
    from thenwhat.claims.entry import find_claim

    claim = find_claim(session, SLUG)
    assert claim is not None
    [intervention] = entities_of(session, claim)

    result = run("entity", "delete-people", str(intervention.id))

    assert result.exit_code == 1
    assert "no person entity" in result.output
    assert names(session) == ["EX-1 antibody"]


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


def test_resolve_approves_a_confident_candidate_by_rule_by_default(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("MATCH_ACCEPT_ABOVE")

    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "1 approved by rule" in result.output
    [match] = session.scalars(select(EntityMatch)).all()
    assert match.reviewed_by is Decider.RULE


def test_resolve_stores_the_related_papers_it_finds(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("thenwhat.cli.resolve.make_research", lambda s: research(Papers()))
    monkeypatch.setenv("MATCH_ACCEPT_ABOVE", "0.8")

    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "Found 1 related paper: 1 approved by rule" in result.output
    assert "approved 0.80  10.1000/found" in result.output
    paper = session.scalars(select(EntityMatch).where(EntityMatch.source_name == "openalex")).one()
    assert paper.reviewed_by is Decider.RULE


def test_resolve_says_what_the_paper_search_sent_and_what_is_left(
    run, session: Session, monkeypatch: pytest.MonkeyPatch, fixture_json, fake_time
):
    answer = httpx.Response(
        200,
        json=fixture_json("openalex/search_median_nerve_tourette.json"),
        headers={
            "X-RateLimit-Cost-USD": "0.001",
            "X-RateLimit-Remaining-USD": "0.994",
            "X-RateLimit-Prepaid-Remaining-USD": "0",
        },
    )
    client = OpenAlex(
        session,
        contact_email="ops@thenwhat.test",
        api_key="test-key-not-a-real-one",
        transport=httpx.MockTransport(lambda request: answer),
        time=fake_time,
    )
    monkeypatch.setattr("thenwhat.cli.resolve.make_research", lambda s: research(client))

    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "Found 3 related papers" in result.output
    assert (
        "OpenAlex: 1 search sent ($0.001), $0.994 of the free allowance left today."
        in result.output
    )
    assert "test-key" not in result.output


def test_resolve_says_plainly_when_the_paper_search_found_nothing(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    class NoPapers(Papers):
        def search_papers(
            self, terms: list[str], condition: str, limit: int = 20
        ) -> list[SourceRecord]:
            return []

    monkeypatch.setattr("thenwhat.cli.resolve.make_research", lambda s: research(NoPapers()))

    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "The paper search found nothing for this claim." in result.output
    assert session.scalars(select(EntityMatch)).one().source_name == "clinicaltrials.gov"


def test_resolve_rescore_scores_the_pending_papers_again(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    class Known(Papers):
        def paper(self, external_id: str) -> SourceRecord | None:
            return self.search_papers([], "")[0]

    monkeypatch.setattr("thenwhat.cli.resolve.make_research", lambda s: research(Known()))
    run("resolve", SLUG)

    result = run("resolve", SLUG, "--rescore")

    assert result.exit_code == 0, result.output
    assert "Scored 1 pending paper again; a rule decided 0." in result.output


def test_resolve_keeps_its_trial_candidates_when_the_paper_search_breaks(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    class BrokenPapers(Papers):
        def search_papers(
            self, terms: list[str], condition: str, limit: int = 20
        ) -> list[SourceRecord]:
            raise KeyError("results")

    monkeypatch.setattr("thenwhat.cli.resolve.make_research", lambda s: research(BrokenPapers()))

    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "Papers were not searched for" in result.output
    assert session.scalars(select(EntityMatch)).one().source_name == "clinicaltrials.gov"


def test_resolve_without_the_literature_key_says_paper_search_is_off(run, session: Session):
    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "Paper search is off: OPENALEX_API_KEY is not set." in result.output
    assert session.scalars(select(EntityMatch)).one().source_name == "clinicaltrials.gov"


def test_resolve_rescore_scores_the_pending_candidates_again(run, session: Session):
    run("resolve", SLUG)

    result = run("resolve", SLUG, "--rescore")

    assert result.exit_code == 0, result.output
    assert "Scored 1 pending candidate again" in result.output
    assert len(session.scalars(select(EntityMatch)).all()) == 1


def test_resolve_says_how_many_candidates_the_rule_rejected(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    # The fake backend scores every candidate 0.8; a threshold above that rejects it.
    monkeypatch.setenv("MATCH_REJECT_BELOW", "0.9")

    result = run("resolve", SLUG)

    assert result.exit_code == 0, result.output
    assert "1 rejected by rule" in result.output and "review list --by-rule" in result.output
    [match] = session.scalars(select(EntityMatch)).all()
    assert match.reviewed_by is Decider.RULE


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
