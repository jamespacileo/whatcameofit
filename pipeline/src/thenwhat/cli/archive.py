"""Taking a published claim off the site, and putting it back."""

from datetime import UTC, datetime
from typing import Annotated

import typer

from thenwhat.claims.entry import archive_claim, unarchive_claim
from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session


def archive_command(
    slug: Annotated[str, typer.Argument(help="The claim's slug.")],
    reason: Annotated[
        str, typer.Option("--reason", help="Why it comes down. Kept, never published.")
    ],
) -> None:
    """Take a claim off the public site. Its address answers 410 after the next export."""
    with entry_session() as session:
        claim = archive_claim(session, slug, reason=reason, now=datetime.now(UTC))
        out.print(
            f"Archived {claim.slug}. Export and deploy to take it off the site.", markup=False
        )


def unarchive_command(slug: Annotated[str, typer.Argument(help="The claim's slug.")]) -> None:
    """Put an archived claim back on the public site from the next export on."""
    with entry_session() as session:
        claim = unarchive_claim(session, slug)
        out.print(f"Unarchived {claim.slug}. Export and deploy to put it back.", markup=False)
