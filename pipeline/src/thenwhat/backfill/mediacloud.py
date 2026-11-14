"""Media Cloud's story search. Terms, key and allowance: docs/sources.md.

A search returns each story's address, outlet, title and date. Media Cloud does not
release article text, and this client never asks for the expanded form. Any field that
could hold text is still removed before a result leaves this module, so that none can
be stored, logged or written to a fixture.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from thenwhat import __version__
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.errors import BackfillError, SourceStop
from thenwhat.backfill.outlet_kinds import outlet_of
from thenwhat.sources.base import MissingContact, SourceError, SourceUnavailable, SystemTime, Time

API = "https://search.mediacloud.org/api/search/story-list"
PLATFORM = "onlinenews-mediacloud"
# Fields that could carry an article's words. Never kept.
TEXT_FIELDS = frozenset(
    ["text", "article_text", "body", "content", "snippet", "excerpt", "summary", "description"]
)
# News before this is outside what the tracker follows.
EARLIEST = date(2010, 1, 1)


class MissingKey(BackfillError):
    """No Media Cloud key is configured, so no request may be sent."""


class NothingToSearch(BackfillError):
    """No collection or outlet is named. Media Cloud refuses a search that names
    neither, so no request may be sent."""


class SourceRejectedKey(SourceStop):
    """Media Cloud did not accept the key. Every record would fail the same way, so
    the run ends without counting an attempt against any of them."""


@dataclass(frozen=True, slots=True)
class Story:
    url: str
    outlet: str
    title: str
    published: date | None
    # What Media Cloud returned for the story, with any text field removed.
    raw: dict[str, Any]


def without_text(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key.lower() not in TEXT_FIELDS}


class MediaCloud:
    name = "mediacloud"

    def __init__(
        self,
        *,
        api_key: str | None,
        contact_email: str | None,
        allowances: Allowances,
        collection_ids: str = "",
        source_ids: str = "",
        transport: httpx.BaseTransport | None = None,
        time: Time | None = None,
    ) -> None:
        self._key = (api_key or "").strip()
        self._contact = (contact_email or "").strip()
        self._allowances = allowances
        self._collections = _ids(collection_ids)
        self._sources = _ids(source_ids)
        self._time = time or SystemTime()
        self._client = httpx.Client(transport=transport, timeout=60.0)
        self.requests_made = 0

    def check_ready(self) -> None:
        """Refuse before any record is touched when a search could not be sent."""
        if not self._key:
            raise MissingKey(
                "MEDIACLOUD_API_KEY is not set, so no search was sent. "
                "Create the Media Cloud account and key yourself; see docs/sources.md."
            )
        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        if not (self._collections or self._sources):
            raise NothingToSearch(
                "Neither MEDIACLOUD_COLLECTION_IDS nor MEDIACLOUD_SOURCE_IDS is set, so no "
                "search was sent. Media Cloud searches only the collections and outlets "
                "it is given; take their ids from its directory (docs/sources.md)."
            )

    def search(self, query: str, *, limit: int) -> list[Story]:
        """The stories that match a query, newest window first as Media Cloud orders
        them, up to `limit`. One request, counted against the shared allowance."""
        self.check_ready()
        self._allowances.claim(self.name)
        self.requests_made += 1
        params = {
            "q": query,
            "start": EARLIEST.isoformat(),
            "end": self._time.now().date().isoformat(),
            "platform": PLATFORM,
            "page_size": str(limit),
        }
        if self._collections:
            params["cs"] = self._collections
        if self._sources:
            params["ss"] = self._sources
        headers = {
            "Authorization": f"Token {self._key}",
            "Accept": "application/json",
            "User-Agent": f"thenwhat/{__version__} (mailto:{self._contact})",
        }
        try:
            response = self._client.get(API, params=params, headers=headers)
        except httpx.TransportError as error:
            raise SourceUnavailable(f"{self.name} could not be reached: {error}") from None
        if response.status_code == 429:
            raise self._allowances.refused(self.name, _retry_after(response))
        if response.status_code in (401, 403):
            raise SourceRejectedKey(
                f"{self.name} did not accept the key (status {response.status_code}). "
                "Check MEDIACLOUD_API_KEY."
            )
        if response.status_code >= 500:
            raise SourceUnavailable(f"{self.name} answered with status {response.status_code}.")
        if not response.is_success:
            raise SourceError(f"{self.name} refused the search with status {response.status_code}.")
        stories = []
        for result in response.json().get("stories", [])[:limit]:
            url = (result.get("url") or "").strip()
            if not url:
                continue
            stories.append(
                Story(
                    url=url,
                    outlet=outlet_of(url) or (result.get("media_url") or ""),
                    title=(result.get("title") or "").strip(),
                    published=_day(result.get("publish_date")),
                    raw=without_text(result),
                )
            )
        return stories


def _ids(written: str) -> str:
    return ",".join(part.strip() for part in written.split(",") if part.strip())


def _day(written: Any) -> date | None:
    try:
        return date.fromisoformat(str(written)[:10])
    except ValueError:
        return None


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return None
