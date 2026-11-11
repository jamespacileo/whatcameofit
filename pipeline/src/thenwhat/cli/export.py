"""The export command."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.export.build import write_export, write_schema


def export_command(
    out_path: Annotated[
        Path, typer.Option("--out", envvar="EXPORT_PATH", help="Where to write the export.")
    ] = Path("export/export.json"),
    schema_path: Annotated[
        Path | None,
        typer.Option("--write-schema", help="Also write the export's JSON Schema to this file."),
    ] = None,
) -> None:
    """Write the JSON file the site is built from: approved claims and events only."""
    if schema_path is not None:
        write_schema(schema_path)
        out.print(f"Wrote schema to {schema_path}.", markup=False)
    settings = settings_or_exit()
    with entry_session() as session:
        export = write_export(
            session, out_path, now=datetime.now(UTC), no_signal_years=settings.no_signal_years
        )
        noun = "claim" if len(export.claims) == 1 else "claims"
        out.print(f"Exported {len(export.claims)} {noun} to {out_path}.", markup=False)
