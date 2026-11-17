"""The truth store filled in bulk: a store file built from the database, and the SQL files
D1's import takes it in by."""

import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
import typer
from sqlalchemy.orm import Session

from thenwhat.cli.backfill import backfill_app
from thenwhat.cli.console import err, out
from thenwhat.cli.export import STORE_SQL, reading_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.db.session import make_engine
from thenwhat.export.parallel import read_only
from thenwhat.store.build import (
    BuildFailed,
    apply_delta,
    base_of,
    build,
    merge_day,
    write_delta,
)
from thenwhat.store.dump import DumpRefused, counts_of, differences, dump
from thenwhat.store.form import Payload
from thenwhat.store.gather import Gathered, gather, stream
from thenwhat.store.inbox import InboxFailed, clear, fold, record_fold
from thenwhat.store.people import (
    FIELDS,
    PROOF_SQL,
    emails_left,
    prove_file,
    prove_file_objects,
    strip,
    strip_papers,
)
from thenwhat.store.push import (
    USER_AGENT,
    PushFailed,
    push,
    read_state,
    write_state,
)
from thenwhat.store.tiers import (
    ALL,
    BOTH,
    CHOICES,
    answer_row,
    bulk_records,
    checks,
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


def bulk_state_path(file: Path) -> Path:
    """What the bulk file holds, for `thenwhat store merge-bulk` to start from."""
    return file.with_name(file.name + ".bulk.json")


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
    write_state(bulk_state_path(file), report.state)
    out.print(f"Build {report.build_id}.", markup=False)
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
    checks_file: Annotated[
        Path | None,
        typer.Option(
            "--checks",
            help="Also write the checks store/ingest/scripts/checksum-d1.mjs runs: each"
            " table's SQL and the row it must give, and the build's id.",
        ),
    ] = None,
    against: Annotated[
        Path | None,
        typer.Option(
            help="A JSON object of D1's answers by table: for each, a list of the `wrangler d1"
            " execute --json` answers to that table's statements, in order. Exit 1 where a"
            " checksum differs."
        ),
    ] = None,
) -> None:
    """Each table's rows and checksum in a store file, and the SQL that gives D1 the same
    checksum in one row: one scan of aggregates a table, no sort."""
    if not file.is_file():
        err.print(f"No store file at {file}.")
        raise typer.Exit(code=1)
    found = checksums(file, tier)
    if checks_file is not None:
        checks_file.write_text(json.dumps(checks(file, tier), indent=1) + "\n")
    if sql is not None:
        sql.write_text(json.dumps({c.table: c.sql for c in found}, indent=1) + "\n")
    answers = json.loads(against.read_text()) if against is not None else None
    differ = 0
    for checksum in found:
        line = f"{checksum.table}\t{checksum.rows}\t{checksum.sha256}"
        if answers is not None:
            given = answers.get(checksum.table)
            theirs = (
                hash_of([answer_row(part) for part in given]) if given is not None else "missing"
            )
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


@store_app.command("merge-bulk")
def merge_bulk_command(
    file: Annotated[
        Path, typer.Argument(help="The bulk file, as the last build or merge left it.")
    ],
    state: Annotated[
        Path,
        typer.Option(help="What the bulk file holds: `<store file>.bulk.json` from the build."),
    ],
    delta: Annotated[
        Path, typer.Option(help="Write the day's records here, gzipped JSON lines, for R2.")
    ],
    payloads: Annotated[Path, typer.Option(help="The bulk tier's folder of payload objects.")],
    store_sql: StoreSql = STORE_SQL,
) -> None:
    """Merge the day's records of the bulk tier into the bulk file, by the store's own
    merge, as the one writer of that file (docs/adr/0010), and write them as the day's
    delta to keep beside the last bulk build. The database is only read."""
    if not file.is_file() or not state.is_file():
        err.print(f"No bulk file at {file}, or no state at {state}.")
        raise typer.Exit(code=1)
    held = read_state(state)

    def keep_payload(payload: Payload) -> None:
        if not payload.inline and f"payload\t{payload.sha256}" not in held:
            target = payloads / payload.r2_key
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload.text.encode())

    with reading_session() as session:
        records, _ = bulk_records(stream(session, Gathered(records=[]), keep_payload=keep_payload))
    try:
        chosen, added = merge_day(
            file, records, held, delta=delta, store_sql=store_sql, now=datetime.now(UTC)
        )
    except BuildFailed as fault:
        err.print(str(fault), markup=False)
        raise typer.Exit(code=1) from None
    write_state(state, held)
    out.print(
        f"Merged {len(chosen.records):,} records into {file}; the delta is {delta}"
        f" ({_size(delta.stat().st_size)}).",
        markup=False,
    )
    for kind, count in sorted(added.items()):
        if count:
            out.print(f"  {kind}: {count:,} added", markup=False)
    for reason, count in sorted(chosen.left_out.items()):
        out.print(f"{count:,} left out: {reason}.", markup=False)


