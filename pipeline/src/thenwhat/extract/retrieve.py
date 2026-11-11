"""Getting the text of a news article, politely. Behavior: openspec claim-extraction.

The text is returned to the caller and kept nowhere: not cached, not logged.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from thenwhat import __version__
from thenwhat.sources.base import MissingContact

ROBOTS_NAME = "thenwhat"
WAYBACK_AVAILABLE = "https://archive.org/wayback/available"
SKIPPED_ELEMENTS = {"script", "style", "noscript", "template", "svg"}


class PasteNeeded(Exception):
    """The article cannot be fetched; the operator must supply its text."""


@dataclass(frozen=True, slots=True)
class Retrieved:
    text: str
    archive_url: str | None = None


class ArticleRetriever:
    def __init__(
        self, *, contact_email: str | None, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._contact = (contact_email or "").strip()
        self._client = httpx.Client(transport=transport, timeout=30.0, follow_redirects=True)

    def retrieve(self, url: str) -> Retrieved:
        """The article as plain text: from the site if robots.txt allows it, else from
        an archived snapshot. Raises PasteNeeded when neither is possible."""
        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        if not self._allowed(url):
            raise PasteNeeded(
                f"The robots.txt of {urlsplit(url).netloc} does not allow fetching {url}."
                " Supply the article text instead."
            )
        page = self._page(url)
        if page is not None:
            return Retrieved(_plain_text(page))
        snapshot = self._snapshot(url)
        page = self._page(snapshot) if snapshot else None
        if page is None:
            raise PasteNeeded(
                f"{url} could not be retrieved and no archived snapshot was found."
                " Supply the article text instead."
            )
        return Retrieved(_plain_text(page), archive_url=snapshot)

    def _get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response | None:
        headers = {"User-Agent": f"{ROBOTS_NAME}/{__version__} (mailto:{self._contact})"}
        try:
            return self._client.get(url, params=params, headers=headers)
        except httpx.TransportError:
            return None

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        response = self._get(f"{parts.scheme}://{parts.netloc}/robots.txt")
        if response is None or response.status_code >= 500:
            return False  # rules unknown: do not fetch
        if response.status_code in (401, 403):
            return False
        if response.status_code >= 400:
            return True  # no robots.txt: nothing is disallowed
        rules = RobotFileParser()
        rules.parse(response.text.splitlines())
        return rules.can_fetch(ROBOTS_NAME, url)

    def _page(self, url: str) -> str | None:
        response = self._get(url)
        return response.text if response is not None and response.status_code == 200 else None

    def _snapshot(self, url: str) -> str | None:
        response = self._get(WAYBACK_AVAILABLE, {"url": url})
        if response is None or response.status_code != 200:
            return None
        closest = response.json().get("archived_snapshots", {}).get("closest", {})
        return closest.get("url") if closest.get("available") else None


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.pieces: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_ELEMENTS:
            self._skipping += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_ELEMENTS and self._skipping:
            self._skipping -= 1

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.pieces.append(data)


def _plain_text(html: str) -> str:
    collector = _TextCollector()
    collector.feed(html)
    return " ".join(" ".join(collector.pieces).split())
