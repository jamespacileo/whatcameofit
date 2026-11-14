"""The statements command: wiring only. The rules are tested in
test_reported_statements.py. Scenario names are from openspec claim-extraction."""

import hashlib
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entry import add_article, add_claim
from thenwhat.cli import app
from thenwhat.db.models import ReportedStatement, SourceArticle
from thenwhat.decide.core import BackendAnswer
from thenwhat.domain import Decider, ReviewState
from thenwhat.extract.retrieve import PasteNeeded, Retrieved
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.review.decisions import record_decision
from thenwhat.statements.service import StatementChecker

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SLUG = "knee-gel-gx7"
URL = "https://news.example.org/2026/knee-gel"
TEXT = "Synthetic article: a gel called GX-7 eased knee pain in forty people in a study."
STATEMENTS = [
    {
        "text": "GX-7 eased knee pain in a small study in people.",
        "kind": "effect",
        "firmness": "fact",
        "speaker": "article",
        "basis": "people",
    }
]


class Checks:
    name = "fake"

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer]:
        return [
            BackendAnswer(options[0], {o: 0.9 if o == options[0] else 0.05 for o in options})
            for _ in items
        ]

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise AssertionError("Statements are checked together.")


class FakeRetriever:
    def __init__(self, outcome: Retrieved | Exception) -> None:
        self.outcome = outcome

    def retrieve(self, url: str) -> Retrieved:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def article(session: Session) -> SourceArticle:
    """An approved claim's article, first read with the same text the fake web serves."""
    claim = add_claim(
        session,
        slug=SLUG,
        headline="A gel was reported to ease knee pain",
        vertical="mouth-and-teeth",
        intervention="GX-7",
        indication="knee osteoarthritis",
    )
    article = add_article(
        session, SLUG, url=URL, outlet="Example News", title="Gel", published_date=date(2026, 3, 1)
    )
    article.content_hash = hashlib.sha256(TEXT.encode()).hexdigest()
    record_decision(claim, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
    session.flush()
    return article


@pytest.fixture
def prompts() -> list[str]:
    """What the scripted model was shown, one entry per call."""
    return []


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, prompts: list[str]):
    """Invoke the CLI on the test session with a scripted model and a fake web."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    def respond(messages, info) -> ModelResponse:
        prompts.append(str(messages))
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"statements": STATEMENTS})]
        )

    def configure(*, web: Retrieved | Exception | None = None) -> None:
        settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
        monkeypatch.setattr(
            "thenwhat.cli.extract.make_llm",
            lambda s: Llm(s, settings, model=FunctionModel(respond), now=lambda: NOW),
        )
        monkeypatch.setattr(
            "thenwhat.cli.extract.make_retriever", lambda: FakeRetriever(web or Retrieved(TEXT))
        )
        monkeypatch.setattr(
            "thenwhat.cli.extract.make_checker", lambda s: StatementChecker(Checks())
        )

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    configure()
    runner = CliRunner()

    def invoke(*arguments: str, input: str | None = None, **configuration: Any) -> Result:
        if configuration:
            configure(**configuration)
        return runner.invoke(app, list(arguments), input=input)

    return invoke


def statements(session: Session) -> list[ReportedStatement]:
    session.flush()
    return list(session.scalars(select(ReportedStatement).order_by(ReportedStatement.id)))


def output(result: Result) -> str:
    return " ".join(result.output.split())


def test_statements_reads_a_decided_claims_article_for_statements(
    run, session: Session, article: SourceArticle
):
    """Scenario: Approved claim with no statements"""
    result = run("statements", SLUG)

    assert result.exit_code == 0, result.output
    assert "1 proposed, 1 approved by rule" in output(result)
    [stored] = statements(session)
    assert stored.source_article_id == article.id
    assert "has changed since it was first read" not in output(result)


def test_an_article_that_cannot_be_read_asks_for_pasted_text_and_exits_1(
    run, session: Session, article: SourceArticle
):
    """Scenario: Article that cannot be read"""
    refused = PasteNeeded(f"The robots.txt of news.example.org does not allow fetching {URL}.")

    result = run("statements", SLUG, web=refused)

    assert result.exit_code == 1
    assert URL in output(result) and "Pasted text is needed" in output(result)
    assert statements(session) == []


def test_an_article_whose_text_has_changed_is_named(run, session: Session, article: SourceArticle):
    """Scenario: Article whose text has changed"""
    article.content_hash = hashlib.sha256(b"the text as first read").hexdigest()

    result = run("statements", SLUG)

    assert result.exit_code == 0, result.output
    assert "the article has changed since it was first read" in output(result)
    assert len(statements(session)) == 1


def test_a_second_run_reads_nothing_and_asks_no_model(
    run, prompts: list[str], article: SourceArticle
):
    """Scenario: Second run with no change"""
    run("statements", SLUG)
    never = PasteNeeded("the web must not be asked again")

    result = run("statements", SLUG, web=never)

    assert result.exit_code == 0, result.output
    assert "already has reported statements" in output(result)
    assert len(prompts) == 1


def test_pasted_text_is_read_from_standard_input(run, session: Session, article: SourceArticle):
    never = PasteNeeded("the web must not be used when text is pasted")

    result = run("statements", SLUG, "--paste", input=TEXT, web=never)

    assert result.exit_code == 0, result.output
    assert len(statements(session)) == 1


def test_statements_without_claims_or_missing_explains_and_exits_1(run):
    result = run("statements")

    assert result.exit_code == 1
    assert "--missing" in output(result)
