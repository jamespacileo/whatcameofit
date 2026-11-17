"""The truth store filled in bulk: a store file built from the database, and the SQL files
D1's import takes it in by."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from thenwhat.cli.console import err, out
from thenwhat.cli.export import STORE_SQL, reading_session
from thenwhat.store.build import BuildFailed, build

store_app = typer.Typer(help="Fill the truth store in bulk, and restore it.", no_args_is_help=True)

StoreSql = Annotated[
    Path,
    typer.Option(
        envvar="STORE_SQL", help="The folder of the store's schema.sql, merge.sql and ingest.sql."
    ),
]


def _size(count: int) -> str:
    return f"{count / 1_000_000:,.1f} MB"


@store_app.command("build")
def build_command(
    file: Annotated[Path, typer.Argument(help="The store file to write; one there is replaced.")],
    payloads: Annotated[
        Path,
        typer.Option(
            "--payloads", help="The folder large payloads are written to, under their R2 keys."
        ),
    ],
    store_sql: StoreSql = STORE_SQL,
) -> None:
    """Build the whole store as one SQLite file from the database, through the store's own
    merge. The database is only read."""
    if not (store_sql / "merge.sql").is_file():
        err.print(f"No merge.sql in {store_sql}. Name the store's folder with --store-sql.")
        raise typer.Exit(code=1)
    with reading_session() as session:
        try:
            report = build(
                session, file, payloads=payloads, store_sql=store_sql, now=datetime.now(UTC)
            )
        except BuildFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    out.print(f"Built {file} ({_size(report.size)}) in {report.runs} runs.", markup=False)
    for kind in sorted(report.handed):
        out.print(
            f"  {kind}: {report.handed[kind]:,} handed over, {report.added[kind]:,} added",
            markup=False,
        )
    out.print(
        f"{report.payload_objects:,} payloads written to {payloads}"
        f" ({_size(report.payload_bytes)}).",
        markup=False,
    )
    for kind, count in sorted(report.repeated.items()):
        out.print(f"{count:,} {kind} rows share a natural key with an earlier row.", markup=False)
    for kind, count in sorted(report.unnamed.items()):
        out.print(f"{count:,} {kind} rows name no record the store keeps.", markup=False)
