"""Outlet icons: fetched through `IconFetcher.fetch` on a fake transport, stored through
`fetch_outlet_icons`, and carried by the export. Scenario names are from openspec
site-publishing. Every image here is synthetic: a real signature followed by filler.
"""

import base64
import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.claims.entry import add_article, add_claim
from thenwhat.cli import app
from thenwhat.db.models import OutletIcon
from thenwhat.domain import ReviewState
from thenwhat.export.build import build_export
from thenwhat.outlets.icons import (
    MAX_ICON_BYTES,
    IconFetcher,
    fetch_outlet_icons,
    outlet_domain,
)
from thenwhat.review.queue import decide_item
from thenwhat.sources.base import MissingContact

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SITE = "https://www.news.example.org"
ARTICLE = f"{SITE}/2018/teeth"
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic icon"
ICO = b"\x00\x00\x01\x00" + b"synthetic icon"
ALLOW_ALL = httpx.Response(200, text="User-agent: *\nDisallow:\n")
CHECKED_IN_SCHEMA = Path(__file__).resolve().parents[2] / "site" / "export.schema.json"


class Web:
    """Answers by exact URL and records which URLs were asked for."""

    def __init__(self, answers: dict[str, httpx.Response]) -> None:
        self.answers = answers
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.answers.get(str(request.url), httpx.Response(404))

    @property
    def urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]


def fetcher(web: Web, fake_time, contact: str | None = "ops@thenwhat.test") -> IconFetcher:
    return IconFetcher(contact_email=contact, transport=httpx.MockTransport(web), time=fake_time)


def test_domain_is_the_host_without_www():
    assert outlet_domain("https://WWW.News.Example.org/2018/teeth?x=1") == "news.example.org"
    assert outlet_domain("not an address") == ""


def test_favicon_is_fetched_with_its_time_and_the_client_names_itself(fake_time):
    """Scenario: Outlet with an icon"""
    web = Web(
        {f"{SITE}/robots.txt": ALLOW_ALL, f"{SITE}/favicon.ico": httpx.Response(200, content=ICO)}
    )

    icon = fetcher(web, fake_time).fetch(SITE)

    assert (icon.url, icon.media_type, icon.content) == (
        f"{SITE}/favicon.ico",
        "image/x-icon",
        ICO,
    )
    assert icon.fetched_at == fake_time.now()
    assert web.urls == [f"{SITE}/robots.txt", f"{SITE}/favicon.ico"]
    for request in web.requests:
        assert "mailto:ops@thenwhat.test" in request.headers["User-Agent"]
    # Requests are spaced out, not sent back to back.
    assert fake_time.slept == [1.0]


def test_icon_named_by_the_home_page_is_used_when_there_is_no_favicon_file(fake_time):
    page = """<html><head>
      <link rel="icon" type="image/svg+xml" href="/icon.svg">
      <link rel="apple-touch-icon" sizes="180x180" href="/touch.png">
      <link rel="shortcut icon" sizes="32x32" href="https://static.example.net/icon-32.png">
      </head><body>Not kept.</body></html>"""
    web = Web(
        {
            f"{SITE}/robots.txt": ALLOW_ALL,
            f"{SITE}/": httpx.Response(200, text=page),
            "https://static.example.net/icon-32.png": httpx.Response(200, content=PNG),
        }
    )

    icon = fetcher(web, fake_time).fetch(SITE)

    declared = "https://static.example.net/icon-32.png"
    assert (icon.url, icon.media_type) == (declared, "image/png")
    # The other host's robots.txt was read before its file was asked for.
    assert web.urls.index("https://static.example.net/robots.txt") < web.urls.index(declared)
    assert f"{SITE}/icon.svg" not in web.urls


def test_robots_refusal_means_nothing_else_is_asked(fake_time):
    """Scenario: Outlet whose robots.txt refuses"""
    web = Web(
        {
            f"{SITE}/robots.txt": httpx.Response(200, text="User-agent: *\nDisallow: /\n"),
            f"{SITE}/favicon.ico": httpx.Response(200, content=ICO),
        }
    )

    icon = fetcher(web, fake_time).fetch(SITE)

    assert icon.content is None
    assert web.urls == [f"{SITE}/robots.txt"]


def test_unreadable_robots_means_nothing_else_is_asked(fake_time):
    web = Web({f"{SITE}/robots.txt": httpx.Response(503)})

    assert fetcher(web, fake_time).fetch(SITE).content is None
    assert web.urls == [f"{SITE}/robots.txt"]


@pytest.mark.parametrize(
    "body",
    [
        PNG + b"x" * MAX_ICON_BYTES,
        b"<html>Not an image, whatever the server calls it.</html>",
        b'<svg xmlns="http://www.w3.org/2000/svg"/>',
    ],
    ids=["too large", "not an image", "svg"],
)
def test_file_that_is_too_large_or_not_a_raster_image_is_not_kept(fake_time, body: bytes):
    """Scenario: Icon over the size cap"""
    web = Web(
        {
            f"{SITE}/robots.txt": ALLOW_ALL,
            f"{SITE}/favicon.ico": httpx.Response(
                200, content=body, headers={"Content-Type": "image/png"}
            ),
        }
    )

    assert fetcher(web, fake_time).fetch(SITE).content is None


