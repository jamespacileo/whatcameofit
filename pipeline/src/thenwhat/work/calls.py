"""How every call to a source or a model is tried again, waited for and given up on.
Behavior: openspec source-clients ("A stated wait is honoured in either form and
bounded", "Try later is told apart from not found") and decision-steps ("A model call is
retried within bounds"); design decision 7 of change one-work-runner.

One policy for every source client and both model backends. The page reader keeps its
own rules (docs/adr/0006): nothing here retries around it.

An attempt that fails for a cause that passes, a broken connection, a timeout, too many
requests or a server error, says so by raising `Passing`, and is made again a bounded
number of times. Each delay is longer than the one before, with a little jitter, and
never shorter than a wait the provider stated, whether it stated seconds or a time. No
one wait is longer than the ceiling. A provider that asks for longer, or that still fails
when the attempts run out, cannot be asked: the caller is told so with `NotAnswered`,
and until when where that is known, and that time is kept as the provider's pause for
every process. Anything else an attempt raises, a refusal, a not-found, an invalid
result, passes straight through and is never tried again here.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx
from tenacity import AsyncRetrying, RetryCallState, RetryError, Retrying, retry_if_exception_type

from thenwhat.measure import spans as measure
from thenwhat.work.clock import when
from thenwhat.work.errors import CannotAsk

TOO_MANY_REQUESTS = 429
# Besides every server error: the request timed out, or too many were sent.
PASSING_STATUSES = frozenset({408, TOO_MANY_REQUESTS})
# What a measurement names a delay before another attempt: this, then the provider.
RETRY = "retry:"


def passes(status: int) -> bool:
    """Whether an answer with this status may be different if the request is sent again."""
    return status in PASSING_STATUSES or status >= 500


def stated_wait(response: httpx.Response, now: datetime) -> float | None:
    """The wait the answer's Retry-After states, in seconds, whether it is given as a
    number of seconds or as a time. None when it states none, or none this can read."""
    value = (response.headers.get("Retry-After") or "").strip()
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        pass
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max((moment - now).total_seconds(), 0.0)


class Passing(Exception):
    """One attempt failed for a cause that passes, and may be made again. `status` is the
    answer's status when there was an answer; `wait` is the wait it stated, in seconds."""

    def __init__(self, detail: str, *, status: int | None = None, wait: float | None = None):
        super().__init__(detail)
        self.status = status
        self.wait = wait

    @property
    def throttled(self) -> bool:
        return self.status == TOO_MANY_REQUESTS


class NotAnswered(CannotAsk):
    """A provider could not be asked: its attempts ran out on causes that pass, or it
    asked for a wait above the ceiling. `last` is the last attempt's failure."""

    def __init__(
        self, message: str, *, until: datetime | None, last: Passing, attempts: int
    ) -> None:
        super().__init__(message, until=until)
        self.last = last
        self.attempts = attempts


@dataclass(frozen=True, slots=True)
class CallRules:
    # How many times one call is attempted in all.
    attempts: int = 4
    # The longest any one wait may be, in seconds (CALL_WAIT_CEILING_SECONDS).
    wait_ceiling_seconds: float = 60.0
    # The delay before the second attempt; each later one is twice the one before.
    first_delay_seconds: float = 1.0
    # How long a provider that kept answering "too many requests", without saying how
    # long to wait, is not asked. None leaves it unpaused: the next call asks it again.
    throttled_pause: timedelta | None = None


def some_jitter(delay: float) -> float:
    """Up to a quarter of the delay more, so callers that failed together do not all
    come back together."""
    return random.uniform(0, delay / 4)


def no_jitter(delay: float) -> float:
    return 0.0


# A pause kept for every process: given the name and the time, it returns the time kept,
# which is later when a longer pause was already kept.
KeepPause = Callable[[datetime], datetime]


