"""The export command, and the comparison of the database's export with the store's."""

import json
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import awaiting_audit
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.config import Settings
from thenwhat.db.session import make_engine
from thenwhat.domain import ReviewState
from thenwhat.export.build import write_export, write_schema
from thenwhat.export.parallel import compare_with_store, read_only
from thenwhat.export.store_copy import CopyFailed
from thenwhat.export.store_fetch import FetchFailed, fetch_store, wrangler_in
from thenwhat.export.store_records import StoreFault, StoreRecords

# Where the store's schema and merge are in a checkout.
STORE_SQL = Path(__file__).resolve().parents[4] / "store"

StoreFile = Annotated[
    Path | None,
    typer.Option(
        "--store",
        envvar="STORE_FILE",
        help="Read the records from this SQLite file of the truth store's schema, not from"
        " the database.",
    ),
]
PayloadFolder = Annotated[
    Path | None,
    typer.Option(
        "--payloads",
        envvar="STORE_PAYLOADS",
        help="With --store: the folder holding the store's payload objects under their keys"
        " (payload/<checksum>).",
    ),
]


@contextmanager
def reading_session() -> Generator[Session]:
    """A session the database itself refuses any write in, rolled back when done."""
    engine = make_engine(settings_or_exit().database_url)
    with Session(engine) as session:
        read_only(session)
        try:
            yield session
        finally:
            session.rollback()


def _thresholds(settings: Settings) -> dict[str, Any]:
    return {
        "no_signal_years": settings.no_signal_years,
        "reading_accept_above": settings.reading_accept_above,
        "stage_show_above": settings.stage_show_above,
        "match_accept_above": settings.match_accept_above,
    }


D1Database = Annotated[
    str | None,
    typer.Option(
        "--d1",
        envvar="STORE_D1",
        help="Read the store's records from this D1 database itself: its rows are first"
        " fetched into a store file with `wrangler d1 execute --remote`. Only reads.",
    ),
]
R2Bucket = Annotated[
    str | None,
    typer.Option(
        envvar="STORE_R2_BUCKET",
        help="With --d1 and --payloads: fetch each payload object the folder lacks from"
        " this bucket.",
    ),
]
WranglerDir = Annotated[
    Path, typer.Option(help="With --d1: the folder wrangler is installed and run in.")
]
WranglerConfig = Annotated[
    Path | None,
    typer.Option(
        envvar="STORE_WRANGLER_CONFIG",
        help="With --d1: the Wrangler configuration that names the database.",
    ),
]


def _export_from_store(store: Path, payloads: Path | None, out_path: Path) -> None:
    settings = settings_or_exit()
    try:
        records = StoreRecords(store, payloads=payloads)
        export = write_export(records, out_path, now=datetime.now(UTC), **_thresholds(settings))
        held = records.held()
        records.close()
    except StoreFault as fault:
        err.print(str(fault), markup=False)
        raise typer.Exit(code=1) from None
    noun = "claim" if len(export.claims) == 1 else "claims"
    out.print(f"Exported {len(export.claims)} {noun} from {store} to {out_path}.", markup=False)
    unchecked = sum(1 for claim in export.claims if not claim.checked_by_person)
    if unchecked:
        out.print(f"{unchecked} of them have not been checked by a person.", markup=False)
    if records.first_published:
        out.print(
            f"{len(records.first_published)} of them have no published time in the store."
            " Nothing was written to it.",
            markup=False,
        )
    if held:
        noun = "claim was" if held == 1 else "claims were"
        out.print(f"{held} approved {noun} left out: awaiting audit.", markup=False)


def export_command(
    out_path: Annotated[
        Path, typer.Option("--out", envvar="EXPORT_PATH", help="Where to write the export.")
    ] = Path("export/export.json"),
    schema_path: Annotated[
        Path | None,
        typer.Option("--write-schema", help="Also write the export's JSON Schema to this file."),
    ] = None,
    store: StoreFile = None,
    payloads: PayloadFolder = None,
    d1: D1Database = None,
    r2_bucket: R2Bucket = None,
    wrangler_dir: WranglerDir = STORE_SQL / "ingest",
    wrangler_config: WranglerConfig = None,
) -> None:
    """Write the JSON file the site is built from: approved, unarchived claims and events.
    A claim awaiting audit is left out and counted.

    With --store the records are read from a SQLite file of the truth store's schema
    instead of the database. The file is only read. With --d1 as well, that file is
    first made from the D1 database named, which is only read."""
    if schema_path is not None:
        write_schema(schema_path)
        out.print(f"Wrote schema to {schema_path}.", markup=False)
    if d1 is not None:
        if store is None:
            err.print("With --d1, name the store file to fetch into with --store.")
            raise typer.Exit(code=1)
        try:
            fetched = fetch_store(
                d1,
                store,
                schema=STORE_SQL / "schema.sql",
                wrangler=wrangler_in(wrangler_dir, wrangler_config),
                payloads=payloads,
                bucket=r2_bucket,
            )
        except FetchFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
        out.print(
            f"Fetched {sum(fetched.rows.values())} rows of {d1} in {fetched.queries} queries"
            f" ({fetched.objects_fetched} payload objects).",
            markup=False,
        )
    if store is not None:
        _export_from_store(store, payloads, out_path)
        return
    settings = settings_or_exit()
    with entry_session() as session:
        export = write_export(session, out_path, now=datetime.now(UTC), **_thresholds(settings))
        noun = "claim" if len(export.claims) == 1 else "claims"
        out.print(f"Exported {len(export.claims)} {noun} to {out_path}.", markup=False)
        unchecked = sum(1 for claim in export.claims if not claim.checked_by_person)
        if unchecked:
            out.print(f"{unchecked} of them have not been checked by a person.", markup=False)
        held = sum(
            1
            for claim in awaiting_audit(session)
            if claim.review_state is ReviewState.APPROVED and claim.archived_at is None
        )
        if held:
            noun = "claim was" if held == 1 else "claims were"
            out.print(
                f"{held} approved {noun} left out: awaiting audit (thenwhat audit list).",
                markup=False,
            )