def test_redirect_to_another_host_checks_that_hosts_robots(fake_time):
    web = Web(
        {
            f"{SITE}/robots.txt": ALLOW_ALL,
            f"{SITE}/favicon.ico": httpx.Response(
                302, headers={"Location": "https://cdn.example.net/favicon.ico"}
            ),
            "https://cdn.example.net/robots.txt": httpx.Response(
                200, text="User-agent: *\nDisallow: /\n"
            ),
            "https://cdn.example.net/favicon.ico": httpx.Response(200, content=ICO),
        }
    )

    assert fetcher(web, fake_time).fetch(SITE).content is None
    assert "https://cdn.example.net/favicon.ico" not in web.urls


def test_no_request_is_sent_without_a_contact_address(fake_time):
    web = Web({})

    with pytest.raises(MissingContact):
        fetcher(web, fake_time, contact=" ").fetch(SITE)

    assert web.requests == []


# --- storing -----------------------------------------------------------------------


def new_claim(session: Session, slug: str = "tooth-regrowth-ex1", url: str = ARTICLE) -> None:
    claim = add_claim(
        session,
        slug=slug,
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention=f"EX-1 antibody {slug}",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
    )
    add_article(
        session,
        slug,
        url=url,
        outlet="Example News",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
    )
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)


def test_each_domain_is_asked_once_and_its_icon_kept_with_the_fetch_time(
    session: Session, fake_time
):
    """Scenario: Outlet asked before"""
    new_claim(session)
    new_claim(session, "second-claim", f"{SITE}/2019/again")
    new_claim(session, "third-claim", "https://quiet.example.com/story")
    web = Web(
        {
            f"{SITE}/robots.txt": ALLOW_ALL,
            f"{SITE}/favicon.ico": httpx.Response(200, content=ICO),
            "https://quiet.example.com/robots.txt": ALLOW_ALL,
        }
    )

    first = fetch_outlet_icons(session, fetcher(web, fake_time))
    asked = len(web.requests)
    second = fetch_outlet_icons(session, fetcher(web, fake_time))

    assert (first.stored, first.none_found) == (["news.example.org"], ["quiet.example.com"])
    assert web.urls.count(f"{SITE}/favicon.ico") == 1
    kept = session.get(OutletIcon, "news.example.org")
    assert kept is not None
    assert (kept.content, kept.media_type, kept.icon_url) == (
        ICO,
        "image/x-icon",
        f"{SITE}/favicon.ico",
    )
    assert kept.fetched_at.tzinfo is not None and kept.fetched_at <= fake_time.now()
    # The second run asks nobody, not even the outlet that had no icon.
    assert (second.stored, second.none_found, second.already_asked) == ([], [], 2)
    assert len(web.requests) == asked


def test_retry_asks_again_only_the_outlets_that_had_no_icon(session: Session, fake_time):
    new_claim(session)
    new_claim(session, "third-claim", "https://quiet.example.com/story")
    web = Web(
        {
            f"{SITE}/robots.txt": ALLOW_ALL,
            f"{SITE}/favicon.ico": httpx.Response(200, content=ICO),
            "https://quiet.example.com/robots.txt": ALLOW_ALL,
        }
    )
    fetch_outlet_icons(session, fetcher(web, fake_time))
    web.answers["https://quiet.example.com/favicon.ico"] = httpx.Response(200, content=PNG)
    web.requests.clear()

    run = fetch_outlet_icons(session, fetcher(web, fake_time), retry_missing=True)

    assert (run.stored, run.already_asked) == (["quiet.example.com"], 1)
    assert all("quiet.example.com" in url for url in web.urls)


# --- export ------------------------------------------------------------------------


def exported(session: Session) -> dict[str, Any]:
    return json.loads(build_export(session, now=NOW).model_dump_json())


def test_export_carries_the_icon_itself_for_outlets_of_exported_articles(session: Session):
    """Scenario: Export of an outlet's icon"""
    new_claim(session)
    for domain, content in [("news.example.org", PNG), ("elsewhere.example.com", PNG)]:
        session.add(
            OutletIcon(
                domain=domain,
                icon_url=f"https://{domain}/favicon.ico",
                media_type="image/png",
                content=content,
                fetched_at=NOW,
            )
        )
    session.flush()

    export = exported(session)

    # Only the outlet of an exported article, as data: no address the site could fetch.
    assert export["outlets"] == [
        {
            "domain": "news.example.org",
            "icon": "data:image/png;base64," + base64.b64encode(PNG).decode(),
            "fetched_at": "2026-11-20T10:00:00Z",
        }
    ]
    jsonschema.validate(export, json.loads(CHECKED_IN_SCHEMA.read_text()))


def test_outlet_without_an_icon_is_absent_from_the_export(session: Session):
    new_claim(session)
    session.add(OutletIcon(domain="news.example.org", fetched_at=NOW))
    session.flush()

    assert exported(session)["outlets"] == []


# --- command -----------------------------------------------------------------------


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, fake_time):
    web = Web(
        {f"{SITE}/robots.txt": ALLOW_ALL, f"{SITE}/favicon.ico": httpx.Response(200, content=ICO)}
    )

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    new_claim(session)

    def invoke(contact: str | None):
        monkeypatch.setattr(
            "thenwhat.cli.icons.make_icon_fetcher", lambda: fetcher(web, fake_time, contact)
        )
        return CliRunner().invoke(app, ["icons"])

    return invoke


def test_icons_command_stores_icons_and_says_how_many(run, session: Session):
    result = run("ops@thenwhat.test")

    assert result.exit_code == 0, result.output
    assert "Stored 1 outlet icons" in result.output
    assert session.get(OutletIcon, "news.example.org") is not None


def test_icons_command_refuses_without_a_contact_address(run, session: Session):
    result = run(None)

    assert result.exit_code == 1
    assert "CONTACT_EMAIL" in result.output
    assert session.get(OutletIcon, "news.example.org") is None
