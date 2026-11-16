"""Getting the text of a news article through the page reader. Behavior: openspec
page-reading and claim-extraction.

Every news page is fetched by the page reader, the operator's self-hosted Firecrawl
service, and in no other way. The reader holds the rules about each site: whether an
address may be fetched, how often a site is asked and where a copy comes from. This
module asks it for one page and turns its answer into one of four outcomes.

The text is returned to the caller and kept nowhere: not cached, not logged.
"""

import math
import threading
import time as system_time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from thenwhat.backfill.errors import ReaderUnavailable
from thenwhat.extract.page import BODY_FROM, Page, read_page
from thenwhat.measure import spans as measure
from thenwhat.sources.base import require_contact, user_agent

# The name the read step's allowance is kept under.
READER = "reader"
SCRAPE = "/v2/scrape"
# What the pipeline asks the reader for: the page as drawn and its main content, and
# nothing kept. Never a summary, structured extraction or image descriptions: every
# model call on an article is the pipeline's own.
FORMATS = ("rawHtml", "html")
# The answers the service is asked to give when it will not read a page now or at all
# (design.md of the change firecrawl-page-reader, decision 2).
NOT_ALLOWED_CODE = "NOT_ALLOWED"
NOT_NOW_CODE = "NOT_NOW"
# How an address answered, for the record of which outlets can be read.
READ = "read"
NOT_ALLOWED = "not_allowed"
NOT_NOW = "not_now"
NOT_SERVED = "not_served"


# The name the page reader goes by in allowances and in measurements.
READER_SOURCE = "reader"


class PasteNeeded(Exception):
    """The article cannot be fetched; the operator must supply its text."""


class ThinPage(PasteNeeded):
    """The reader returned too little main content to read as an article."""


class NotAllowed(PasteNeeded):
    """The reader answered that the address is not allowed. It is not asked for again."""

    def __init__(self, url: str, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f"The page reader does not allow {url}: {reason}. Supply the article text instead."
        )


class NotNow(PasteNeeded):
    """The reader answered that the site cannot be asked now."""

    def __init__(self, url: str, reason: str, retry_after_seconds: float | None) -> None:
        self.reason = reason
        self.retry_after_seconds = retry_after_seconds
        when = (
            f"in {round(retry_after_seconds):,} seconds"
            if retry_after_seconds is not None
            else "later"
        )
        super().__init__(
            f"The page reader cannot ask for {url} now: {reason}. It may be asked again {when},"
            " or supply the article text instead."
        )


class NotServed(PasteNeeded):
    """The reader asked the site, and the site did not serve the page."""

    def __init__(self, url: str, status: int) -> None:
        self.status = status
        super().__init__(
            f"{url} could not be retrieved: the site answered {status}."
            " Supply the article text instead."
        )


@dataclass(frozen=True, slots=True)
class Retrieved:
    text: str
    archive_url: str | None = None
    # The same page with what it says about itself: headline, date, the papers it links to.
    page: Page | None = None


@dataclass(frozen=True, slots=True)
class Probe:
    """How one article address answered, for the record of which outlets can be read."""

    # READ, NOT_ALLOWED, NOT_NOW or NOT_SERVED.
    answer: str
    # The site's HTTP status, as the reader reports it.
    status: int | None = None
    page: Page | None = None
    # With NOT_NOW: the wait the reader stated. Not part of how the address answered.
    retry_after_seconds: float | None = field(default=None, compare=False)


# The reader answers 429 with a Retry-After when it is at capacity, which is not a
# failure: it is asked again after the wait it states, this many times in all, and
# only for a wait this short. Anything longer or unstated ends the run as before.
BUSY_TRIES = 5
BUSY_WAIT_MOST = 120.0

# The longest wait a "not now" is taken to state. The reader documents waits of at most
# six hours; anything past a day is a unit mistaken or a sentinel, and is read as a day,
# so no outlet is left for weeks and no time is computed that cannot be.
WAIT_MOST = 24 * 60 * 60.0

