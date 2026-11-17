"""The trials-listing command."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from thenwhat.backfill.trial_sets import ROLLING
from thenwhat.cli import session as cli_session
from thenwhat.cli.console import err, out
from thenwhat.cli.session import settings_or_exit
from thenwhat.export.trials_listing import UnknownSet, write_listing, write_listing_schema

# The set the site lists, by the operator's decision of 2026-11-17: trials under way
# now, or ended in the current calendar year.
DEFAULT_SET = ROLLING


def trials_listing_command(
    out_path: Annotated[Path, typer.Option("--out", help="Where to write the listing.")] = Path(
        "export/trials-listing.json"
    ),
    set_name: Annotated[
        str, typer.Option("--set", help="The named set of stored trials to list.")
    ] = DEFAULT_SET,
    schema_path: Annotated[
        Path | None,
        typer.Option("--write-schema", help="Also write the listing's JSON Schema to this file."),
    ] = None,
) -> None:
    """Write the trial listing the site's search and trial page are built with: for each
    stored trial of a named set, its registry number, title, acronym, phases, state, the
    day the registry last changed it, conditions, intervention names, and the published
    claim that cites it, if one does. Registry facts only. Sends no request and changes
    nothing in the database."""
    if schema_path is not None:
        write_listing_schema(schema_path)
        out.print(f"Wrote schema to {schema_path}.", markup=False)
    settings_or_exit()
    with cli_session.open_session() as session:
        try:
            # The rolling set is chosen by the year, read from the clock here and nowhere else.
            listing = write_listing(session, out_path, set_name, datetime.now(UTC).year)
        except UnknownSet as error:
            err.print(str(error), markup=False)
            raise typer.Exit(code=1) from None
    if not listing.trials:
        # Written all the same: a site built with an empty listing opens no trial page.
        err.print(
            f"The set {set_name} holds no stored trial, so the listing at {out_path} is "
            "empty. Count the sets with `thenwhat backfill trial-sets`.",
            markup=False,
        )
        return
    cited = sum(1 for row in listing.trials if row[-1] is not None)
    size = out_path.stat().st_size
    noun = "trial" if len(listing.trials) == 1 else "trials"
    out.print(
        f"Listed {len(listing.trials):,} {noun} of {set_name} in {out_path}: "
        f"{size:,} bytes, {cited:,} cited by a published claim, "
        f"records read up to {listing.records_read}.",
        markup=False,
    )
