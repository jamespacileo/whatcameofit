"""What every registry client shares: the record contract, cache, rate limit,
client identification and retry. Behavior: openspec source-clients.

Every request goes through the one call policy (`work/calls.py`): retried for causes that
pass, within a ceiling on any wait, and refused while the source is paused or its
allowance is used up (`work/pause.py`), whichever command sends it."""

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol, cast

import httpx
from sqlalchemy import CursorResult, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat import __version__
from thenwhat.config import load_call_settings
from thenwhat.db.models import HttpCache
from thenwhat.measure import spans as measure
from thenwhat.sources.terms import SOURCES
from thenwhat.work.calls import CallRules, Calls, NotAnswered, Passing, passes, stated_wait
from thenwhat.work.clock import SystemTime, Time
from thenwhat.work.errors import AllowanceUsedUp as AllowanceSpent
from thenwhat.work.errors import CannotAsk, SourcePaused
from thenwhat.work.pause import apart, let_in, pause, refuse_if_paused

# The clock is the work package's; it is named here too for the source clients.
__all__ = ["SystemTime", "Time"]


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
    "opentargets": "https://platform.opentargets.org/target/{}",
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
    if source_name == "opentargets" and external_id.startswith("CHEMBL"):
        return f"https://platform.opentargets.org/drug/{external_id}"
    template = RECORD_URLS.get(source_name)
    return template.format(external_id) if template else None


class SourceError(Exception):
    """A registry could not be read."""


class MissingContact(SourceError):
    """No contact address is configured, so no request may be sent."""


class SourceUnavailable(SourceError):
    """The registry kept failing after every allowed attempt."""


class SourceCannotBeAsked(SourceUnavailable, CannotAsk):
    """The registry cannot be asked now: it failed on every allowed attempt, it asked for
    a wait above the ceiling, it is paused, or its allowance is used up. Nothing was
    found or not found, and nothing is stored as an answer. A run that meets it stops;
    `until` is when it may be asked again, where that is known."""

    def __init__(self, message: str, *, until: datetime | None = None) -> None:
        super().__init__(message)
        self.until = until


class SourceThrottled(SourceCannotBeAsked):
    """The registry's last answer was "too many requests", after every allowed attempt or
    with a wait above the ceiling. `retry_after` is the wait it stated in seconds, or
    None when it stated none."""

    def __init__(
        self, message: str, retry_after: float | None, *, until: datetime | None = None
    ) -> None:
        super().__init__(message, until=until)
        self.retry_after = retry_after


class UnsearchableTerm(SourceError):
    """The registry cannot search for a term and says why. A source reports this
    after any bounded condition-discovery fallback; treatment names are not simplified."""

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


def forget_expired(session: Session, now: datetime) -> int:
    """Delete the cached answers whose lifetime has passed, and say how many. None of
    them would be used again: a request whose answer has expired is sent afresh, and the
    new answer replaces the old."""
    deleted = cast(
        CursorResult[Any], session.execute(delete(HttpCache).where(HttpCache.expires_at <= now))
    )
    return deleted.rowcount


class Turns(Protocol):
    """Whose turn it is to ask a source."""

    def wait(self, time: Time, interval: float) -> None: ...


