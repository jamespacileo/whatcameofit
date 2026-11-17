"""The truth store filled in bulk: a store file built from the database, and the SQL files
D1's import takes it in by."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from thenwhat.cli.console import err, out
from thenwhat.cli.export import STORE_SQL, reading_session
from thenwhat.store.build import BuildFailed, build
from thenwhat.store.dump import DumpRefused, count_query, counts_of, differences, dump

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


@store_app.command("dump")
def dump_command(
    file: Annotated[
        Path, typer.Argument(help="The store file, as `thenwhat store build` wrote it.")
    ],
    out_folder: Annotated[
        Path, typer.Argument(help="The folder for the SQL files and manifest.json.")
    ],
    payloads: Annotated[
        Path | None,
        typer.Option("--payloads", help="The build's payload folder, counted into the manifest."),
    ] = None,
) -> None:
    """Write a store file as data-only SQL files for D1's import, into a database that
    already has the schema, and a manifest to check the load against."""
    if not file.is_file():
        err.print(f"No store file at {file}.")
        raise typer.Exit(code=1)
    try:
        manifest = dump(file, out_folder, payloads=payloads)
    except DumpRefused as fault:
        err.print(str(fault), markup=False)
        raise typer.Exit(code=1) from None
    total = sum(entry["bytes"] for entry in manifest.files)
    out.print(
        f"Wrote {len(manifest.files)} files ({_size(total)}) and manifest.json to {out_folder}.",
        markup=False,
    )
    for table, rows in manifest.tables.items():
        if rows:
            out.print(f"  {table}: {rows:,}", markup=False)
    out.print(
        "Load each file in name order: wrangler d1 execute <db> --remote --file <file>.",
        markup=False,
    )
    (out_folder / "counts.sql").write_text(
        count_query(json.loads((out_folder / "manifest.json").read_text())) + "\n"
    )
    out.print(
        "Then: wrangler d1 execute <db> --remote --json --file counts.sql > counts.json,"
        " and thenwhat store check.",
        markup=False,
    )


@store_app.command("check")
def check_command(
    manifest: Annotated[Path, typer.Argument(help="The dump's manifest.json.")],
    counts: Annotated[
        Path,
        typer.Argument(
            help="The answer of `wrangler d1 execute --json --file counts.sql`, or a JSON"
            " object of counts by table."
        ),
    ],
) -> None:
    """Compare a loaded store's counts with the dump's manifest. Exits with 1 when they
    differ."""
    expected = json.loads(manifest.read_text())
    found = differences(expected, counts_of(json.loads(counts.read_text())))
    if found:
        for line in found:
            err.print(line, markup=False)
        raise typer.Exit(code=1)
    out.print(f"All {len(expected['tables'])} tables hold the manifest's counts.", markup=False)
