"""Entry commands: one success and one refusal each, to prove wiring, message and exit code.

The rules themselves are tested in test_claim_entry.py and test_csv_import.py.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entry import (
    add_article,
    add_claim,
    articles_of,
    claim_count,
    find_claim,
    promises_of,
)
from thenwhat.cli import app

ARTICLE_URL = "https://news.example.org/2018/teeth"
CSV_HEADER = (
    "slug,headline,vertical,intervention,indication,article_url,outlet,article_title,published_date"
)


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    """Invoke the CLI with its database session replaced by the test session."""

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, list(arguments))

    return invoke


@pytest.fixture
def claim_with_article(session: Session):
    claim = add_claim(
        session,
        slug="tooth-regrowth-usag1",
        headline="Antibody regrows teeth in mice",
        vertical="dental-regeneration",
        intervention="USAG-1 antibody",
        indication="tooth agenesis",
    )
    add_article(
        session,
        claim.slug,
        url=ARTICLE_URL,
        outlet="Example News",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
    )
    return claim


CLAIM_ADD = [
    "claim",
    "add",
    "enamel-gel",
    "--headline",
    "Gel regrows enamel",
    "--intervention",
    "Enamel gel",
    "--indication",
    "enamel loss",
]


def test_claim_add_creates_the_claim(run, session: Session):
    result = run(*CLAIM_ADD, "--vertical", "dental-regeneration")

    assert result.exit_code == 0, result.output
    assert "enamel-gel" in result.output
    assert find_claim(session, "enamel-gel") is not None


def test_claim_add_refusal_explains_and_exits_1(run, session: Session):
    result = run(*CLAIM_ADD, "--vertical", "hair-regrowth-typo")

    assert result.exit_code == 1
    assert "Valid verticals: dental-regeneration" in result.output
    assert claim_count(session) == 0


def test_article_add_attaches_the_article(run, session: Session, claim_with_article):
    result = run(
        "article",
        "add",
        "tooth-regrowth-usag1",
        "--url",
        "https://news.example.org/2021/update",
        "--outlet",
        "Example News",
        "--title",
        "Tooth drug heads for trials",
        "--published",
        "2021-04-02",
    )

    assert result.exit_code == 0, result.output
    assert len(articles_of(session, claim_with_article)) == 2


def test_article_add_refusal_explains_and_exits_1(run):
    result = run(
        "article",
        "add",
        "no-such-claim",
        "--url",
        ARTICLE_URL,
        "--outlet",
        "o",
        "--title",
        "t",
        "--published",
        "2021-04-02",
    )

    assert result.exit_code == 1
    assert "No claim has the slug 'no-such-claim'" in result.output


def test_promise_add_records_the_promise_and_shows_its_date(
    run, session: Session, claim_with_article
):
    result = run(
        "promise",
        "add",
        "tooth-regrowth-usag1",
        "--article-url",
        ARTICLE_URL,
        "--text",
        "human trials by 2025",
    )

    assert result.exit_code == 0, result.output
    assert "2025-12-31" in result.output
    assert len(promises_of(session, claim_with_article)) == 1


def test_promise_add_refusal_explains_and_exits_1(run, claim_with_article):
    result = run(
        "promise",
        "add",
        "tooth-regrowth-usag1",
        "--article-url",
        "https://news.example.org/unknown",
        "--text",
        "by 2025",
    )

    assert result.exit_code == 1
    assert "has no article" in result.output


def test_claim_rename_slug_renames(run, session: Session, claim_with_article):
    result = run("claim", "rename-slug", "tooth-regrowth-usag1", "tooth-regrowth")

    assert result.exit_code == 0, result.output
    assert find_claim(session, "tooth-regrowth") is not None


def test_claim_rename_slug_refusal_explains_and_exits_1(run):
    result = run("claim", "rename-slug", "no-such-claim", "new-name")

    assert result.exit_code == 1
    assert "No claim has the slug 'no-such-claim'" in result.output


def test_claim_import_csv_imports_the_file(run, session: Session, tmp_path: Path):
    file = tmp_path / "claims.csv"
    file.write_text(
        f"{CSV_HEADER}\n"
        "enamel-gel,Gel regrows enamel,dental-regeneration,Enamel gel,enamel loss,"
        "https://news.example.org/gel,Example News,Gel regrows enamel,2019-08-30\n"
    )

    result = run("claim", "import-csv", str(file))

    assert result.exit_code == 0, result.output
    assert "1 claim" in result.output
    assert find_claim(session, "enamel-gel") is not None


def test_claim_import_csv_refusal_names_the_row_and_exits_1(run, session: Session, tmp_path: Path):
    file = tmp_path / "claims.csv"
    file.write_text(
        f"{CSV_HEADER}\n"
        "enamel-gel,Gel regrows enamel,dental-regeneration,Enamel gel,enamel loss,"
        ",Example News,Gel regrows enamel,2019-08-30\n"
    )

    result = run("claim", "import-csv", str(file))

    assert result.exit_code == 1
    assert "Nothing was imported" in result.output
    assert "row 2: article_url is missing" in result.output
    assert claim_count(session) == 0
