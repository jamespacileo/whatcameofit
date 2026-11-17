"""The truth store filled in bulk: a store file built from the database, and the SQL files
D1's import takes it in by."""

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
import typer

from thenwhat.cli.backfill import backfill_app
from thenwhat.cli.console import err, out
from thenwhat.cli.export import STORE_SQL, reading_session
from thenwhat.store.build import BuildFailed, build
from thenwhat.store.dump import DumpRefused, counts_of, differences, dump
from thenwhat.store.form import Payload
from thenwhat.store.gather import gather
from thenwhat.store.push import USER_AGENT, PushFailed, push, read_state, write_state

store_app = typer.Typer(help="Fill the truth store in bulk, and restore it.", no_args_is_help=True)

StoreSql = Annotated[
    Path,
    typer.Option(
        envvar="STORE_SQL", help="The folder of the store's schema.sql, merge.sql and ingest.sql."
    ),
]


def state_path(file: Path) -> Path:
    return file.with_name(file.name + ".pushed.json")


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
    merge. The database is only read. Beside the file, `<file>.pushed.json` records what
    it holds, for `thenwhat backfill push` to start from once it is loaded."""
    if not (store_sql / "merge.sql").is_file():
        err.print(f"No merge.sql in {store_sql}. Name the store's folder with --store-sql.")
        raise typer.Exit(code=1)
    with reading_session() as session:
        try:
            report = build(
                session,
                file,
                payloads=payloads,
                store_sql=store_sql,
                now=datetime.now(UTC),
                on_kind=lambda kind, count, seconds: out.print(
                    f"  {kind}: {count:,} read and merged in {seconds:,.1f} s", markup=False
                ),
            )
        except BuildFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    write_state(state_path(file), report.state)
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
    for table, rows in manifest.left_out.items():
        out.print(
            f"{rows:,} {table} rows are too large for one D1 statement and were left out;"
            " they are fetched again.",
            markup=False,
        )
    out.print(
        "Load and count: node store/ingest/scripts/import-folder.mjs"
        f" {out_folder} --remote (docs/deploy.md).",
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


def _commit() -> str:
    try:
        found = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=STORE_SQL
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    return found


@backfill_app.command("push")
def push_command(
    state: Annotated[
        Path,
        typer.Option(
            "--state",
            envvar="STORE_PUSH_STATE",
            help="What was last handed over: `<store file>.pushed.json` from the build, kept"
            " up to date by each push.",
        ),
    ],
    url: Annotated[
        str, typer.Option("--url", envvar="INGEST_URL", help="The ingest service's address.")
    ] = "",
    writer: Annotated[
        str,
        typer.Option(help="The run's writer, as the token may register: daily, device, operator."),
    ] = "daily",
    actions: Annotated[
        bool, typer.Option("--actions", help="Also hand over actions (the operator's token only).")
    ] = False,
    report_only: Annotated[
        bool,
        typer.Option("--report-only", help="Say what each run would do, apply nothing."),
    ] = False,
) -> None:
    """Hand the day's changes to the ingest service: every record new or changed since
    the last push or the build. The token is read from INGEST_TOKEN. The database is
    only read."""
    if not url:
        err.print("No ingest address: set INGEST_URL or give --url.")
        raise typer.Exit(code=1)
    token = os.environ.get("INGEST_TOKEN", "")
    if not token:
        err.print("INGEST_TOKEN is not set.")
        raise typer.Exit(code=1)
    if not state.is_file():
        err.print(
            f"No state at {state}. Build and load the store first (thenwhat store build);"
            " a push hands over only what changed since."
        )
        raise typer.Exit(code=1)
    commit = _commit()
    if not commit:
        err.print("The commit of this code could not be read; run from the repository.")
        raise typer.Exit(code=1)
    held = read_state(state)
    texts: dict[str, str] = {}

    def keep_payload(payload: Payload) -> None:
        if not payload.inline and f"payload\t{payload.sha256}" not in held:
            texts[payload.sha256] = payload.text

    with reading_session() as session:
        records = gather(session, keep_payload=keep_payload).records
    with httpx.Client(
        base_url=url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        timeout=120,
    ) as client:
        try:
            report = push(
                client,
                records,
                held,
                writer=writer,
                commit=commit,
                payload_text=texts.get,
                actions=actions,
                report_only=report_only,
                on_merged=lambda now: write_state(state, now),
            )
        except PushFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    out.print(
        ("Would hand over" if report_only else "Handed over")
        + f" {sum(report.handed.values()):,} records in {report.runs} runs"
        f" ({report.payloads_put} payloads put).",
        markup=False,
    )
    for kind in sorted(report.handed):
        out.print(
            f"  {kind}: {report.handed[kind]:,} handed over, {report.added[kind]:,} added",
            markup=False,
        )
    for reason, count in sorted(report.left_out.items()):
        out.print(f"{count:,} left out: {reason}.", markup=False)
