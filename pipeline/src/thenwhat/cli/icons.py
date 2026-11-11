"""The icons command."""

from typing import Annotated

import typer

from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.outlets.icons import IconFetcher, fetch_outlet_icons


def make_icon_fetcher() -> IconFetcher:
    return IconFetcher(contact_email=settings_or_exit().contact_email)


def icons_command(
    retry_missing: Annotated[
        bool,
        typer.Option("--retry-missing", help="Ask again the outlets that had no usable icon."),
    ] = False,
) -> None:
    """Fetch each outlet's own icon, once per domain, for the site to show beside its name."""
    with entry_session() as session:
        run = fetch_outlet_icons(session, make_icon_fetcher(), retry_missing=retry_missing)
        out.print(
            f"Stored {len(run.stored)} outlet icons. {len(run.none_found)} outlets had none."
            f" {run.already_asked} were asked before.",
            markup=False,
        )
        for domain in run.none_found:
            out.print(f"No usable icon: {domain}", markup=False)
