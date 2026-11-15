"""Getting an article's text through the page reader, tested through `ArticleRetriever`
on a synthetic reader.

Scenario names are from openspec page-reading and claim-extraction. Every page and every
reader answer here is synthetic.
"""

import ast
import logging
import threading
import time
from pathlib import Path

import httpx
import pytest

from reader_support import READER_URL, SyntheticReader, retriever
from thenwhat.backfill.errors import ReaderUnavailable
from thenwhat.extract.retrieve import (
    NOT_ALLOWED,
    NOT_NOW,
    NOT_SERVED,
    READ,
    ArticleRetriever,
    NotAllowed,
    NotNow,
    NotServed,
    Probe,
)

ARTICLE_URL = "https://news.example.org/2018/teeth"
SNAPSHOT_URL = "http://web.archive.org/web/20190101000000/https://news.example.org/2018/teeth"
MARKER = "Researchers say the & drug works on synthetic molars."
PAGE = """<html><head><title>Teeth</title><style>p { color: red }</style>
<meta property="og:title" content="Mice regrow teeth">
<meta property="article:published_time" content="2018-03-01T08:00:00Z">
<script>var tracking = "do not keep";</script></head>
<body><nav>Home Sport Weather</nav><main><h1>Mice regrow teeth</h1>
<p>Researchers say the &amp; drug works on synthetic molars.</p>
<a href="https://doi.org/10.1234/synthetic.5678">the paper</a> NCT01234567</main>
<footer>Cookie settings</footer></body></html>"""
SOURCE = Path(__file__).parents[1] / "src" / "thenwhat"


def site(pages: dict[str, httpx.Response]):
    def answer(request: httpx.Request) -> httpx.Response:
        return pages.get(str(request.url), httpx.Response(404))

    return answer


def reader_of(pages: dict[str, httpx.Response] | None = None) -> SyntheticReader:
    return SyntheticReader(site(pages or {ARTICLE_URL: httpx.Response(200, text=PAGE)}))


def test_a_read_page_is_returned_as_plain_text_from_its_main_content():
    reader = reader_of()

    retrieved = retriever(reader).retrieve(ARTICLE_URL)

    assert MARKER in retrieved.text
    assert "Home Sport Weather" not in retrieved.text and "Cookie settings" not in retrieved.text
    assert "tracking" not in retrieved.text and "color" not in retrieved.text
    assert retrieved.archive_url is None


def test_a_page_whose_text_exists_only_as_drawn_is_read():
    """Scenario: A page drawn by scripts"""
    # As served, the page holds only a script; the reader returns it as drawn.
    drawn = (
        "<html><head><title>Drawn</title></head>"
        "<body><main><p>Drawn text only.</p></main></body></html>"
    )

    reader = SyntheticReader(lambda request: httpx.Response(200, text=drawn))
    retrieved = retriever(reader).retrieve(ARTICLE_URL)

    assert retrieved.text == "Drawn text only."


def test_metadata_comes_from_the_head_and_links_of_the_page_as_drawn():
    page = retriever(reader_of()).retrieve(ARTICLE_URL).page

    assert page is not None
    assert page.headline == "Mice regrow teeth"
    assert page.published == "2018-03-01T08:00:00Z"
    assert page.dois == ("10.1234/synthetic.5678",)
    assert page.registry_numbers == ("NCT01234567",)


def test_not_allowed_carries_the_readers_reason_and_asks_for_the_text():
    """Scenario: Disallowed URL; An address the reader refuses for another reason"""
    reader = reader_of()
    reader.not_allowed["news.example.org"] = "the site's robots.txt disallows it"

    with pytest.raises(NotAllowed, match="robots.txt disallows it") as refused:
        retriever(reader).retrieve(ARTICLE_URL)

    assert refused.value.reason == "the site's robots.txt disallows it"
    assert "Supply the article text" in str(refused.value)


def test_not_now_says_when_the_site_may_be_asked_again():
    reader = reader_of()
    reader.not_now["news.example.org"] = 90

    with pytest.raises(NotNow, match="90 seconds") as later:
        retriever(reader).retrieve(ARTICLE_URL)

    assert later.value.retry_after_seconds == 90


def test_a_page_the_site_did_not_serve_is_not_served_with_its_status():
    """Scenario: The site did not serve the page; Dead link without a snapshot"""
    reader = reader_of({ARTICLE_URL: httpx.Response(404)})

    with pytest.raises(NotServed, match="answered 404") as missing:
        retriever(reader).retrieve(ARTICLE_URL)

    assert missing.value.status == 404
    # Scenario: The reader gives no page. The pipeline sends the site nothing of its own.
    assert reader.elsewhere == []


def test_a_copy_from_an_archive_keeps_the_archive_address_and_no_archive_is_asked():
    """Scenario: Dead link with a snapshot"""
    reader = reader_of()
    reader.archived[ARTICLE_URL] = SNAPSHOT_URL

    retrieved = retriever(reader).retrieve(ARTICLE_URL)

    assert retrieved.archive_url == SNAPSHOT_URL
    assert MARKER in retrieved.text
    assert reader.elsewhere == []  # the Internet Archive is sent nothing


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(lambda: httpx.Response(200, json={"weird": True}), id="unknown answer"),
        pytest.param(lambda: httpx.Response(200, text="not json"), id="not json"),
        pytest.param(
            lambda: httpx.Response(400, json={"success": False, "error": "bad"}), id="error"
        ),
        pytest.param(
            lambda: httpx.Response(200, json={"success": True, "data": {"metadata": {}}}),
            id="no status",
        ),
        pytest.param(lambda: httpx.Response(503), id="overloaded"),
        pytest.param(lambda: httpx.Response(429), id="too busy"),
    ],
)
def test_an_answer_that_is_none_of_the_four_is_the_reader_failing(answer):
    """Scenario: An answer the pipeline does not know"""
    reader = reader_of()
    reader.answer = answer

    with pytest.raises(ReaderUnavailable):
        retriever(reader).retrieve(ARTICLE_URL)
    with pytest.raises(ReaderUnavailable):
        retriever(reader).probe(ARTICLE_URL)  # not counted against the outlet


