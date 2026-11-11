"""What every registry client shares: the record contract, cache, rate limit,
client identification and retry. Behavior: openspec source-clients."""

import time as system_time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
from sqlalchemy.orm import Session

from thenwhat import __version__
from thenwhat.db.models import HttpCache


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """One record as a registry returned it."""

    source_name: str
    external_id: str
    url: str
    payload: dict[str, Any]
    fetched_at: datetime


class SourceError(Exception):
    """A registry could not be read."""


class MissingContact(SourceError):
    """No contact address is configured, so no request may be sent."""


class SourceUnavailable(SourceError):
    """The registry kept failing after every allowed attempt."""


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


@dataclass(frozen=True, slots=True)
class Fetched:
    payload: dict[str, Any]
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
    ) -> None:
        self._session = session
        self._contact = (contact_email or "").strip()
        self._time = time or SystemTime()
        self._interval = 1.0 / (rate_per_second or self.default_rate_per_second)
        self._cache_ttl = cache_ttl
        self._max_attempts = max_attempts
        self._next_request_at: float | None = None
        self._client = httpx.Client(transport=transport, timeout=30.0, follow_redirects=True)

    def _get(
        self, url: str, params: dict[str, str] | None = None, *, force: bool = False
    ) -> Fetched | None:
        """The JSON at `url`, or None when the registry answers not-found.

        Answers come from the cache while they are fresh, keeping their original
        fetch time, unless `force` is set.
        """
        key = f"{self.name} GET {httpx.URL(url, params=params)}"
        cached = self._session.get(HttpCache, key)
        if cached is not None and not force and cached.expires_at > self._time.now():
            return Fetched(cached.payload, cached.fetched_at)

        if not self._contact:
            raise MissingContact("CONTACT_EMAIL is not set, so no request was sent.")
        response = self._request(url, params)
        if response is None:
            return None

        fetched = Fetched(response.json(), self._time.now())
        entry = cached or HttpCache(request_key=key, source_name=self.name)
        entry.payload = fetched.payload
        entry.fetched_at = fetched.fetched_at
        entry.expires_at = fetched.fetched_at + self._cache_ttl
        self._session.add(entry)
        self._session.flush()
        return fetched

    def _request(self, url: str, params: dict[str, str] | None) -> httpx.Response | None:
        """One GET with bounded retries. None means the registry said not-found."""
        headers = {"User-Agent": f"thenwhat/{__version__} (mailto:{self._contact})"}
        for attempt in range(self._max_attempts):
            self._wait_for_turn()
            stated_delay = 0.0
            try:
                response = self._client.get(url, params=params, headers=headers)
            except httpx.TransportError:
                response = None
            if response is not None:
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

    def _wait_for_turn(self) -> None:
        now = self._time.monotonic()
        if self._next_request_at is not None and now < self._next_request_at:
            self._time.sleep(self._next_request_at - now)
            now = self._time.monotonic()
        self._next_request_at = now + self._interval


def _retry_after(response: httpx.Response) -> float:
    try:
        return float(response.headers.get("Retry-After", "0"))
    except ValueError:  # an HTTP date; fall back to our own backoff
        return 0.0