_turns: dict[int, threading.BoundedSemaphore] = {}
_turns_lock = threading.Lock()


def reader_turns(at_once: int) -> threading.BoundedSemaphore:
    """One set of turns per process for each size, so every retriever made in it shares
    the cap on requests in flight with the reader."""
    with _turns_lock:
        return _turns.setdefault(at_once, threading.BoundedSemaphore(at_once))


class ArticleRetriever:
    def __init__(
        self,
        *,
        reader_url: str,
        reader_key: str,
        contact_email: str | None,
        turns: threading.BoundedSemaphore,
        timeout_seconds: float = 120,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = system_time.sleep,
    ) -> None:
        self._scrape = reader_url.rstrip("/") + SCRAPE
        self._key = reader_key
        self._turns = turns
        self._sleep = sleep
        self._contact = (contact_email or "").strip()
        self._reader = httpx.Client(transport=transport, timeout=timeout_seconds)
        # Only for the platforms' own interfaces that `json` asks, until posts are read
        # through the reader too.
        self._client = httpx.Client(transport=transport, timeout=30.0, follow_redirects=True)

    def retrieve(self, url: str) -> Retrieved:
        """The article as plain text, from the page reader. Raises NotAllowed, NotNow or
        NotServed when the reader gives no page, and ReaderUnavailable when the reader
        itself could not be asked."""
        data = self._ask(url)
        if data.answer != READ:
            raise _refusal(url, data)
        page = data.page
        assert page is not None
        if len(page.text) < BODY_FROM:
            raise ThinPage(
                f"{url} returned too little article text. Supply the article text instead."
            )
        return Retrieved(page.text, archive_url=data.archive_url, page=page)

    def probe(self, url: str) -> Probe:
        """Ask the reader for one article and say how it answered. Raises
        ReaderUnavailable when the reader itself could not be asked: that is not the
        outlet's answer."""
        data = self._ask(url)
        return Probe(data.answer, data.status, data.page, data.retry_after_seconds)

    def json(self, url: str) -> Any:
        """The JSON a platform's own interface for software serves at this address, or
        None when it does not answer with any."""
        require_contact(self._contact)
        headers = {"User-Agent": user_agent(self._contact)}
        try:
            response = self._client.get(url, headers=headers)
        except httpx.TransportError:
            return None
        if response.status_code != 200:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def _ask(self, url: str) -> "_Answer":
        body = {
            "url": url,
            "formats": list(FORMATS),
            "maxAge": 0,
            "storeInCache": False,
        }
        headers = {"Authorization": f"Bearer {self._key}"}
        for attempt in range(BUSY_TRIES):
            began = system_time.monotonic()
            with self._turns:
                # Time spent waiting for one of the reader's turns is waiting, not reading.
                measure.add_wait(READER_SOURCE, system_time.monotonic() - began)
                measure.add_request(READER_SOURCE)
                try:
                    response = self._reader.post(self._scrape, json=body, headers=headers)
                except httpx.TimeoutException:
                    raise ReaderUnavailable(
                        "The page reader did not answer in time. Nothing was recorded against"
                        " the site; try again when the reader is running."
                    ) from None
                except httpx.TransportError:
                    raise ReaderUnavailable(
                        "The page reader could not be reached. Nothing was recorded against"
                        " the site; try again when the reader is running."
                    ) from None
            wait = _busy_for(response)
            if wait is None or attempt + 1 == BUSY_TRIES:
                break
            # The reader is at capacity and says when to ask again. The turn is given
            # back first, so the wait holds no other request up.
            measure.add_wait(READER_SOURCE, wait)
            self._sleep(wait)
        return _answer_of(response)