@store_app.command("apply-delta")
def apply_delta_command(
    file: Annotated[Path, typer.Argument(help="A bulk file downloaded from R2.")],
    deltas: Annotated[list[Path], typer.Argument(help="The deltas kept beside it, oldest first.")],
    store_sql: StoreSql = STORE_SQL,
) -> None:
    """Bring a downloaded bulk file up to date by merging its deltas into it in order: the
    bulk tier's restore."""
    missing = [delta for delta in [file, *deltas] if not delta.is_file()]
    if missing:
        err.print(f"No file at {missing[0]}.")
        raise typer.Exit(code=1)
    for delta in deltas:
        try:
            merged = apply_delta(file, delta, store_sql=store_sql, now=datetime.now(UTC))
        except BuildFailed as fault:
            err.print(f"{delta}: {fault}", markup=False)
            raise typer.Exit(code=1) from None
        out.print(
            f"Applied {delta}: {len(merged)} runs merged."
            if merged
            else f"{delta} was already applied: nothing merged.",
            markup=False,
        )


def _service(url: str) -> httpx.Client:
    token = os.environ.get("INGEST_TOKEN", "")
    if not url or not token:
        err.print("Set INGEST_URL (or --url) and INGEST_TOKEN, the daily or operator token.")
        raise typer.Exit(code=1)
    return httpx.Client(
        base_url=url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        timeout=120,
    )


@store_app.command("fold-inbox")
def fold_inbox_command(
    file: Annotated[Path, typer.Argument(help="The bulk file the daily job keeps.")],
    delta: Annotated[
        Path, typer.Option(help="Write the folded records here, gzipped JSON lines, for R2.")
    ],
    url: Annotated[
        str, typer.Option("--url", envvar="INGEST_URL", help="The ingest service's address.")
    ] = "",
    after: Annotated[int, typer.Option(help="Fold only the inbox after this seq.")] = 0,
    store_sql: StoreSql = STORE_SQL,
) -> None:
    """Merge the bulk records lookups handed to D1 into the bulk file, and write them as a
    delta. Nothing is cleared: once the delta is kept in R2, run `thenwhat store
    clear-inbox --through` with the seq this prints."""
    if not file.is_file():
        err.print(f"No bulk file at {file}.")
        raise typer.Exit(code=1)
    with _service(url) as client:
        try:
            folded = fold(client, file, store_sql=store_sql, now=datetime.now(UTC), after=after)
        except InboxFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    write_delta(delta, folded.named, base=base_of(file, folded.named))
    out.print(
        f"Folded {len(folded.records):,} records of {len(folded.named)} runs into {file}"
        f" ({folded.runs} merged now, the others already);"
        f" the delta is {delta}. Through seq {folded.through}.",
        markup=False,
    )


@store_app.command("clear-inbox")
def clear_inbox_command(
    through: Annotated[int, typer.Option(help="The last seq folded, as fold-inbox printed it.")],
    object_key: Annotated[
        str | None,
        typer.Option(
            "--object",
            help="The delta's key in the bucket, as upload-delta.mjs printed it: the fold is"
            " recorded first. Leave it out on a quiet day, with --through at or below the"
            " last fold recorded.",
        ),
    ] = None,
    url: Annotated[
        str, typer.Option("--url", envvar="INGEST_URL", help="The ingest service's address.")
    ] = "",
) -> None:
    """Have the service clear the inbox up to a seq, and the rows those runs added to D1,
    once their delta is kept in R2: with --object, the fold into that delta is recorded
    first (docs/deploy.md, "The daily fold, in order"). Run it every day, with nothing new
    too (`--through` the last fold recorded, or 0): a lead held while its processing was
    due is removed by a later clear."""
    with _service(url) as client:
        try:
            if object_key is not None:
                recorded = record_fold(client, through, object_key)
                out.print(
                    f"Recorded the fold through seq {recorded.get('folded_through', through)}"
                    f" into {object_key}.",
                    markup=False,
                )
            answer = clear(client, through)
        except InboxFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    out.print(
        f"Cleared {answer.get('cleared', 0):,} inbox records and {answer.get('rows_removed', 0):,}"
        f" rows of D1; {answer.get('left', 0):,} left; {answer.get('leads_held', 0):,} leads held"
        " in D1 until their processing is done.",
        markup=False,
    )


