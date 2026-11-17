"""Extraction and edit commands: one success and one refusal each, for wiring only.

The rules are tested in test_extraction.py and test_article_retrieval.py.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entry import claim_count, find_claim, promises_of
from thenwhat.cli import app
from thenwhat.decide.core import BackendAnswer
from thenwhat.extract.retrieve import PasteNeeded, Retrieved
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.statements.service import StatementChecker

URL = "https://news.example.org/2018/teeth"
TEXT = "Synthetic article: an antibody called EX-1 regrew teeth in mice. Trials by 2025."
DRAFT: dict[str, Any] = {
    "headline": "Antibody regrows teeth in mice",
    "summary": "An antibody restored missing teeth in mice.",
    "intervention": "EX-1 antibody",
    "indication": "tooth agenesis",
    "promises": ["trials by 2025"],
    "statements": [
        {
            "text": "EX-1 grew new teeth in mice.",
            "kind": "effect",
            "firmness": "fact",
            "speaker": "article",
            "basis": "animals",
        },
        {
            # Nine words of the article in a row: refused as copied.
            "text": "An antibody called EX-1 regrew teeth in mice.",
            "kind": "effect",
            "firmness": "fact",
            "speaker": "article",
            "basis": "animals",
        },
    ],
}
NEW = [
    "extract",
    "new",
    URL,
    "--slug",
    "tooth-regrowth-ex1",
    "--vertical",
    "mouth-and-teeth",
    "--outlet",
    "Example News",
    "--title",
    "Mice regrow teeth",
    "--published",
    "2018-03-10",
]


class Checks:
    """The statement check, answering that the article says each statement."""

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


@pytest.fixture(autouse=True)
def rules_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Approval by rule is on by default. These tests are about what happens without it,
    unless one turns it on."""
    monkeypatch.setenv("MATCH_ACCEPT_ABOVE", "0")
    monkeypatch.setenv("APPROVE_DRAFTS_BY_RULE", "false")


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    """Invoke the CLI on the test session with a scripted model and a fake web."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    def respond(messages, info) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, DRAFT)])

    def configure(*, model: str | None = "test:scripted", web: Retrieved | Exception | None = None):
        settings = LlmSettings(model, Decimal("10"), Decimal("3"), Decimal("15"))
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

    NOW = datetime(2026, 11, 20, tzinfo=UTC)
    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    configure()
    runner = CliRunner()

    def invoke(*arguments: str, input: str | None = None, **configuration: Any) -> Result:
        if configuration:
            configure(**configuration)
        return runner.invoke(app, list(arguments), input=input)

    return invoke


def test_extract_new_drafts_a_pending_claim(run, session: Session):
    result = run(*NEW)

    assert result.exit_code == 0, result.output
    assert "tooth-regrowth-ex1" in result.output and "pending" in result.output
    assert find_claim(session, "tooth-regrowth-ex1") is not None
    # Reported statements are proposed and checked in the same command, and a refused
    # one is counted by its rule.
    assert (
        "Reported statements: 2 proposed, 1 approved by rule, 0 pending review,"
        " 1 refused by rule (copies the article: 1)."
    ) in " ".join(result.output.split())


def test_extract_new_that_cannot_fetch_asks_for_pasted_text_and_exits_1(run, session: Session):
    result = run(*NEW, web=PasteNeeded("The robots.txt of news.example.org does not allow it."))

    assert result.exit_code == 1
    assert "--paste" in result.output
    assert claim_count(session) == 0


def test_extract_article_reads_pasted_text_from_standard_input(run, session: Session):
    run(*NEW)
    never = PasteNeeded("the web must not be used when text is pasted")

    result = run(
        "extract",
        "article",
        "tooth-regrowth-ex1",
        "--article-url",
        URL,
        "--paste",
        input=TEXT,
        web=never,
    )

    claim = find_claim(session, "tooth-regrowth-ex1")
    assert result.exit_code == 0, result.output
    assert claim is not None and len(promises_of(session, claim)) == 1


def test_extract_article_without_a_configured_model_names_the_setting_and_exits_1(run):
    run(*NEW)

    result = run("extract", "article", "tooth-regrowth-ex1", "--article-url", URL, model=None)

    assert result.exit_code == 1
    assert "LLM_MODEL" in result.output


def test_claim_edit_corrects_the_headline(run, session: Session):
    run(*NEW)

    result = run("claim", "edit", "tooth-regrowth-ex1", "--headline", "Corrected headline")

    claim = find_claim(session, "tooth-regrowth-ex1")
    assert result.exit_code == 0, result.output
    assert claim is not None and claim.headline == "Corrected headline"


def test_claim_edit_refusal_explains_and_exits_1(run):
    result = run("claim", "edit", "no-such-claim", "--headline", "x")

    assert result.exit_code == 1
    assert "No claim has the slug" in result.output


def test_extract_new_with_the_rule_on_says_the_draft_is_published(
    run, monkeypatch: pytest.MonkeyPatch, session: Session
):
    monkeypatch.setenv("APPROVE_DRAFTS_BY_RULE", "true")

    result = run(*NEW)

    assert result.exit_code == 0, result.output
    assert "Approved by rule" in result.output
