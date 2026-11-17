"""When a source or a model may next be asked, and whether a request may go to it now,
for every process and every later run. Behavior: openspec source-clients ("A pause is
seen by every process", "Every command's requests count against the source's
allowance").

Both are kept in the name's row of `source_allowance_use`. A pause is written in a short
transaction of its own, apart from the work in hand, so other processes see it at once
and it stands when that work is undone. Every request a source client sends, whichever
command sends it, is let in here first: refused while the source is paused, counted
against the source's allowance when one is configured, and given its turn. A source with
no configured allowance is not counted, only given its turn.
"""

import math
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.config import SourceAllowance
from thenwhat.db.models import SourceAllowanceUse
from thenwhat.work.clock import when
from thenwhat.work.errors import AllowanceUsedUp, SourcePaused


@contextmanager
def apart(session: Session) -> Generator[Session]:
    """A short transaction of its own beside the caller's, ended when the block ends.
    On a session bound to one connection, as in the tests, it is a savepoint of that
    connection."""
    with (
        Session(session.get_bind(), join_transaction_mode="create_savepoint") as own,
        own.begin(),
    ):
        yield own


def locked(session: Session, name: str, now: datetime) -> SourceAllowanceUse:
    """The name's row, made if it has none, held until the caller's transaction ends."""
    session.execute(
        insert(SourceAllowanceUse)
        .values(source_name=name, period_start=now, requests_used=0)
        .on_conflict_do_nothing(index_elements=[SourceAllowanceUse.source_name])
    )
    return session.scalars(
        select(SourceAllowanceUse).where(SourceAllowanceUse.source_name == name).with_for_update()
    ).one()


def paused_until(session: Session, name: str, now: datetime) -> datetime | None:
    """When the pause kept under `name` ends, or None when none is running."""
    until = session.scalar(
        select(SourceAllowanceUse.paused_until).where(SourceAllowanceUse.source_name == name)
    )
    return until if until is not None and until > now else None


def paused(name: str, until: datetime) -> SourcePaused:
    """What a caller is told of a source that is paused: nothing was sent to it."""
    return SourcePaused(
        f"{name} is paused until {when(until)}: it said it could not be asked before then. "
        "Nothing was sent to it.",
        until=until,
    )


def refuse_if_paused(session: Session, name: str, now: datetime) -> None:
    """Raise, sending nothing, while `name` is paused."""
    until = paused_until(session, name, now)
    if until is not None:
        raise paused(name, until)


def keep(session: Session, name: str, until: datetime, now: datetime) -> datetime:
    """Record, in the caller's transaction, that `name` is not asked before `until`. A
    pause already kept that ends later stands. Returns when the pause ends."""
    use = locked(session, name, now)
    kept = use.paused_until
    if kept is None or kept < until:
        use.paused_until = kept = until
        use.refusals += 1
    session.flush()
    return kept


def pause(session: Session, name: str, until: datetime, now: datetime) -> datetime:
    """Record that `name` is not asked before `until`, for every process and every later
    run, in a short transaction of its own. Returns when the pause ends."""
    with apart(session) as own:
        return keep(own, name, until, now)


def let_in(
    session: Session,
    name: str,
    *,
    now: datetime,
    allowance: SourceAllowance | None,
    interval: float | None,
) -> datetime:
    """Let one request to `name` go, in the caller's transaction, and say when it may be
    sent: refused while the source is paused, counted against its allowance when one is
    configured, and given the turn `interval` seconds after the one before when an
    interval is given. Raises, counting nothing, when the request may not be sent."""
    use = locked(session, name, now)
    if use.paused_until is not None and now < use.paused_until:
        raise paused(name, use.paused_until)
    if allowance is not None:
        period = timedelta(hours=allowance.period_hours)
        if now >= use.period_start + period:
            use.period_start = now
            use.requests_used = 0
        if use.requests_used >= allowance.requests:
            restored = use.period_start + period
            raise AllowanceUsedUp(
                f"The allowance for {name} ({allowance.requests} requests) is used up. "
                f"It is restored at {when(restored)}.",
                until=restored,
            )
        use.requests_used += 1
    turn = now
    if interval is not None and use.last_request_at is not None:
        # Rounded up to the clock's own step, so a turn is never early.
        turn = max(turn, use.last_request_at + timedelta(microseconds=math.ceil(interval * 1e6)))
    use.last_request_at = turn
    session.flush()
    return turn
