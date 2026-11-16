"""The hold on an outlet the page reader has stopped, for everything that asks the reader
for an outlet's pages. Behavior: openspec lead-reading and page-reading.

The reader states a wait with every "not now": seconds for a site it is pacing, hours for
an outlet it has stopped because the outlet refuses it. The time that wait ends is kept
for the outlet where every process and every later run sees it, and until then the outlet
is not asked: by the backfill's read, by `thenwhat statements` or by `thenwhat outlets`.
Whether and when a site is asked stays the reader's decision (ADR 0006): this only keeps
the reader's own answer for as long as the reader said.
"""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.backfill.allowance import Allowances, held_until
from thenwhat.extract.retrieve import (
    NOT_NOW,
    WAIT_MOST,
    ArticleRetriever,
    NotNow,
    PasteNeeded,
    Probe,
    Retrieved,
)

OpenSession = Callable[[], AbstractContextManager[Session]]

# The name an outlet's hold is kept under, before the outlet's own.
OUTLET_HOLD = "reader:"
# The first key of the lock that gives one worker at a time an outlet's turn.
OUTLET_TURN_LOCK = 7_468


class OutletHeld(PasteNeeded):
    """The page reader said the address's outlet cannot be asked before a time that has
    not come, so the reader was not asked."""

    def __init__(self, url: str, outlet: str, until: datetime) -> None:
        self.until = until
        super().__init__(
            f"{url} was not asked for: the page reader said {outlet} cannot be asked before"
            f" {until:%Y-%m-%d %H:%M} UTC. Ask again after that, or supply the article text"
            " instead."
        )


def outlet_of(url: str) -> str | None:
    """The outlet an address belongs to, named as a link lead's outlet is: the host of
    its address in comparison form. None when the address is no page."""
    key = article_key(url)
    return key.split("/", 1)[0].split("?", 1)[0] if key else None


@contextmanager
def asking(session: Session, outlet: str) -> Generator[None]:
    """Hold the outlet's turn, among every worker of every process, while its hold is
    looked at and the page reader is asked. The lock is the connection's and is given
    back as soon as the reader has answered: whatever follows needs no turn."""
    key = func.hashtext(OUTLET_HOLD + outlet)
    session.execute(select(func.pg_advisory_lock(OUTLET_TURN_LOCK, key)))
    try:
        yield
    finally:
        try:
            session.execute(select(func.pg_advisory_unlock(OUTLET_TURN_LOCK, key)))
        except SQLAlchemyError:
            # The turn could not be given back on a transaction that has failed. The
            # connection is closed instead of returned to its pool, which gives it back.
            session.connection().invalidate()
            raise


def keep(allowances: Allowances, outlet: str, now: datetime, wait_seconds: float) -> datetime:
    """Keep that the outlet is not to be asked for this long, in its own short
    transaction. A wait past `WAIT_MOST` is kept as that. Returns when the hold ends."""
    wait = timedelta(seconds=min(max(wait_seconds, 0.0), WAIT_MOST))
    return allowances.hold(OUTLET_HOLD + outlet, now + wait)


@dataclass(frozen=True, slots=True)
class _Turn:
    outlet: str | None
    # When the outlet's hold ends, if one is running: the reader is then not asked.
    held: datetime | None
    stopped: Callable[[float | None], None]


@contextmanager
def _turn(open_session: OpenSession, url: str, now: datetime) -> Generator[_Turn]:
    """The turn of the address's outlet, for a command that reads no lead: taken on a
    session of its own, with what the outlet's hold says and a way to keep a new one."""
    outlet = outlet_of(url)
    if outlet is None:
        yield _Turn(None, None, lambda wait: None)
        return

    def stopped(wait: float | None) -> None:
        if wait:
            keep(Allowances(open_session, {}), outlet, now, wait)

    with open_session() as session, asking(session, outlet):
        yield _Turn(outlet, held_until(session, OUTLET_HOLD + outlet, now), stopped)


def retrieve_unless_held(
    open_session: OpenSession, retriever: ArticleRetriever, url: str, now: datetime
) -> Retrieved:
    """The article from the page reader, as `ArticleRetriever.retrieve` gives it, unless
    its outlet is held: then `OutletHeld` is raised and no request is made. A "not now"
    that states a wait is kept as the outlet's hold before it is raised."""
    with _turn(open_session, url, now) as turn:
        if turn.held is not None and turn.outlet is not None:
            raise OutletHeld(url, turn.outlet, turn.held)
        try:
            return retriever.retrieve(url)
        except NotNow as later:
            turn.stopped(later.retry_after_seconds)
            raise


def probe_unless_held(
    open_session: OpenSession, retriever: ArticleRetriever, url: str, now: datetime
) -> Probe | None:
    """How the reader answered for the address, as `ArticleRetriever.probe` gives it, or
    None when its outlet is held and the reader was not asked. A "not now" that states a
    wait is kept as the outlet's hold."""
    with _turn(open_session, url, now) as turn:
        if turn.held is not None:
            return None
        probe = retriever.probe(url)
        if probe.answer == NOT_NOW:
            turn.stopped(probe.retry_after_seconds)
        return probe