def test_no_answer_from_the_reader_is_the_reader_unavailable():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    unreachable = ArticleRetriever(
        reader_url=READER_URL,
        reader_key="k",
        contact_email=None,
        turns=threading.BoundedSemaphore(2),
        transport=httpx.MockTransport(down),
    )

    with pytest.raises(ReaderUnavailable, match="could not be reached"):
        unreachable.retrieve(ARTICLE_URL)


def test_a_wrong_key_is_the_reader_refusing_not_the_site():
    reader = reader_of()
    wrong = ArticleRetriever(
        reader_url=READER_URL,
        reader_key="not-the-key",
        contact_email=None,
        turns=threading.BoundedSemaphore(2),
        transport=httpx.MockTransport(reader),
    )

    with pytest.raises(ReaderUnavailable, match="FIRECRAWL_API_KEY"):
        wrong.retrieve(ARTICLE_URL)


def test_the_request_is_one_scrape_for_the_page_and_nothing_kept():
    reader = reader_of()

    retriever(reader).retrieve(ARTICLE_URL)

    assert reader.asked == [
        {"url": ARTICLE_URL, "formats": ["rawHtml", "html"], "maxAge": 0, "storeInCache": False}
    ]
    assert reader.elsewhere == []


def test_only_single_scrapes_are_sent_whatever_is_asked():
    """Scenario: A read that drafts a claim. The reader runs no model for the pipeline:
    no format but the page's is asked for, and no batch, crawl or map route is used."""
    reader = reader_of()
    asking = retriever(reader)

    asking.retrieve(ARTICLE_URL)
    asking.probe(ARTICLE_URL)

    assert {tuple(body["formats"]) for body in reader.asked} == {("rawHtml", "html")}
    assert all(set(body) == {"url", "formats", "maxAge", "storeInCache"} for body in reader.asked)
    assert reader.elsewhere == []  # nothing reached any route but /v2/scrape


def test_a_readers_answer_appears_in_no_log_record(caplog: pytest.LogCaptureFixture):
    """Scenario: After a read"""
    reader = reader_of()
    caplog.set_level(logging.DEBUG)

    retriever(reader).retrieve(ARTICLE_URL)
    with pytest.raises(NotServed):
        retriever(reader_of({ARTICLE_URL: httpx.Response(404, text=PAGE)})).retrieve(ARTICLE_URL)

    assert "synthetic molars" not in caplog.text


def test_no_more_requests_are_in_flight_than_allowed():
    """Two reads side by side at most, however many threads ask."""
    lock = threading.Lock()
    now = {"in flight": 0, "most": 0}

    def slow(request: httpx.Request) -> httpx.Response:
        with lock:
            now["in flight"] += 1
            now["most"] = max(now["most"], now["in flight"])
        time.sleep(0.05)
        with lock:
            now["in flight"] -= 1
        return httpx.Response(200, text=PAGE)

    shared = retriever(SyntheticReader(slow), at_once=2)
    threads = [threading.Thread(target=shared.retrieve, args=(ARTICLE_URL,)) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert now["most"] == 2


def test_a_probe_says_how_the_reader_answered():
    """Scenario: An outlet the reader does not allow"""
    refusing = "https://refusing.example.org/story"
    later = "https://busy.example.org/story"
    failing = "https://failing.example.org/story"
    reader = reader_of({ARTICLE_URL: httpx.Response(200, text=PAGE), failing: httpx.Response(402)})
    reader.not_allowed["refusing.example.org"] = "not allowed by the service"
    reader.not_now["busy.example.org"] = None
    probing = retriever(reader)

    read = probing.probe(ARTICLE_URL)
    assert (read.answer, read.status) == (READ, 200)
    assert read.page is not None and read.page.headline == "Mice regrow teeth"
    assert probing.probe(refusing) == Probe(NOT_ALLOWED)
    assert probing.probe(later) == Probe(NOT_NOW)
    assert probing.probe(failing) == Probe(NOT_SERVED, 402)


def _content_hash_comparisons() -> list[str]:
    """Every place in the pipeline that compares an article's content hash, by file."""
    found = []
    for path in SOURCE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Compare):
                names = [
                    part.attr
                    for part in ast.walk(node)
                    if isinstance(part, ast.Attribute) and part.attr == "content_hash"
                ]
                if names:
                    found.append(str(path.relative_to(SOURCE)))
    return found


def test_no_code_decides_whether_to_read_an_article_by_comparing_content_hashes():
    """A hash from a read through the reader differs from one recorded before. The one
    comparison only reports, after the read, whether the text changed."""
    assert set(_content_hash_comparisons()) == {"statements/service.py"}
    service = (SOURCE / "statements" / "service.py").read_text()
    assert "changed = hashlib.sha256(text.encode()).hexdigest() != article.content_hash" in service