class Pacer:
    """Whose turn it is among the clients that hold this one pacer, whatever thread each
    is on. It knows nothing of other processes: a source's clients take turns in the
    source's row of the allowance table unless they are handed a pacer."""

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
    and build their lookups on `_get`, or on `_post` for a source that is asked with a
    request body.

    Every client of a source, in every process, takes turns in the source's row of the
    allowance table: the row holds the time of the latest turn given out, a client takes
    the next free time in a short transaction of its own and waits for it with nothing
    held, so turns are never closer than the interval whichever process takes them. The
    same transaction refuses the request while the source is paused and counts it
    against the source's allowance when one is configured. A client handed a pacer
    takes its turns there instead, and is still refused and counted."""

    name: str
    default_rate_per_second: float
    default_max_attempts: int = 4
    request_timeout: float = 30.0

    def __init__(
        self,
        session: Session,
        *,
        contact_email: str | None,
        transport: httpx.BaseTransport | None = None,
        rate_per_second: float | None = None,
        cache_ttl: timedelta = timedelta(hours=24),
        max_attempts: int | None = None,
        time: Time | None = None,
        pacer: Turns | None = None,
    ) -> None:
        self._session = session
        self._contact = (contact_email or "").strip()
        self._time = time or SystemTime()
        self._interval = 1.0 / (rate_per_second or self.default_rate_per_second)
        self._cache_ttl = cache_ttl
        self._max_attempts = self.default_max_attempts if max_attempts is None else max_attempts
        # Every client of this source, in every process, takes turns with this one,
        # unless it is handed a pacer of its own.
        self._pacer = pacer
        configured = load_call_settings()
        self._allowance = configured.allowances().get(self.name)
        if self._allowance is not None:
            self._interval = max(self._interval, self._allowance.interval_seconds)
        self._calls = Calls(
            self.name,
            rules=CallRules(
                attempts=self._max_attempts,
                wait_ceiling_seconds=configured.call_wait_ceiling_seconds,
                throttled_pause=(
                    timedelta(minutes=self._allowance.pause_minutes)
                    if self._allowance is not None
                    else None
                ),
            ),
            now=self._time.now,
            sleep=self._time.sleep,
            admit=self._wait_for_turn,
            keep_pause=lambda until: pause(self._session, self.name, until, self._time.now()),
        )
        self._client = httpx.Client(
            transport=transport, timeout=self.request_timeout, follow_redirects=True
        )

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
        key = f"{self.name} GET {httpx.URL(url, params=params)}"
        return self._kept(key, lambda: self._request(url, params), force=force, ttl=ttl)

    def _post(
        self,
        url: str,
        body: dict[str, Any],
        *,
        force: bool = False,
        ttl: timedelta | None = None,
    ) -> Fetched | None:
        """The JSON answered to `body` sent to `url` as JSON, or None for not-found.

        The answer is kept under the source, the address and the body together, so two
        bodies sent to one address never share an answer. Everything else is as for
        `_get`: the cache, the pacing, the retries, the client's name and the refusal
        for a source whose terms are not recorded.
        """
        sent = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(sent.encode()).hexdigest()
        key = f"{self.name} POST {httpx.URL(url)} {digest}"
        return self._kept(key, lambda: self._request(url, None, body=body), force=force, ttl=ttl)

    def _kept(
        self,
        key: str,
        ask: Callable[[], httpx.Response | None],
        *,
        force: bool,
        ttl: timedelta | None,
    ) -> Fetched | None:
        """The answer stored under `key` while it is fresh, else what `ask` fetches."""
        require_recorded(self.name)
        cached = self._session.get(HttpCache, key)
        if cached is not None and not force and cached.expires_at > self._time.now():
            return Fetched(cached.payload, cached.fetched_at)

        require_contact(self._contact)
        response = ask()
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

    def _request(
        self, url: str, params: dict[str, str] | None, *, body: dict[str, Any] | None = None
    ) -> httpx.Response | None:
        """One GET, or one POST of `body` as JSON, under the call policy. None means the
        registry said not-found. A registry that cannot be asked raises
        `SourceCannotBeAsked`, never an empty answer."""
        headers = {"User-Agent": user_agent(self._contact)} | self._extra_headers()

        def attempt() -> httpx.Response | None:
            measure.add_request(self.name)
            try:
                if body is None:
                    response = self._client.get(url, params=params, headers=headers)
                else:
                    response = self._client.post(url, json=body, headers=headers)
            except httpx.TransportError as error:
                raise Passing(
                    f"{self.name} could not be reached ({type(error).__name__})."
                ) from error
            self._heed(response)
            if response.status_code == 404:
                return None
            if response.is_success:
                return response
            if passes(response.status_code):
                raise Passing(
                    f"{self.name} answered with status {response.status_code}.",
                    status=response.status_code,
                    wait=stated_wait(response, self._time.now()),
                )
            raise SourceError(
                f"{self.name} refused the request with status {response.status_code}."
            )

        try:
            return self._calls.send(attempt)
        except NotAnswered as stop:
            if stop.last.throttled:
                raise SourceThrottled(str(stop), stop.last.wait, until=stop.until) from None
            raise SourceCannotBeAsked(str(stop), until=stop.until) from None
        except (SourcePaused, AllowanceSpent) as refused:
            raise SourceCannotBeAsked(str(refused), until=refused.until) from None

    def _extra_headers(self) -> dict[str, str]:
        """Headers a source adds to every request, such as its key. They are never part
        of the cache key, which is built from the address alone."""
        return {}

    def _heed(self, response: httpx.Response) -> None:
        """Called with every answer before it is used. A source that states an allowance
        reads it here and raises when nothing is left, which also ends the retries."""

    def _wait_for_turn(self) -> None:
        """Let one request in (work/pause.py) and wait for its turn. Raises, sending
        nothing, while the source is paused or its allowance is used up."""
        began = self._time.monotonic()
        now = self._time.now()
        with apart(self._session) as own:
            turn = let_in(
                own,
                self.name,
                now=now,
                allowance=self._allowance,
                interval=self._interval if self._pacer is None else None,
            )
        wait = (turn - self._time.now()).total_seconds()
        if wait > 0:
            self._time.sleep(wait)
        if self._pacer is not None:
            self._pacer.wait(self._time, self._interval)
        measure.add_wait(self.name, self._time.monotonic() - began)
        if wait > 0 or self._pacer is not None:
            with apart(self._session) as own:
                refuse_if_paused(own, self.name, self._time.now())
