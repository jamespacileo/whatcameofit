"""Which outlets can be read: counted through `check_outlets` on a fake transport and a real
database, worded through `report`, and run through the `outlets` command.

Scenario names are from openspec live-lookup. Every page here is synthetic.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.cli import app
from thenwhat.db.models import EntityMatch
from thenwhat.domain import Decider, ReviewState
from thenwhat.extract.page import Page
from thenwhat.extract.retrieve import ArticleRetriever
from thenwhat.outlets.readability import Measured, Outlet, check_outlets, report
from thenwhat.review.decisions import record_decision

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"
ALLOW_ALL = httpx.Response(200, text="User-agent: *\nDisallow:\n")
REFUSE_ALL = httpx.Response(200, text="User-agent: *\nDisallow: /\n")
ARTICLE = f"""<html><head><meta property="og:title" content="Antibody regrows teeth">
<meta name="description" content="A drug restored missing teeth."></head>
<body><p>{"EX-1 regrew teeth in people born without them. " * 20}</p>
<a href="https://doi.org/10.1234/example.2026.0042">the paper</a></body></html>"""
DRAWN_BY_SCRIPT = "<html><head><title>News</title></head><body><div id='app'></div></body></html>"
WEB = {
    "https://open.example.org/robots.txt": ALLOW_ALL,
    "https://open.example.org/first": httpx.Response(200, text=ARTICLE),
    "https://open.example.org/second": httpx.Response(200, text=DRAWN_BY_SCRIPT),
    "https://closed.example.org/robots.txt": REFUSE_ALL,
    "https://www.paid.example.org/robots.txt": ALLOW_ALL,
    "https://www.paid.example.org/story": httpx.Response(402),
}


class Web:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.urls.append(str(request.url))
        return WEB.get(str(request.url), httpx.Response(404))


@pytest.fixture
def tracked(session: Session) -> Session:
    """One claim with an approved trial and four articles at three outlets."""
    claim = add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth",
        vertical="dental-regeneration",
        intervention="EX-1",
        indication="tooth agenesis",
    )
    for url in (
        "https://open.example.org/first",
        "https://open.example.org/second",
        "https://closed.example.org/story",
        "https://www.paid.example.org/story",
    ):
        add_article(
            session,
            SLUG,
            url=url,
            outlet="An outlet",
            title="A title",
            published_date=date(2026, 3, 4),
        )
    match = EntityMatch(
        entity_id=entities_of(session, claim)[0].id,
        source_name="clinicaltrials.gov",
        external_id="NCT00000001",
        score=0.9,
    )
    record_decision(match, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.add(match)
    session.flush()
    return session


def retriever(web: Web) -> ArticleRetriever:
    return ArticleRetriever(contact_email="ops@thenwhat.test", transport=httpx.MockTransport(web))


def test_each_outlet_is_counted_by_how_its_site_answered(tracked: Session, fake_time):
    """Scenario: Outlet that can be read, outlet that refuses, outlet that fails"""
    web = Web()
    outlets = {o.domain: o for o in check_outlets(tracked, retriever(web), time=fake_time)}

    opened = outlets["open.example.org"]
    assert (opened.articles, opened.read, opened.thin, opened.refused) == (2, 1, 1, 0)
    assert opened.signals == {"headline": 2, "summary": 1, "paper link": 1}
    closed = outlets["closed.example.org"]
    assert (closed.articles, closed.refused, closed.read) == (1, 1, 0)
    assert "https://closed.example.org/story" not in web.urls
    paid = outlets["paid.example.org"]
    assert (paid.articles, paid.read, dict(paid.failed)) == (1, 0, {"402": 1})
    assert [(c.url, c.outcome, c.signals) for c in opened.checked] == [
        ("https://open.example.org/first", "read", ("headline", "summary", "paper link")),
        ("https://open.example.org/second", "thin", ("headline",)),
    ]
    assert [c.outcome for c in (*closed.checked, *paid.checked)] == ["refused", "402"]
    # The second article of the same outlet waits its turn.
    assert fake_time.slept == [1.0]


def test_a_lookup_is_measured_on_articles_that_were_read(tracked: Session, fake_time):
    seen: list[tuple[str | None, list[str]]] = []

    def measure(page: Page, approved: list[str]) -> Measured | None:
        seen.append((page.headline, approved))
        return Measured(found=True, first=False) if page.summary else None

    outlets = check_outlets(tracked, retriever(Web()), time=fake_time, measure=measure)

    opened = next(outlet for outlet in outlets if outlet.domain == "open.example.org")
    assert seen == [("Antibody regrows teeth", ["NCT00000001"]), ("News", ["NCT00000001"])]
    # A lookup that could not be made is not counted as a miss.
    assert (opened.measured, opened.found, opened.first) == (1, 1, 0)
    assert [c.lookup for c in opened.checked] == ["found", ""]


def test_the_record_is_a_table_with_a_total_and_no_article_text():
    opened = Outlet("open.example.org", articles=2, read=1, thin=1, measured=1, found=1)
    opened.signals.update({"headline": 2, "paper link": 1})
    paid = Outlet("paid.example.org", articles=1)
    paid.failed["402"] += 1

    page = report([opened, paid], checked=date(2026, 11, 12))

    assert "Checked 2026-11-12" in page
    assert "| open.example.org | 2 | 1 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |" in page
    assert (
        "| paid.example.org | 1 | 0 | 0 | 0 | 402 ×1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |" in page
    )
    assert "| All outlets | 3 | 1 | 1 | 0 | 402 ×1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |" in page


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.extract.make_retriever", lambda: retriever(Web()))
    monkeypatch.setattr("thenwhat.outlets.readability.SECONDS_BETWEEN_REQUESTS", 0.0)
    runner = CliRunner()
    return lambda *arguments: runner.invoke(app, list(arguments), env={"COLUMNS": "300"})


def test_outlets_prints_and_saves_the_record(tracked: Session, run, tmp_path: Path):
    saved = tmp_path / "outlets.md"

    rows = tmp_path / "articles.csv"

    result = run("outlets", "--save", str(saved), "--articles", str(rows))

    assert result.exit_code == 0, result.output
    assert "| closed.example.org | 1 | 0 | 0 | 1 |" in result.output
    assert "| open.example.org | 2 | 1 | 1 | 0 |" in saved.read_text()
    assert "EX-1 regrew teeth" not in saved.read_text() + rows.read_text()
    assert rows.read_text().splitlines()[:3] == [
        "outlet,url,outcome,signals,lookup",
        "closed.example.org,https://closed.example.org/story,refused,,",
        "open.example.org,https://open.example.org/first,read,headline; summary; paper link,",
    ]


def test_outlets_with_no_article_tracked_explains_and_exits_1(run):
    result = run("outlets")

    assert result.exit_code == 1
    assert "No article is tracked" in result.output
