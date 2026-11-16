"""Claims that `thenwhat prepare` approved and that wait for the audit of their batch."""

from typing import Annotated

import typer

from thenwhat.claims.entry import awaiting_audit, clear_audit
from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session

audit_app = typer.Typer(no_args_is_help=True, help="Claims held off the site until audited.")


@audit_app.command("list")
def audit_list() -> None:
    """List the claims held off the site until audited, oldest hold first."""
    with entry_session() as session:
        held = awaiting_audit(session)
        if not held:
            out.print("No claim awaits audit.")
            return
        for claim in held:
            assert claim.awaiting_audit_at is not None
            archived = "  archived" if claim.archived_at is not None else ""
            out.print(
                f"{claim.slug}  held since {claim.awaiting_audit_at:%Y-%m-%d %H:%M}"
                f"  {claim.current_status.value}{archived}",
                markup=False,
            )
        noun = "claim awaits" if len(held) == 1 else "claims await"
        out.print(f"{len(held)} {noun} audit.", markup=False)


@audit_app.command("clear")
def audit_clear(
    slugs: Annotated[list[str], typer.Argument(help="Slugs of the claims whose audit passed.")],
) -> None:
    """Let audited claims be published from the next export on. A claim that should not
    be published is archived instead. If any slug is not awaiting audit, nothing is cleared."""
    with entry_session() as session:
        cleared = clear_audit(session, slugs)
        noun = "claim" if len(cleared) == 1 else "claims"
        out.print(
            f"Cleared {len(cleared)} {noun}. Export and deploy to publish them.", markup=False
        )
        for claim in cleared:
            if claim.archived_at is not None:
                out.print(f"{claim.slug} is archived and stays off the site.", markup=False)
