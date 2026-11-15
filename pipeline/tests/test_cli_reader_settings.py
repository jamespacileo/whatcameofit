"""Every command that reads a page refuses, naming the setting, when no page reader is
configured, and sends nothing. Scenario: No reader configured (openspec page-reading).
Everything here is synthetic."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

import httpx
import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.claims.entry import add_article, add_claim
from thenwhat.cli import app

ARTICLE = "https://news.example.org/2026/teeth"


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    sent: list[str] = []

    def no_request(self, request: httpx.Request, **kwargs):
        sent.append(str(request.url))
        raise AssertionError(f"a request was sent: {request.url}")

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.session.open_session", test_session)
    monkeypatch.setattr(httpx.Client, "send", no_request)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("CONTACT_EMAIL", "ops@thenwhat.test")
    monkeypatch.setenv("LLM_MODEL", "test:scripted")
    monkeypatch.delenv("FIRECRAWL_API_URL", raising=False)
    monkeypatch.setenv("FIRECRAWL_API_KEY", "synthetic-key")
    runner = CliRunner()

    def invoke(*arguments: str):
        result = runner.invoke(app, list(arguments), env={"COLUMNS": "300"})
        return result, sent

    return invoke


@pytest.fixture
def tracked(session: Session) -> Session:
    add_claim(
        session,
        slug="tooth-regrowth-ex1",
        headline="Antibody regrows teeth",
        vertical="mouth-and-teeth",
        intervention="EX-1",
        indication="tooth agenesis",
    )
    add_article(
        session,
        "tooth-regrowth-ex1",
        url=ARTICLE,
        outlet="An outlet",
        title="A title",
        published_date=date(2026, 3, 4),
    )
    return session


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(
            (
                "extract",
                "new",
                "https://news.example.org/2026/other",
                *("--slug", "other-ex1", "--vertical", "mouth-and-teeth"),
                *("--outlet", "An outlet", "--title", "A title", "--published", "2026-03-04"),
            ),
            id="extract",
        ),
        pytest.param(("lookup", ARTICLE), id="lookup"),
        pytest.param(("statements", "tooth-regrowth-ex1"), id="statements"),
        pytest.param(("outlets",), id="outlets"),
    ],
)
def test_a_command_that_reads_a_page_refuses_with_no_reader_configured(
    run, tracked: Session, arguments: tuple[str, ...]
):
    result, sent = run(*arguments)

    assert result.exit_code == 1, result.output
    assert "FIRECRAWL_API_URL is not set" in result.output
    assert sent == []


def test_a_reader_with_no_key_is_refused_too(run, tracked: Session, monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_URL", "http://reader.test")
    monkeypatch.delenv("FIRECRAWL_API_KEY")

    result, sent = run("outlets")

    assert result.exit_code == 1
    assert "FIRECRAWL_API_KEY is not set" in result.output
    assert sent == []


def test_the_reading_step_refuses_before_any_lead_is_touched(
    run, tracked: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LEAD_PASS_ABOVE", "0.7")
    monkeypatch.setenv("LEAD_REJECT_BELOW", "0.2")
    monkeypatch.setenv("LEAD_EVALUATION_MIN_LABELS", "0")

    result, sent = run("backfill", "run", "link_read", "--limit", "1")

    assert result.exit_code == 1, result.output
    assert "FIRECRAWL_API_URL is not set" in result.output
    assert sent == []
