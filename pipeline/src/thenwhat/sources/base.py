"""What every registry client shares: the record contract, cache, rate limit,
client identification and retry. Behavior: openspec source-clients."""

import threading
import time as system_time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat import __version__
from thenwhat.db.models import HttpCache
from thenwhat.sources.terms import SOURCES


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """One record as a registry returned it."""

    source_name: str
    external_id: str
    url: str
    payload: dict[str, Any]
    fetched_at: datetime


# Where a reader can open a record, by registry name.
RECORD_URLS = {
    "clinicaltrials.gov": "https://clinicaltrials.gov/study/{}",
    "crossref": "https://doi.org/{}",
    "ror": "https://ror.org/{}",
    "mesh": "https://id.nlm.nih.gov/mesh/{}",
}


def record_url(source_name: str, external_id: str) -> str | None:
    """Where a reader can open the record a match points to, if the registry has a page
    for it. A paper found by a literature search is known by its DOI when it has one,
    else by the search source's own identifier."""
    if source_name == "openalex":
        template = (
            "https://doi.org/{}" if external_id.startswith("10.") else "https://openalex.org/{}"
        )
        return template.format(external_id)
    template = RECORD_URLS.get(source_name)
    return template.format(external_id) if template else None


class SourceError(Exception):
    """A registry could not be read."""


class MissingContact(SourceError):
    """No contact address is configured, so no request may be sent."""


class SourceUnavailable(SourceError):
    """The registry kept failing after every allowed attempt."""


class UnsearchableTerm(SourceError):
    """The registry cannot search for a term as written, and says why. The term is
    reported for someone to reword. It is never searched for in a simpler form."""

    def __init__(self, term: str, reason: str, source_name: str) -> None:
        super().__init__(f"{source_name} cannot search for '{term}': {reason}")
        self.term = term
        self.reason = reason


class MissingKey(SourceError):
    """The source needs a key and none is configured, so no request may be sent."""


class AllowanceUsedUp(SourceError):
    """The source's free allowance cannot be drawn on: it is used up for the day, or the
    source did not say what is left, or asking again would spend paid credit. The source
    is not asked again until the allowance resets."""


class TermsNotRecorded(SourceError):
    """The source is not in the list of sources, so no request may be sent."""


def require_recorded(source_name: str) -> None:
    """Refuse to ask a source whose terms, licence and date read are not recorded."""
    if source_name not in SOURCES:
        raise TermsNotRecorded(
            f"The terms of '{source_name}' are not recorded in the list of sources, so no"
            " request was sent. Read them, add an entry to docs/sources.md and to the list"
            " in sources/terms.py, then run this again."
        )


# The name this client goes by, in its User-Agent and when reading a site's robots.txt.
CLIENT_NAME = "thenwhat"


def user_agent(contact: str) -> str:
    return f"{CLIENT_NAME}/{__version__} (mailto:{contact})"


def require_contact(contact: str) -> None:
    """Refuse to send a request when no contact address is configured."""
    if not contact:
        raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")


class Time(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemTime:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return system_time.monotonic()

    def sleep(self, seconds: float) -> None:
        system_time.sleep(seconds)


class Pacer:
    """Whose turn it is to ask a registry. One pacer shared by several clients of the same
    registry keeps them, together, to that registry's rate, whatever thread each is on."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_request_at: float | None = None

    def wait(self, time: Time, interval: float) -> None:
        with self._lock:
            now = time.monotonic()
            if self._next_request_at is not None and now < self._next_request_at:
                time.sleep(self._next_request_at - now)
                now = time.monotonic()
            self._next_request_at = now + interval


@dataclass(frozen=True, slots=True)
class Fetched:
    # What the source answered: an object, or a list from a source that answers one.
    payload: Any
    fetched_at: datetime


class Source:
    """Base for registry clients. Subclasses set `name` and `default_rate_per_second`
    and build their lookups on `_get`."""

    name: str
    default_rate_per_second: float

    def __init__(
        self,
        session: Session,
        *,
        contact_email: str | None,
        transport: httpx.BaseTransport | None = None,
        rate_per_second: float | None = None,
        cache_ttl: timedelta = timedelta(hours=24),
        max_attempts: int = 4,
        time: Time | None = None,
        pacer: Pacer | None = None,
    ) -> None:
        self._session = session
        self._contact = (contact_email or "").strip()
        self._time = time or SystemTime()
        self._interval = 1.0 / (rate_per_second or self.default_rate_per_second)
        self._cache_ttl = cache_ttl
        self._max_attempts = max_attempts
        # Its own pacer unless one is shared with other clients of the same registry.
        self._pacer = pacer or Pacer()
        self._client = httpx.Client(transport=transport, timeout=30.0, follow_redirects=True)

    def _get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        *,
        force: bool = False,
        ttl: timedelta | None = None,
    ) -> Fetched | None:
        """The JSON at `url`, or None when the registry answers not-found.

        Answers come from the cache while they are fresh, keeping their original
        fetch time, unless `force` is set. `ttl` keeps this answer for longer or
        shorter than the client's usual time.
        """
        require_recorded(self.name)
        key = f"{self.name} GET {httpx.URL(url, params=params)}"
        cached = self._session.get(HttpCache, key)
        if cached is not None and not force and cached.expires_at > self._time.now():
            return Fetched(cached.payload, cached.fetched_at)

        require_contact(self._contact)
        response = self._request(url, params)
        if response is None:
            return None

        fetched = Fetched(response.json(), self._time.now())
        kept = {
            "source_name": self.name,
            "payload": fetched.payload,
            "fetched_at": fetched.fetched_at,
            "expires_at": fetched.fetched_at + (ttl or self._cache_ttl),
        }
        # Written in one statement that also replaces an entry another session wrote in
        # the meantime, so two lookups at once cannot collide on the same request.
        self._session.execute(
            insert(HttpCache)
            .values(request_key=key, **kept)
            .on_conflict_do_update(index_elements=[HttpCache.request_key], set_=kept)
        )
        if cached is not None:
            self._session.refresh(cached)
        return fetched

    def _request(self, url: str, params: dict[str, str] | None) -> httpx.Response | None:
        """One GET with bounded retries. None means the registry said not-found."""
        headers = {"User-Agent": user_agent(self._contact)} | self._extra_headers()
        for attempt in range(self._max_attempts):
            self._wait_for_turn()
            stated_delay = 0.0
            try:
                response = self._client.get(url, params=params, headers=headers)
            except httpx.TransportError:
                response = None
            if response is not None:
                self._heed(response)
                if response.status_code == 404:
                    return None
                if response.is_success:
                    return response
                if response.status_code != 429 and response.status_code < 500:
                    raise SourceError(
                        f"{self.name} refused the request with status {response.status_code}."
                    )
                stated_delay = _retry_after(response)
            if attempt + 1 < self._max_attempts:
                self._time.sleep(max(2.0**attempt, stated_delay))
        raise SourceUnavailable(f"{self.name} did not answer after {self._max_attempts} attempts.")

    def _extra_headers(self) -> dict[str, str]:
        """Headers a source adds to every request, such as its key. They are never part
        of the cache key, which is built from the address alone."""
        return {}

    def _heed(self, response: httpx.Response) -> None:
        """Called with every answer before it is used. A source that states an allowance
        reads it here and raises when nothing is left, which also ends the retries."""

    def _wait_for_turn(self) -> None:
        self._pacer.wait(self._time, self._interval)


def _retry_after(response: httpx.Response) -> float:
    try:
        return float(response.headers.get("Retry-After", "0"))
    except ValueError:  # an HTTP date; fall back to our own backoff
        return 0.0
