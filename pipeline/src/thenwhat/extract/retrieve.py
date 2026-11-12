"""Getting the text of a news article, politely. Behavior: openspec claim-extraction.

The text is returned to the caller and kept nowhere: not cached, not logged.
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from thenwhat import __version__
from thenwhat.extract.page import Page, read_page
from thenwhat.sources.base import MissingContact

ROBOTS_NAME = "thenwhat"
WAYBACK_AVAILABLE = "https://archive.org/wayback/available"
# How a site answered when asked for one article.
ALLOWED = "allowed"
REFUSED_BY_ROBOTS = "robots"


class PasteNeeded(Exception):
    """The article cannot be fetched; the operator must supply its text."""


@dataclass(frozen=True, slots=True)
class Retrieved:
    text: str
    archive_url: str | None = None
    # The same page with what it says about itself: headline, date, the papers it links to.
    page: Page | None = None


@dataclass(frozen=True, slots=True)
class Probe:
    """How one article address answered, for the record of which outlets can be read."""

    # ALLOWED, or REFUSED_BY_ROBOTS when the site's rules forbid the fetch or cannot be read.
    robots: str
    # The page's HTTP status; None when it was not asked for or did not answer.
    status: int | None = None
    page: Page | None = None


class ArticleRetriever:
    def __init__(
        self, *, contact_email: str | None, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._contact = (contact_email or "").strip()
        self._client = httpx.Client(transport=transport, timeout=30.0, follow_redirects=True)
        # A site's rules are read once for as long as this retriever lives.
        self._rules: dict[str, RobotFileParser | bool] = {}

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
        html = self._page(url)
        if html is not None:
            return _retrieved(html)
        snapshot = self._snapshot(url)
        html = self._page(snapshot) if snapshot else None
        if html is None:
            raise PasteNeeded(
                f"{url} could not be retrieved and no archived snapshot was found."
                " Supply the article text instead."
            )
        return _retrieved(html, archive_url=snapshot)

    def allowed(self, url: str) -> bool:
        """Whether the site's own rules let this client fetch the address."""
        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        return self._allowed(url)

    def json(self, url: str) -> Any:
        """The JSON a platform's own interface for software serves at this address, or
        None when it does not answer with any."""
        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        response = self._get(url)
        if response is None or response.status_code != 200:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def probe(self, url: str) -> Probe:
        """Ask the site itself for one article and say how it answered. No archive is tried:
        the question is whether this outlet can be read."""
        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        if not self._allowed(url):
            return Probe(REFUSED_BY_ROBOTS)
        response = self._get(url)
        if response is None:
            return Probe(ALLOWED)
        page = read_page(response.text) if response.status_code == 200 else None
        return Probe(ALLOWED, response.status_code, page)

    def _get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response | None:
        headers = {"User-Agent": f"{ROBOTS_NAME}/{__version__} (mailto:{self._contact})"}
        try:
            return self._client.get(url, params=params, headers=headers)
        except httpx.TransportError:
            return None

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        site = f"{parts.scheme}://{parts.netloc}"
        if site not in self._rules:
            self._rules[site] = self._rules_of(site)
        rules = self._rules[site]
        return rules if isinstance(rules, bool) else rules.can_fetch(ROBOTS_NAME, url)

    def _rules_of(self, site: str) -> RobotFileParser | bool:
        """A site's rules, or one answer for every address when it has none to parse."""
        response = self._get(f"{site}/robots.txt")
        if response is None or response.status_code >= 500:
            return False  # rules unknown: do not fetch
        if response.status_code in (401, 403):
            return False
        if response.status_code >= 400:
            return True  # no robots.txt: nothing is disallowed
        rules = RobotFileParser()
        rules.parse(response.text.splitlines())
        return rules

    def _page(self, url: str) -> str | None:
        response = self._get(url)
        return response.text if response is not None and response.status_code == 200 else None

    def _snapshot(self, url: str) -> str | None:
        response = self._get(WAYBACK_AVAILABLE, {"url": url})
        if response is None or response.status_code != 200:
            return None
        closest = response.json().get("archived_snapshots", {}).get("closest", {})
        return closest.get("url") if closest.get("available") else None


def _retrieved(html: str, archive_url: str | None = None) -> Retrieved:
    page = read_page(html)
    return Retrieved(page.text, archive_url=archive_url, page=page)
