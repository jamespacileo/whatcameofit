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
from thenwhat.store.gather import Gathered, gather, stream
from thenwhat.store.push import USER_AGENT, PushFailed, push, read_state, write_state
from thenwhat.store.tiers import (
    ALL,
    BOTH,
    CHOICES,
    answer_row,
    checksums,
    hash_of,
    hot_records,
    split_build,
)

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
    tier: Annotated[
        str,
        typer.Option(
            help="both: a hot file for D1 and a bulk file for R2 (store.hot.sqlite,"
            " store.bulk.sqlite); hot or bulk: that one; all: the one whole file."
        ),
    ] = BOTH,
) -> None:
    """Build the store from the database, through the store's own merge, as the hot tier
    loaded into D1 and the bulk tier kept as one file in R2 (docs/adr/0010). The database
    is only read. `<file>.pushed.json` records what the build holds, for
    `thenwhat backfill push` to start from once it is loaded."""
    if tier not in CHOICES:
        err.print(f"--tier is one of {', '.join(CHOICES)}.")
        raise typer.Exit(code=1)
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
    out.print(f"Built the whole store ({_size(report.size)}) in {report.runs} runs.", markup=False)
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
    for written in split_build(file, payloads, tier):
        objects = payloads / written.stem.rsplit(".", 1)[-1]
        out.print(
            f"Wrote {written} ({_size(written.stat().st_size)})"
            + (f", its payload objects in {objects}." if tier != ALL else "."),
            markup=False,
        )


@store_app.command("checksum")
def checksum_command(
    file: Annotated[Path, typer.Argument(help="A store file.")],
    tier: Annotated[
        str | None, typer.Option(help="Only the tables of this tier: hot or bulk.")
    ] = None,
    sql: Annotated[
        Path | None,
        typer.Option(help="Also write each table's SQL to this JSON file, for the D1 side."),
    ] = None,
    against: Annotated[
        Path | None,
        typer.Option(
            help="A JSON object of D1's answers by table (each the `wrangler d1 execute"
            " --json` answer to that table's SQL): exit 1 where a checksum differs."
        ),
    ] = None,
) -> None:
    """Each table's rows and checksum in a store file, and the SQL that gives D1 the same
    checksum in one row: one scan of aggregates a table, no sort."""
    if not file.is_file():
        err.print(f"No store file at {file}.")
        raise typer.Exit(code=1)
    found = checksums(file, tier)
    if sql is not None:
        sql.write_text(json.dumps({c.table: c.sql for c in found}, indent=1) + "\n")
    answers = json.loads(against.read_text()) if against is not None else None
    differ = 0
    for checksum in found:
        line = f"{checksum.table}\t{checksum.rows}\t{checksum.sha256}"
        if answers is not None:
            given = answers.get(checksum.table)
            theirs = hash_of(answer_row(given)) if given is not None else "missing"
            same = theirs == checksum.sha256
            differ += not same
            line += "\tsame" if same else f"\tDIFFERS ({theirs})"
        out.print(line, markup=False)
    if differ:
        err.print(f"{differ} table(s) differ.")
        raise typer.Exit(code=1)


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
    every_tier: Annotated[
        bool,
        typer.Option(
            "--every-tier",
            help="Also hand over bulk kinds (trials, leads, shares...), for a store that"
            " holds the bulk tier in D1.",
        ),
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

    left_out = 0
    with reading_session() as session:
        if every_tier:
            records = gather(session, keep_payload=keep_payload).records
        else:
            records, left_out = hot_records(
                stream(session, Gathered(records=[]), keep_payload=keep_payload)
            )
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
    if left_out:
        out.print(
            f"{left_out:,} records of the bulk tier left out: they go with the next bulk file.",
            markup=False,
        )
    for reason, count in sorted(report.left_out.items()):
        out.print(f"{count:,} left out: {reason}.", markup=False)