@backfill_app.command("strip-event-people")
def strip_event_people_command(
    apply: Annotated[
        bool, typer.Option("--apply", help="Write the records without people; else only count.")
    ] = False,
) -> None:
    """Count the people named in the registry records stored with evidence events and
    registry trials (officials, contacts, investigators, a sponsor who is a person) and,
    with --apply, store each record without them. Running it again changes nothing."""
    engine = make_engine(settings_or_exit().database_url)
    with Session(engine) as session:
        if not apply:
            read_only(session)  # counting writes nothing, and the database refuses it
        report = strip(session, apply=apply)
        session.rollback()
    for table in report.before:
        out.print(
            f"{table}: {report.rows[table]:,} registry records,"
            f" {report.changed[table]:,} naming a person"
            + (" (written without)" if apply else " (counted only; --apply writes)"),
            markup=False,
        )
        for name in FIELDS:
            out.print(
                f"  {name}: {report.before[table][name]:,} before,"
                f" {report.after[table][name]:,} after",
                markup=False,
            )
    out.print(f'Prove it: psql "$DATABASE_URL" -f {PROOF_SQL}', markup=False)


@store_app.command("prove-no-people")
def prove_no_people_command(
    files: Annotated[list[Path], typer.Argument(help="Store files: the hot and the bulk one.")],
    payloads: Annotated[
        list[Path] | None,
        typer.Option("--payloads", help="Folders of payload objects to read too."),
    ] = None,
) -> None:
    """Count the people the payloads of store files and their objects on disk name. Exits
    with 1 when any is found."""
    found: Counter[str] = Counter()
    for file in files:
        if not file.is_file():
            err.print(f"No store file at {file}.")
            raise typer.Exit(code=1)
        found.update({f"{file.name}: {k}": v for k, v in prove_file(file).items()})
    for folder in payloads or []:
        found.update({f"{folder}: {k}": v for k, v in prove_file_objects(folder).items()})
    for name, count in sorted(found.items()):
        err.print(f"{name}: {count:,}", markup=False)
    if found:
        raise typer.Exit(code=1)
    out.print("No person is named in these files.", markup=False)


@backfill_app.command("strip-paper-people")
def strip_paper_people_command(
    apply: Annotated[
        bool, typer.Option("--apply", help="Write the records without them; else only count.")
    ] = False,
) -> None:
    """Count the authors, their identifiers and affiliations, the abstracts and any person's
    keys in every stored payload that is not a registry study (a follow-up paper's record,
    a retraction notice, a paper's or a trial paper's record) and, with --apply, store each
    without them (openspec paper-facts). Running it again changes nothing."""
    engine = make_engine(settings_or_exit().database_url)
    with Session(engine) as session:
        if not apply:
            read_only(session)
        report = strip_papers(session, apply=apply)
        left = emails_left(session)
        session.rollback()
    for table, source in sorted(report.rows):
        out.print(
            f"{table} {source}: {report.rows[(table, source)]:,} records,"
            f" {report.changed[(table, source)]:,} naming a person or holding an abstract"
            + (" (written without)" if apply else " (counted only; --apply writes)"),
            markup=False,
        )
        for (t, s, key), count in sorted(report.before.items()):
            if (t, s) == (table, source):
                out.print(
                    f"  {key}: {count:,} before, {report.after[(t, s, key)]:,} after", markup=False
                )
    out.print(
        f"Registry studies with an email address left in a text once stripped (reported,"
        f" not changed): {left['with an email in a text']:,} of {left['studies']:,}.",
        markup=False,
    )
    out.print(f'Prove it: psql "$DATABASE_URL" -f {PROOF_SQL}', markup=False)
