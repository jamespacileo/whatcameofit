"""Getting an article's text, tested through `ArticleRetriever.retrieve` on a fake transport.

Scenario names are from openspec claim-extraction. Article text here is synthetic.
"""

import httpx
import pytest

from thenwhat.extract.retrieve import ArticleRetriever, PasteNeeded, Probe
from thenwhat.sources.base import MissingContact

ARTICLE_URL = "https://news.example.org/2018/teeth"
SNAPSHOT_URL = "http://web.archive.org/web/20190101000000/https://news.example.org/2018/teeth"
PAGE = """<html><head><title>Teeth</title><style>p { color: red }</style>
<script>var tracking = "do not keep";</script></head>
<body><h1>Mice regrow teeth</h1><p>Researchers say the &amp; drug works.</p></body></html>"""
ALLOW_ALL = httpx.Response(200, text="User-agent: *\nDisallow:\n")
NO_SNAPSHOT = httpx.Response(200, json={"archived_snapshots": {}})
SNAPSHOT = httpx.Response(
    200,
    json={
        "archived_snapshots": {"closest": {"available": True, "url": SNAPSHOT_URL, "status": "200"}}
    },
)


class Web:
    """Answers by URL and records which URLs were asked for."""

    def __init__(self, answers: dict[str, httpx.Response]) -> None:
        self.answers = answers
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        for prefix, answer in self.answers.items():
            if url.startswith(prefix):
                return answer
        return httpx.Response(404)

    @property
    def urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]


def retriever(web: Web, contact: str | None = "ops@thenwhat.test") -> ArticleRetriever:
    return ArticleRetriever(contact_email=contact, transport=httpx.MockTransport(web))


def test_allowed_page_is_returned_as_plain_text():
    web = Web(
        {
            "https://news.example.org/robots.txt": ALLOW_ALL,
            ARTICLE_URL: httpx.Response(200, text=PAGE),
        }
    )

    retrieved = retriever(web).retrieve(ARTICLE_URL)

    assert "Mice regrow teeth" in retrieved.text
    assert "Researchers say the & drug works." in retrieved.text
    assert "tracking" not in retrieved.text and "color" not in retrieved.text
    assert retrieved.archive_url is None


def test_disallowed_url_is_not_fetched_and_text_is_asked_for():
    """Scenario: Disallowed URL"""
    robots = httpx.Response(200, text="User-agent: *\nDisallow: /2018/\n")
    web = Web(
        {"https://news.example.org/robots.txt": robots, ARTICLE_URL: httpx.Response(200, text=PAGE)}
    )

    with pytest.raises(PasteNeeded, match="robots.txt"):
        retriever(web).retrieve(ARTICLE_URL)

    assert ARTICLE_URL not in web.urls


def test_rule_naming_this_client_is_respected():
    robots = httpx.Response(
        200, text="User-agent: thenwhat\nDisallow: /\n\nUser-agent: *\nDisallow:\n"
    )
    web = Web(
        {"https://news.example.org/robots.txt": robots, ARTICLE_URL: httpx.Response(200, text=PAGE)}
    )

    with pytest.raises(PasteNeeded):
        retriever(web).retrieve(ARTICLE_URL)


def test_site_without_robots_txt_may_be_fetched():
    web = Web({ARTICLE_URL: httpx.Response(200, text=PAGE)})

    assert "Mice regrow teeth" in retriever(web).retrieve(ARTICLE_URL).text


def test_unreadable_robots_txt_counts_as_disallowed():
    web = Web(
        {
            "https://news.example.org/robots.txt": httpx.Response(503),
            ARTICLE_URL: httpx.Response(200, text=PAGE),
        }
    )

    with pytest.raises(PasteNeeded):
        retriever(web).retrieve(ARTICLE_URL)

    assert ARTICLE_URL not in web.urls


def test_dead_link_with_a_snapshot_uses_the_snapshot():
    """Scenario: Dead link with a snapshot"""
    web = Web(
        {
            "https://news.example.org/robots.txt": ALLOW_ALL,
            ARTICLE_URL: httpx.Response(404),
            "https://archive.org/wayback/available": SNAPSHOT,
            SNAPSHOT_URL: httpx.Response(200, text=PAGE),
        }
    )

    retrieved = retriever(web).retrieve(ARTICLE_URL)

    assert "Mice regrow teeth" in retrieved.text
    assert retrieved.archive_url == SNAPSHOT_URL


def test_dead_link_without_a_snapshot_asks_for_the_text():
    """Scenario: Dead link without a snapshot"""
    web = Web(
        {
            "https://news.example.org/robots.txt": ALLOW_ALL,
            ARTICLE_URL: httpx.Response(404),
            "https://archive.org/wayback/available": NO_SNAPSHOT,
        }
    )

    with pytest.raises(PasteNeeded, match="no archived snapshot"):
        retriever(web).retrieve(ARTICLE_URL)


def test_site_that_cannot_be_reached_falls_back_to_the_archive():
    class Down(Web):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            if request.url.host == "news.example.org" and request.url.path != "/robots.txt":
                self.requests.append(request)
                raise httpx.ConnectError("refused")
            return super().__call__(request)

    web = Down(
        {
            "https://news.example.org/robots.txt": ALLOW_ALL,
            "https://archive.org/wayback/available": SNAPSHOT,
            SNAPSHOT_URL: httpx.Response(200, text=PAGE),
        }
    )

    assert retriever(web).retrieve(ARTICLE_URL).archive_url == SNAPSHOT_URL


def test_requests_identify_the_client():
    web = Web(
        {
            "https://news.example.org/robots.txt": ALLOW_ALL,
            ARTICLE_URL: httpx.Response(200, text=PAGE),
        }
    )

    retriever(web).retrieve(ARTICLE_URL)

    assert all("ops@thenwhat.test" in request.headers["User-Agent"] for request in web.requests)


def test_missing_contact_address_sends_nothing():
    web = Web({})

    with pytest.raises(MissingContact):
        retriever(web, contact=None).retrieve(ARTICLE_URL)

    assert web.requests == []


def test_a_probe_says_how_the_site_itself_answered():
    """Scenario: Outlet that can be read, outlet that refuses, outlet that fails"""
    refusing = "https://refusing.example.org/story"
    failing = "https://failing.example.org/story"
    web = Web(
        {
            "https://news.example.org/robots.txt": ALLOW_ALL,
            ARTICLE_URL: httpx.Response(200, text=PAGE),
            "https://refusing.example.org/robots.txt": httpx.Response(
                200, text="User-agent: *\nDisallow: /\n"
            ),
            "https://failing.example.org/robots.txt": ALLOW_ALL,
            failing: httpx.Response(402),
        }
    )
    probing = retriever(web)

    read = probing.probe(ARTICLE_URL)
    assert (read.robots, read.status) == ("allowed", 200)
    assert read.page is not None and read.page.headline == "Teeth"
    assert probing.probe(refusing) == Probe("robots")
    assert probing.probe(failing) == Probe("allowed", 402)
    # No archive is asked: the question is whether the outlet itself can be read.
    assert not any("archive.org" in url for url in web.urls)
    assert refusing not in web.urls
