"""Forgetting cached answers that are past their lifetime."""

from datetime import UTC, datetime

from thenwhat.cli import session as cli_session
from thenwhat.cli.console import out
from thenwhat.sources.base import forget_expired


def cache_prune_command() -> None:
    """Delete the cached answers that have expired. Nothing that is still used goes."""
    with cli_session.open_session() as session:
        forgotten = forget_expired(session, datetime.now(UTC))
    out.print(f"Deleted {forgotten} expired cached answers.", markup=False)
