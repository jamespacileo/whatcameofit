"""A synthetic page reader for tests: it answers as the operator's Firecrawl service is
asked to (openspec page-reading), from a synthetic web of sites. No live request is made.

Every page it serves is made up in the test that uses it, so no article text is in a
fixture.
"""

import json
import re
import threading
from collections.abc import Callable

import httpx

from thenwhat.extract.retrieve import ArticleRetriever

READER_URL = "http://reader.test"
READER_KEY = "synthetic-reader-key"
MAIN = re.compile(r"<main[^>]*>(.*)</main>", re.DOTALL | re.IGNORECASE)

Site = Callable[[httpx.Request], httpx.Response]


def no_site(request: httpx.Request) -> httpx.Response:
    return httpx.Response(404)


class SyntheticReader:
    """The page reader as a transport. A request to the reader is answered from `site`,
    which answers as each site would; any other request goes to `site` directly, as the
    platforms' own interfaces that `json` asks are still asked."""

    def __init__(self, site: Site = no_site) -> None:
        self.site = site
        # Host -> reason: the reader answers NOT_ALLOWED for every address on it.
        self.not_allowed: dict[str, str] = {}
        # Host -> seconds: the reader answers NOT_NOW for every address on it.
        self.not_now: dict[str, float | None] = {}
        # Address -> archive address the reader says its copy came from.
        self.archived: dict[str, str] = {}
        # What the reader was asked: each scrape request's body.
        self.asked: list[dict] = []
        # Anything else that reached the reader's host, or any site directly.
        self.elsewhere: list[str] = []
        # When set, every request to the reader gets this answer instead.
        self.answer: Callable[[], httpx.Response] | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != "reader.test":
            self.elsewhere.append(str(request.url))
            return self.site(request)
        if request.method != "POST" or request.url.path != "/v2/scrape":
            self.elsewhere.append(str(request.url))
            return httpx.Response(404)
        if request.headers.get("authorization") != f"Bearer {READER_KEY}":
            return httpx.Response(401, json={"success": False, "error": "Unauthorized"})
        body = json.loads(request.content)
        self.asked.append(body)
        if self.answer is not None:
            return self.answer()
        url = body["url"]
        host = httpx.URL(url).host
        if host in self.not_allowed:
            return httpx.Response(
                403,
                json={"success": False, "code": "NOT_ALLOWED", "reason": self.not_allowed[host]},
            )
        if host in self.not_now:
            answer: dict = {"success": False, "code": "NOT_NOW", "reason": "rate limited"}
            if self.not_now[host] is not None:
                answer["retryAfter"] = self.not_now[host]
            return httpx.Response(429, json=answer)
        served = self.site(httpx.Request("GET", url))
        metadata: dict = {"statusCode": served.status_code, "sourceURL": url}
        if url in self.archived:
            metadata["archiveUrl"] = self.archived[url]
        drawn = served.text
        found = MAIN.search(drawn)
        main = found.group(1) if found else drawn
        return httpx.Response(
            200,
            json={"success": True, "data": {"rawHtml": drawn, "html": main, "metadata": metadata}},
        )


def retriever(
    reader: SyntheticReader | Site, *, at_once: int = 2, contact: str | None = "ops@thenwhat.test"
) -> ArticleRetriever:
    """A retriever that asks the synthetic reader. A plain site function is wrapped in one."""
    if not isinstance(reader, SyntheticReader):
        reader = SyntheticReader(reader)
    return ArticleRetriever(
        reader_url=READER_URL,
        reader_key=READER_KEY,
        contact_email=contact,
        turns=threading.BoundedSemaphore(at_once),
        transport=httpx.MockTransport(reader),
    )
