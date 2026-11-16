"""One shared allowance of requests per source, for every process that asks it.
Behavior: openspec source-allowances."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import AllowanceUsedUp, NoAllowance, SourcePaused
from thenwhat.config import SourceAllowance
from thenwhat.db.models import SourceAllowanceUse
from thenwhat.sources.base import SystemTime, Time

OpenSession = Callable[[], AbstractContextManager[Session]]


@dataclass(frozen=True, slots=True)
class AllowanceStatus:
    allowed: int
    used: int
    period_ends: datetime | None
    paused_until: datetime | None

    @property
    def left(self) -> int:
        return max(self.allowed - self.used, 0)


class Allowances:
    """Claims requests against each source's allowance.

    A claim is its own short transaction, separate from the record being processed: the
    count is visible to other processes at once and stays counted when the record fails.
    The source's row is locked while a claim waits out the least interval, which is what
    keeps requests from different processes apart.
    """

    def __init__(
        self,
        open_session: OpenSession,
        configured: dict[str, SourceAllowance],
        time: Time | None = None,
    ) -> None:
        self._open_session = open_session
        self._configured = configured
        self._time = time or SystemTime()

    def of(self, source: str) -> SourceAllowance:
        if source not in self._configured:
            raise NoAllowance(
                f"No allowance is configured for '{source}'. "
                "Add it to SOURCE_ALLOWANCES before running a step that asks it."
            )
        return self._configured[source]

    def claim(self, source: str) -> None:
        """Take one request from the source's allowance, waiting for its turn. Raises
        when the allowance is spent or the source is paused; nothing is counted then."""
        allowance = self.of(source)
        period = timedelta(hours=allowance.period_hours)
        with self._open_session() as session:
            use = self._locked(session, source)
            now = self._time.now()
            if now >= use.period_start + period:
                use.period_start = now
                use.requests_used = 0
            if use.paused_until is not None and now < use.paused_until:
                raise SourcePaused(
                    f"{source} said it was asked too often. "
                    f"It is not asked again before {_when(use.paused_until)}."
                )
            if use.requests_used >= allowance.requests:
                raise AllowanceUsedUp(
                    f"The allowance for {source} ({allowance.requests} requests) is used up. "
                    f"It is restored at {_when(use.period_start + period)}."
                )
            if use.last_request_at is not None:
                wait = allowance.interval_seconds - (now - use.last_request_at).total_seconds()
                if wait > 0:
                    self._time.sleep(wait)
                    now = self._time.now()
            use.requests_used += 1
            use.last_request_at = now
            session.flush()

    def refused(self, source: str, retry_after_seconds: float | None = None) -> SourcePaused:
        """Record that the source answered "too many requests". Returns the error to
        raise: the run stops asking this source until the pause has passed."""
        allowance = self.of(source)
        pause = timedelta(seconds=retry_after_seconds or allowance.pause_minutes * 60)
        with self._open_session() as session:
            use = self._locked(session, source)
            until = self._time.now() + pause
            use.paused_until = until
            use.refusals += 1
            session.flush()
        return SourcePaused(
            f"{source} said it was asked too often. It is not asked again before {_when(until)}."
        )

    def hold(self, name: str, until: datetime) -> datetime:
        """Record that `name` is not to be asked before `until`, for every process and
        every later run: an outlet the page reader has stopped. The name needs no
        allowance of its own; only the time is kept, beside the sources' pauses. A hold
        already kept that ends later stands. Returns when the hold ends."""
        with self._open_session() as session:
            use = self._locked(session, name)
            kept = use.paused_until
            if kept is None or kept < until:
                use.paused_until = kept = until
                use.refusals += 1
            session.flush()
            return kept

    def status(self, session: Session, source: str) -> AllowanceStatus:
        allowance = self.of(source)
        use = session.get(SourceAllowanceUse, source)
        now = self._time.now()
        period = timedelta(hours=allowance.period_hours)
        if use is None or now >= use.period_start + period:
            paused = (
                use.paused_until if use and use.paused_until and use.paused_until > now else None
            )
            return AllowanceStatus(allowance.requests, 0, None, paused)
        paused = use.paused_until if use.paused_until and use.paused_until > now else None
        return AllowanceStatus(
            allowance.requests, use.requests_used, use.period_start + period, paused
        )

    def _locked(self, session: Session, source: str) -> SourceAllowanceUse:
        session.execute(
            insert(SourceAllowanceUse)
            .values(source_name=source, period_start=self._time.now(), requests_used=0)
            .on_conflict_do_nothing(index_elements=[SourceAllowanceUse.source_name])
        )
        return session.scalars(
            select(SourceAllowanceUse)
            .where(SourceAllowanceUse.source_name == source)
            .with_for_update()
        ).one()


def held_until(session: Session, name: str, now: datetime) -> datetime | None:
    """When the hold kept under `name` ends, or None when none is running."""
    until = session.scalar(
        select(SourceAllowanceUse.paused_until).where(SourceAllowanceUse.source_name == name)
    )
    return until if until is not None and until > now else None


def holds_under(session: Session, prefix: str, now: datetime) -> dict[str, datetime]:
    """Every running hold whose name begins with `prefix`, by the rest of its name."""
    rows = session.execute(
        select(SourceAllowanceUse.source_name, SourceAllowanceUse.paused_until).where(
            SourceAllowanceUse.source_name.startswith(prefix, autoescape=True),
            SourceAllowanceUse.paused_until > now,
        )
    )
    return {name[len(prefix) :]: until for name, until in rows if until is not None}


def _when(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M UTC")