class Calls:
    """Calls to one provider, `name`, under one policy.

    `admit` runs before every attempt and may raise to send nothing, as for a paused
    source. `keep_pause` keeps the time a provider that cannot be asked may be asked
    again, for every process."""

    def __init__(
        self,
        name: str,
        *,
        rules: CallRules,
        now: Callable[[], datetime],
        sleep: Callable[[float], None],
        jitter: Callable[[float], float] = some_jitter,
        admit: Callable[[], None] | None = None,
        keep_pause: KeepPause | None = None,
    ) -> None:
        self.name = name
        self._rules = rules
        self._now = now
        self._sleep = sleep
        self._jitter = jitter
        self._admit = admit
        self._keep_pause = keep_pause

    def send[T](self, attempt: Callable[[], T]) -> T:
        """What `attempt` returns, once one attempt succeeds."""

        def admitted() -> T:
            if self._admit is not None:
                self._admit()
            return attempt()

        retrying = Retrying(
            retry=retry_if_exception_type(Passing),
            stop=self._stop,
            wait=self._delay,
            sleep=self._wait,
        )
        try:
            return retrying(admitted)
        except RetryError as spent:
            raise self.kept(self._cannot_ask(spent)) from None

    async def send_async[T](self, attempt: Callable[[], Awaitable[T]]) -> T:
        """As `send`, for an attempt that is awaited. Nothing is admitted before it: the
        caller checks once, before the calls it makes at once. Delays are slept on a
        thread, so the other calls go on meanwhile."""

        async def wait(seconds: float) -> None:
            await asyncio.to_thread(self._wait, seconds)

        retrying = AsyncRetrying(
            retry=retry_if_exception_type(Passing),
            stop=self._stop,
            wait=self._delay,
            sleep=wait,
        )
        try:
            return await retrying(attempt)
        except RetryError as spent:
            raise self._cannot_ask(spent) from None

    def kept(self, failure: NotAnswered) -> NotAnswered:
        """The failure, with its time kept as the provider's pause for every process, and
        the time it says the one kept, which is later when a longer pause stood. `send`
        keeps it itself; a caller of `send_async` does once its calls at once are over."""
        if failure.until is None or self._keep_pause is None:
            return failure
        return self._told(failure.last, failure.attempts, self._keep_pause(failure.until))

    def _stop(self, state: RetryCallState) -> bool:
        return state.attempt_number >= self._rules.attempts or self._too_long(_failure(state))

    def _delay(self, state: RetryCallState) -> float:
        failure = _failure(state)
        grown = self._rules.first_delay_seconds * 2 ** (state.attempt_number - 1)
        delay = grown + self._jitter(grown)
        if failure.wait is not None:
            delay = max(delay, failure.wait)
        return min(delay, self._rules.wait_ceiling_seconds)

    def _wait(self, seconds: float) -> None:
        self._sleep(seconds)
        measure.add_wait(f"{RETRY}{self.name}", seconds)

    def _too_long(self, failure: Passing) -> bool:
        return failure.wait is not None and failure.wait > self._rules.wait_ceiling_seconds

    def _cannot_ask(self, spent: RetryError) -> NotAnswered:
        """What the caller is told when the attempts ran out or the wait asked for is too
        long: until when the provider cannot be asked, where it said or where a provider
        that kept saying "too many requests" is given a pause of a set length."""
        last = spent.last_attempt.exception()
        assert isinstance(last, Passing)
        now = self._now()
        until: datetime | None = None
        if last.wait is not None:
            until = now + timedelta(seconds=last.wait)
        elif last.throttled and self._rules.throttled_pause is not None:
            until = now + self._rules.throttled_pause
        return self._told(last, spent.last_attempt.attempt_number, until)

    def _told(self, last: Passing, attempts: int, until: datetime | None) -> NotAnswered:
        if self._too_long(last):
            said = "said it was asked too often" if last.throttled else "said it cannot answer now"
            message = (
                f"{self.name} {said}. It asked for a wait of {last.wait:.0f} seconds, longer "
                f"than the {self._rules.wait_ceiling_seconds:g} seconds a call waits."
            )
        elif last.throttled:
            message = f"{self.name} said it was asked too often, {attempts} times running."
        else:
            message = f"{self.name} did not answer after {attempts} attempts."
        if until is not None:
            message += f" It is not asked again before {when(until)}."
        return NotAnswered(message, until=until, last=last, attempts=attempts)


def _failure(state: RetryCallState) -> Passing:
    assert state.outcome is not None
    failure = state.outcome.exception()
    assert isinstance(failure, Passing)
    return failure
