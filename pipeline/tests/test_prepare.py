"""Preparing many claims for review in one command: which steps each claim needs
(`plan_claims`, on a real database) and the `prepare` command with its steps faked."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.claims.entry import (
    ClaimNotFound,
    add_article,
    add_claim,
    find_article,
    find_claim,
)
from thenwhat.cli import app
from thenwhat.domain import Decider, ReviewState
from thenwhat.prepare import plan_claims, steps_for
from thenwhat.review.decisions import record_decision

NOW = datetime(2026, 11, 20, tzinfo=UTC)


def claim_with_articles(session: Session, slug: str, *urls: str) -> None:
    add_claim(
        session,
        slug=slug,
        headline="Antibody regrows teeth in mice",
        vertical="dental-regeneration",
        intervention=f"EX-1 antibody {slug}",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
    )
    for number, url in enumerate(urls, 1):
        add_article(
            session,
            slug,
            url=url,
            outlet="Example News",
            title=f"Report {number}",
            published_date=date(2018, 3, number),
        )


def test_a_claim_needs_its_unread_articles_read_then_a_search_then_a_fetch(session: Session):
    claim_with_articles(session, "one", "https://news.example.org/a", "https://news.example.org/b")
    one = find_claim(session, "one")
    assert one is not None
    read = find_article(session, one, "https://news.example.org/a")
    assert read is not None
    read.content_hash = "already read"
    session.flush()

    [plan] = plan_claims(session, ["one"])

    assert plan.unread_articles == ["https://news.example.org/b"]
    assert steps_for(plan) == [
        ["extract", "article", "one", "--article-url", "https://news.example.org/b"],
        ["resolve", "one"],
        ["fetch", "one"],
    ]


def test_a_decided_claim_is_searched_and_fetched_but_its_articles_are_not_read(session: Session):
    claim_with_articles(session, "one", "https://news.example.org/a")
    one = find_claim(session, "one")
    assert one is not None
    record_decision(one, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.flush()

    [plan] = plan_claims(session, ["one"])

    assert plan.unread_articles == []
    assert steps_for(plan) == [["resolve", "one"], ["fetch", "one"]]


def test_without_names_every_claim_awaiting_review_is_planned(session: Session):
    claim_with_articles(session, "pending-one", "https://news.example.org/a")
    claim_with_articles(session, "decided-one", "https://news.example.org/b")
    decided = find_claim(session, "decided-one")
    assert decided is not None
    record_decision(decided, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)
    session.flush()

    assert [plan.slug for plan in plan_claims(session, None)] == ["pending-one"]


def test_an_unknown_claim_is_refused_before_anything_runs(session: Session):
    with pytest.raises(ClaimNotFound, match="no-such-claim"):
        plan_claims(session, ["no-such-claim"])


# --- the command -----------------------------------------------------------------------


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    ran: list[list[str]] = []

    def fake_step(arguments: list[str]) -> tuple[bool, str]:
        ran.append(arguments)
        failed = arguments[0] == "extract" and arguments[-1].endswith("/blocked")
        return (not failed, "could not be read" if failed else "done")

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.prepare.run_step", fake_step)
    runner = CliRunner()
    return lambda *arguments: (runner.invoke(app, list(arguments), env={"COLUMNS": "200"}), ran)


def test_prepare_runs_every_step_and_carries_on_after_an_article_that_cannot_be_read(
    run, session: Session
):
    claim_with_articles(session, "one", "https://news.example.org/blocked")

    result, ran = run("prepare", "one")

    assert result.exit_code == 0, result.output
    assert [step[0] for step in ran] == ["extract", "resolve", "fetch"]
    assert "one" in result.output and "could not be read" in result.output


def test_prepare_with_no_claims_named_explains_and_exits_1(run):
    result, ran = run("prepare")

    assert result.exit_code == 1
    assert "--pending" in result.output
    assert ran == []
