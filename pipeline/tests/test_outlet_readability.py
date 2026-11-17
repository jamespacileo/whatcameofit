"""Which outlets can be read: counted through `check_outlets` on a synthetic page reader and
a real database, worded through `report`, and run through the `outlets` command.

Scenario names are from openspec live-lookup and page-reading. Every page here is synthetic.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from reader_support import SyntheticReader
from reader_support import retriever as reader_retriever
from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.cli import app
from thenwhat.db.models import EntityMatch
from thenwhat.domain import Decider, ReviewState
from thenwhat.extract.page import Page
from thenwhat.extract.retrieve import ArticleRetriever
from thenwhat.outlets.readability import Measured, Outlet, check_outlets, report
from thenwhat.review.decisions import record_decision
from thenwhat.work.errors import ReaderUnavailable

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"
ARTICLE = f"""<html><head><meta property="og:title" content="Antibody regrows teeth">
<meta name="description" content="A drug restored missing teeth.">
<meta property="article:published_time" content="2026-03-04"></head>
<body><p>{"EX-1 regrew teeth in people born without them. " * 20}</p>
<a href="https://doi.org/10.1234/example.2026.0042">the paper</a></body></html>"""
# A page whose article is drawn by its scripts, as the page reader returns it: drawn.
DRAWN_BY_SCRIPT = f"""<html><head><title>News</title>
<meta property="article:published_time" content="2026-03-04"></head><body><div id='app'>
<p>{"The drawn article says EX-1 regrew teeth. " * 20}</p></div></body></html>"""
# A page with too little text to read.
THIN = "<html><head><title>Short</title></head><body><p>Subscribe to read.</p></body></html>"
WEB = {
    "https://open.example.org/first": httpx.Response(200, text=ARTICLE),
    "https://open.example.org/second": httpx.Response(200, text=DRAWN_BY_SCRIPT),
    "https://open.example.org/third": httpx.Response(200, text=THIN),
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
    """One claim with an approved trial and five articles at three outlets."""
    claim = add_claim(
        session,
        slug=SLUG,
        headline="Antibody regrows teeth",
        vertical="mouth-and-teeth",
        intervention="EX-1",
        indication="tooth agenesis",
    )
    for url in (
        "https://open.example.org/first",
        "https://open.example.org/second",
        "https://open.example.org/third",
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
    reader = SyntheticReader(web)
    reader.not_allowed["closed.example.org"] = "not allowed by the service"
    return reader_retriever(reader)


def test_each_outlet_is_counted_by_how_the_reader_answered(tracked: Session):
    """Scenarios: An outlet whose pages are drawn by scripts, An outlet the reader does not
    allow"""
    web = Web()
    outlets = {o.domain: o for o in check_outlets(tracked, retriever(web))}

    opened = outlets["open.example.org"]
    assert (opened.articles, opened.read, opened.thin, opened.refused) == (3, 2, 1, 0)
    assert opened.signals == {"headline": 3, "summary": 1, "date": 2, "paper link": 1}
    closed = outlets["closed.example.org"]
    assert (closed.articles, closed.refused, closed.read) == (1, 1, 0)
    assert "https://closed.example.org/story" not in web.urls
    paid = outlets["paid.example.org"]
    assert (paid.articles, paid.read, dict(paid.failed)) == (1, 0, {"402": 1})
    assert [(c.url, c.outcome, c.signals) for c in opened.checked] == [
        ("https://open.example.org/first", "read", ("headline", "summary", "date", "paper link")),
        ("https://open.example.org/second", "read", ("headline", "date")),
        ("https://open.example.org/third", "thin", ("headline",)),
    ]
    assert [c.outcome for c in (*closed.checked, *paid.checked)] == ["refused", "402"]


def test_an_outlet_the_reader_has_stopped_is_asked_once_and_then_held(tracked: Session):
    """Scenario: A stopped outlet is held for every command that reads articles"""
    from backfill_support import same_session

    web = Web()
    reader = SyntheticReader(web)
    reader.not_now["open.example.org"] = 3600

    def check() -> dict[str, Outlet]:
        found = check_outlets(
            tracked,
            reader_retriever(reader),
            open_session=same_session(tracked),
            now=lambda: NOW,
        )
        return {outlet.domain: outlet for outlet in found}

    first = check()

    # One request told the check; the outlet's two other articles were not asked for.
    assert dict(first["open.example.org"].failed) == {"not now": 1, "held": 2}
    assert sum("open.example.org" in body["url"] for body in reader.asked) == 1
    assert dict(first["paid.example.org"].failed) == {"402": 1}

    # A later check within the wait asks the outlet for nothing, though it would answer.
    reader.not_now.clear()
    reader.asked.clear()
    second = check()

    assert dict(second["open.example.org"].failed) == {"held": 3}
    assert not any("open.example.org" in body["url"] for body in reader.asked)
    assert second["paid.example.org"].articles == 1


def test_the_reader_down_stops_the_check_with_nothing_counted(tracked: Session):
    reader = SyntheticReader(Web())
    reader.answer = lambda: httpx.Response(503)

    with pytest.raises(ReaderUnavailable):
        check_outlets(tracked, reader_retriever(reader))


def test_a_lookup_is_measured_on_articles_that_were_read(tracked: Session):
    seen: list[tuple[str | None, list[str]]] = []

    def measure(page: Page, approved: list[str]) -> Measured | None:
        seen.append((page.headline, approved))
        return Measured(found=True, first=False) if page.summary else None

    outlets = check_outlets(tracked, retriever(Web()), measure=measure)

    opened = next(outlet for outlet in outlets if outlet.domain == "open.example.org")
    assert seen == [
        ("Antibody regrows teeth", ["NCT00000001"]),
        ("News", ["NCT00000001"]),
        ("Short", ["NCT00000001"]),
    ]
    # A lookup that could not be made is not counted as a miss.
    assert (opened.measured, opened.found, opened.first) == (1, 1, 0)
    assert [c.lookup for c in opened.checked] == ["found", "", ""]


def test_several_outlets_at_once_give_the_same_record(tracked: Session):
    """Scenario: Several outlets checked at the same time"""
    told: list[str] = []

    def measure(page: Page, approved: list[str]) -> Measured | None:
        return Measured(found=True, first=True)

    one_by_one = check_outlets(tracked, retriever(Web()), measure=measure)
    together = check_outlets(
        tracked,
        retriever(Web()),
        measure=measure,
        workers=3,
        on_article=lambda checked: told.append(checked.url),
    )

    assert together == one_by_one
    assert sorted(told) == sorted(c.url for outlet in together for c in outlet.checked)


def test_the_record_is_a_table_with_a_total_and_no_article_text():
    opened = Outlet("open.example.org", articles=2, read=1, thin=1, measured=1, found=1)
    opened.signals.update({"headline": 2, "paper link": 1})
    paid = Outlet("paid.example.org", articles=1)
    paid.failed["402"] += 1

    page = report([opened, paid], checked=date(2026, 11, 12))

    assert "Checked 2026-11-12" in page
    assert (
        "| open.example.org | 2 | 1 | 1 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |" in page
    )
    assert (
        "| paid.example.org | 1 | 0 | 0 | 0 | 0 | 402 ×1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"
        in page
    )
    assert (
        "| All outlets | 3 | 1 | 1 | 0 | 0 | 402 ×1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |" in page
    )


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.extract.make_retriever", lambda: retriever(Web()))
    runner = CliRunner()
    return lambda *arguments: runner.invoke(app, list(arguments), env={"COLUMNS": "300"})


def test_outlets_prints_and_saves_the_record(tracked: Session, run, tmp_path: Path):
    saved = tmp_path / "outlets.md"

    rows = tmp_path / "articles.csv"

    result = run("outlets", "--save", str(saved), "--articles", str(rows))

    assert result.exit_code == 0, result.output
    assert "| closed.example.org | 1 | 0 | 0 | 0 | 1 |" in result.output
    assert "| open.example.org | 3 | 2 | 1 | 0 | 0 |" in saved.read_text()
    assert "EX-1 regrew teeth" not in saved.read_text() + rows.read_text()
    assert rows.read_text().splitlines()[:3] == [
        "outlet,url,outcome,signals,lookup",
        "closed.example.org,https://closed.example.org/story,refused,,",
        "open.example.org,https://open.example.org/first,read,headline; summary; date; paper link,",
    ]


def test_outlets_with_no_article_tracked_explains_and_exits_1(run):
    result = run("outlets")

    assert result.exit_code == 1
    assert "No article is tracked" in result.output


@pytest.mark.parametrize("missing", ["body", "headline", "date"])
def test_preview_metadata_cannot_make_an_incomplete_page_readable(missing, monkeypatch):
    from thenwhat.outlets.readability import _check_article

    headline = "Article headline" if missing != "headline" else None
    date = "2026-03-04" if missing != "date" else None
    body = "Login required" if missing == "body" else "Article body. " * 60
    page = Page(text=body, headline=headline, published=date, summary="Preview. " * 100)

    from thenwhat.extract.retrieve import READ, Probe

    reader = retriever(Web())
    monkeypatch.setattr(reader, "probe", lambda url: Probe(READ, 200, page))
    outlet = Outlet("example.org")
    checked = _check_article(outlet, reader, "https://example.org/article", [], None)
    if missing == "body":
        assert (checked.outcome, outlet.thin, outlet.undated) == ("thin", 1, 0)
    else:
        assert (checked.outcome, outlet.thin, outlet.undated) == ("no date", 0, 1)
    assert outlet.read == 0