def export_compare_command(
    store: StoreFile = None,
    payloads: PayloadFolder = None,
    every: Annotated[
        int,
        typer.Option(
            min=1,
            help="Without --store: copy and compare every Nth claim, not all of them.",
        ),
    ] = 1,
    store_sql: Annotated[
        Path,
        typer.Option(
            envvar="STORE_SQL",
            help="Without --store: the folder of the store's schema.sql, merge.sql and ingest.sql.",
        ),
    ] = STORE_SQL,
    keep: Annotated[
        Path | None,
        typer.Option(help="Without --store: keep the store file made in this folder."),
    ] = None,
    report: Annotated[
        Path | None, typer.Option(help="Also write the comparison to this file, as JSON.")
    ] = None,
    d1: D1Database = None,
    r2_bucket: R2Bucket = None,
    wrangler_dir: WranglerDir = STORE_SQL / "ingest",
    wrangler_config: WranglerConfig = None,
    allow_named: Annotated[
        bool,
        typer.Option(
            "--allow-named",
            help="Exit with 0 when every difference has a named cause; each is still listed.",
        ),
    ] = False,
) -> None:
    """Compare the export the database gives with the export the truth store gives, for
    the same claims at the same moment. Exits with 1 when they differ.

    A difference the comparison can explain is listed with its cause (the data holds
    what the store cannot, or the store's merge reorders a list). With --allow-named
    only a difference without a cause fails the comparison.

    With --store, the store's export is read from that file, whoever built it. With
    --d1, from the D1 database itself. With neither, a store file is first made from the
    database through the store's own merge, which shows whether the store can hold the
    records, not whether it does.

    Nothing is written to the database or to the store file given."""
    settings = settings_or_exit()
    if store is not None and d1 is not None:
        err.print("Give --store or --d1, not both.")
        raise typer.Exit(code=1)
    if store is None and not (store_sql / "merge.sql").is_file():
        err.print(f"No merge.sql in {store_sql}. Name the store's folder with --store-sql.")
        raise typer.Exit(code=1)
    with tempfile.TemporaryDirectory() as scratch, reading_session() as session:
        try:
            if d1 is not None:
                store = (keep or Path(scratch)) / "store.db"
                fetched = fetch_store(
                    d1,
                    store,
                    schema=store_sql / "schema.sql",
                    wrangler=wrangler_in(wrangler_dir, wrangler_config),
                    payloads=payloads,
                    bucket=r2_bucket,
                )
                out.print(
                    f"Fetched {sum(fetched.rows.values())} rows of {d1} in {fetched.queries}"
                    f" queries ({fetched.objects_fetched} payload objects).",
                    markup=False,
                )
            result = compare_with_store(
                session,
                now=datetime.now(UTC),
                store=store,
                payloads=payloads,
                work=keep or Path(scratch),
                store_sql=store_sql,
                every=every,
                **_thresholds(settings),
            )
        except (StoreFault, CopyFailed, FetchFailed) as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    if result.copy is not None:
        handed = sum(result.copy.handed.values())
        out.print(
            f"Copied {handed} records to a store file in {result.copy.runs} runs"
            f" ({result.copy.payload_objects} payloads as objects).",
            markup=False,
        )
        for kind, fewer in sorted(result.copy.folded.items()):
            out.print(
                f"{fewer} {kind} records share a natural key with another and were not"
                " handed over.",
                markup=False,
            )
        for note in result.copy.notes:
            out.print(note, markup=False)
    for line in result.comparison.lines():
        out.print(line, markup=False)
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result.as_json(), indent=2, ensure_ascii=False) + "\n")
        out.print(f"Wrote the comparison to {report}.", markup=False)
    failing = result.comparison.unexplained if allow_named else result.comparison.differences
    if failing:
        raise typer.Exit(code=1)