def _busy_for(response: httpx.Response) -> float | None:
    """How long the reader asks to be left alone when it answers that it is at capacity:
    a 429 that states a wait of no more than `BUSY_WAIT_MOST` seconds. None for any
    other answer, a 429 with no stated wait among them, which is still the reader
    failing."""
    if response.status_code != 429:
        return None
    try:
        answered = response.json()
    except ValueError:
        answered = None
    if isinstance(answered, dict) and answered.get("code") in (NOT_NOW_CODE, NOT_ALLOWED_CODE):
        # That is the reader's answer about the site, not about itself.
        return None
    try:
        wait = float(response.headers.get("Retry-After", ""))
    except ValueError:
        return None
    if not math.isfinite(wait) or wait < 0 or wait > BUSY_WAIT_MOST:
        return None
    return wait


@dataclass(frozen=True, slots=True)
class _Answer:
    answer: str
    status: int | None = None
    page: Page | None = None
    archive_url: str | None = None
    reason: str = ""
    retry_after_seconds: float | None = None


def _answer_of(response: httpx.Response) -> _Answer:
    """The reader's answer as one of the four outcomes. Anything else is the reader
    failing, never the site. A refusal is known by its code, whatever HTTP status it
    comes with."""
    try:
        answered = response.json()
    except ValueError:
        answered = None
    # A refusal carried on a 429 is still the reader's answer about the site, however
    # long the wait it states: an outlet the reader has stopped for hours is not the
    # reader being overloaded.
    if isinstance(answered, dict) and answered.get("success") is not True:
        code = answered.get("code")
        reason = answered.get("reason")
        if code == NOT_ALLOWED_CODE and isinstance(reason, str) and reason.strip():
            return _Answer(NOT_ALLOWED, reason=reason.strip())
        if code == NOT_NOW_CODE and isinstance(reason, str) and reason.strip():
            retry = answered.get("retryAfter")
            if (
                isinstance(retry, int | float)
                and not isinstance(retry, bool)
                and math.isfinite(retry)
                and retry >= 0
            ):
                return _Answer(
                    NOT_NOW,
                    reason=reason.strip(),
                    retry_after_seconds=min(float(retry), WAIT_MOST),
                )
            raise _unknown(response)
    if response.status_code in (401, 403):
        raise ReaderUnavailable(
            f"The page reader refused the pipeline's key ({response.status_code})."
            " Check FIRECRAWL_API_KEY."
        )
    if response.status_code == 429 or response.status_code >= 500:
        raise ReaderUnavailable(
            f"The page reader is overloaded or failing ({response.status_code})."
            " Nothing was recorded against the site; try again later."
        )
    if not isinstance(answered, dict) or response.status_code != 200:
        raise _unknown(response)
    data = answered.get("data")
    if answered.get("success") is not True or not isinstance(data, dict):
        raise _unknown(response)
    metadata = data.get("metadata")
    status = metadata.get("statusCode") if isinstance(metadata, dict) else None
    if not isinstance(status, int) or isinstance(status, bool):
        raise _unknown(response)
    if status != 200:
        return _Answer(NOT_SERVED, status=status)
    drawn, main = data.get("rawHtml"), data.get("html")
    if not isinstance(drawn, str) or not isinstance(main, str):
        raise _unknown(response)
    archive = metadata.get("archiveUrl") if isinstance(metadata, dict) else None
    return _Answer(
        READ,
        status=status,
        page=read_page(drawn, main),
        archive_url=archive if isinstance(archive, str) and archive else None,
    )


def _unknown(response: httpx.Response) -> ReaderUnavailable:
    # The answer's body is not quoted: it may carry the page's text.
    return ReaderUnavailable(
        f"The page reader answered in a form the pipeline does not know ({response.status_code})."
        " Nothing was recorded against the site."
    )


def _refusal(url: str, data: _Answer) -> PasteNeeded:
    if data.answer == NOT_ALLOWED:
        return NotAllowed(url, data.reason)
    if data.answer == NOT_NOW:
        return NotNow(url, data.reason, data.retry_after_seconds)
    return NotServed(url, data.status or 0)
