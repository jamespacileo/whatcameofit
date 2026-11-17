"""The truth store filled in bulk: a store file built from the database, and the SQL files
D1's import takes it in by."""

import json
import os
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_sets import rule_of
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
    build_id_of,
    merge_day,
    write_delta,
)
from thenwhat.store.form import Payload
from thenwhat.store.gather import Gathered, gather, stream
from thenwhat.store.inbox import InboxFailed, clear, fold, record_fold
from thenwhat.store.people import (
    ABSTRACTS_PROOF_SQL,
    FIELDS,
    PROOF_SQL,
    prove_file,
    prove_file_objects,
    strip,
    strip_abstracts,
)
from thenwhat.store.push import (
    BUILD_KEY,
    TARGET_KEY,
    USER_AGENT,
    PushFailed,
    RetryOnBusy,
    check_store,
    check_target,
    pending_path,
    push,
    read_pending,
    read_state,
    store_build,
    target_of,
    undone_of,
    write_state,
)
from thenwhat.store.tiers import (
    ALL,
    BOTH,
    BULK,
    CHOICES,
    HOT,
    answer_row,
    bulk_records,
    checks,
    checksums,
    hash_of,
    hot_records,
    split_build,
    tier_path,
)
from thenwhat.store.watermark import (
    BULK_SOURCES,
    HOT_SOURCES,
    build_id,
    bulk_unchanged,
    sql_digest,
    watermarks,
)
from thenwhat.store.watermark import read as watermark_read
from thenwhat.store.watermark import write as watermark_write

store_app = typer.Typer(help="Fill the truth store in bulk, and restore it.", no_args_is_help=True)

StoreSql = Annotated[
    Path,
    typer.Option(
        envvar="STORE_SQL", help="The folder of the store's schema.sql, merge.sql and ingest.sql."
    ),
]


def state_path(file: Path) -> Path:
    return file.with_name(file.name + ".pushed.json")


def base_state_path(file: Path) -> Path:
    """What the hot file holds, as a push state for a store loaded from it and pushed to
    by nothing yet: `thenwhat store fresh-state` starts a store's own state from it."""
    return file.with_name(file.name + ".base-state.json")


def bulk_state_path(file: Path) -> Path:
    """What the bulk file holds, for `thenwhat store merge-bulk` to start from."""
    return file.with_name(file.name + ".bulk.json")


# The trial target set, decided by the operator on 2026-11-17. Its trials reach D1 by
# slice pushes (`thenwhat backfill slices`), never by a build's split (docs/adr/0010).
TARGET_SET = "active-or-ended-this-year"


def target_rule(name: str) -> tuple[Any, str]:
    """The rule over stored trials of the named target set, chosen in this year, and how it
    is named; the registry corpus's own rule (`backfill.trial_sets.rule_of`)."""
    year = datetime.now(UTC).year
    return rule_of(name, year)(), f"{name}:{year}"


def remove_pending(file: Path, *, bulk_too: bool) -> list[Path]:
    """The pending runs a build of `file` makes stale, removed: the hot push's, and the bulk
    merge's when the bulk file is built again. The build holds what they carried."""
    replaced = [state_path(file), tier_path(file, HOT)]
    if bulk_too:
        replaced += [bulk_state_path(file), tier_path(file, BULK)]
    removed = [pending_path(path) for path in replaced if pending_path(path).is_file()]
    for stale in removed:
        stale.unlink()
    return removed


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
    fresh: Annotated[
        bool,
        typer.Option(
            "--fresh", help="Build every tier again, even one whose sources have not changed."
        ),
    ] = False,
) -> None:
    """Build the store from the database, through the store's own merge, as the hot tier
    loaded into D1 and the bulk tier kept as one file in R2 (docs/adr/0010). The database
    is only read. `<file>.pushed.json` records what the build holds, for
    `thenwhat backfill push` to start from once it is loaded.

    A rebuild into the same folder leaves the bulk file as it is when none of its sources
    has changed since the last build (`<file>.watermarks.json`; store/watermark.py) and
    builds the hot tier only; --fresh builds both. `--tier hot` reads no bulk table."""
    if tier not in CHOICES:
        err.print(f"--tier is one of {', '.join(CHOICES)}.")
        raise typer.Exit(code=1)
    if not (store_sql / "merge.sql").is_file():
        err.print(f"No merge.sql in {store_sql}. Name the store's folder with --store-sql.")
        raise typer.Exit(code=1)
    digest = sql_digest(store_sql)
    started = time.monotonic()
    with reading_session() as session:
        # A hot build reads only the hot tier's sources, its watermarks included.
        marks = watermarks(session, HOT_SOURCES if tier == HOT else HOT_SOURCES + BULK_SOURCES)
        before = {} if fresh else watermark_read(file)
        kept = (
            tier == BOTH
            and tier_path(file, BULK).is_file()
            and bulk_unchanged(before, marks, digest)
        )
        effective = HOT if kept else tier
        if kept:
            out.print(
                f"The bulk tier's sources are as at build {before.get('build')}:"
                f" {tier_path(file, BULK)} is kept; building the hot tier only.",
                markup=False,
            )
        identity = build_id(marks, digest, tier)
        try:
            report = build(
                session,
                file,
                payloads=payloads,
                store_sql=store_sql,
                now=datetime.now(UTC),
                hot_only=effective == HOT,
                build_id=identity,
                on_kind=lambda kind, count, seconds: out.print(
                    f"  {kind}: {count:,} read and merged in {seconds:,.1f} s", markup=False
                ),
            )
        except BuildFailed as fault:
            err.print(str(fault), markup=False)
            raise typer.Exit(code=1) from None
    # A run left pending was made for the files this build replaces: the build holds
    # what it carried, so it is never settled against the new store.
    for stale in remove_pending(file, bulk_too=effective != HOT):
        out.print(f"Removed {stale}: a run left pending before this build.", markup=False)
    hot = {**report.hot_state, BUILD_KEY: report.build_id}
    write_state(state_path(file), hot)
    # The same, kept as the build left it: the start of a push state for any other store.
    write_state(base_state_path(file), hot)
    if effective != HOT:
        write_state(bulk_state_path(file), {**report.state, BUILD_KEY: report.build_id})
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
    for written in split_build(file, payloads, effective, hot_only=effective == HOT):
        objects = payloads / written.stem.rsplit(".", 1)[-1]
        out.print(
            f"Wrote {written} ({_size(written.stat().st_size)})"
            + (f", its payload objects in {objects}." if tier != ALL else "."),
            markup=False,
        )
    bulk_build = (build_id_of(tier_path(file, BULK)) or "") if kept else report.build_id
    watermark_write(file, marks, digest, report.build_id, bulk_build)
    if kept:
        out.print(
            f"Bulk build {bulk_build}: the hot build {report.build_id} keeps it as its bulk file.",
            markup=False,
        )
    out.print(f"Done in {time.monotonic() - started:,.0f} s.", markup=False)


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


def _commit() -> str:
    try:
        found = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=STORE_SQL
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    return found


def _client(url: str, token: str) -> httpx.Client:
    return httpx.Client(
        transport=RetryOnBusy(),
        base_url=url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        timeout=120,
    )


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
    # The store's build, its database and its address, against the state's: a state of
    # another store, or of this one before a reload, would skip what the store lacks.
    try:
        check_target(held, url, state)
        with _client(url, token) as client:
            progress, took_since = check_store(client, held)
    except PushFailed as fault:
        err.print(str(fault), markup=False)
        raise typer.Exit(code=1) from None
    if progress is None:
        out.print("The store gave no progress: its build is not compared.", markup=False)
    elif store_build(progress) is None:
        out.print("The store gives no build id: the build is not compared.", markup=False)
    if took_since and not report_only:
        write_state(state, held)
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
    with _client(url, token) as client:
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
                pending=pending_path(state),
                belongs={"build": held.get(BUILD_KEY, ""), "target": url},
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
            file,
            records,
            held,
            delta=delta,
            store_sql=store_sql,
            now=datetime.now(UTC),
            save_state=lambda now: write_state(state, now),
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
        transport=RetryOnBusy(),
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
    """Count the people the payloads of store files and their objects on disk name, and
    the papers' abstracts they hold (docs/adr/0011; a paper's byline is not counted).
    Exits with 1 when any is found."""
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
    out.print("No person is named and no abstract is held in these files.", markup=False)


@backfill_app.command("strip-paper-abstracts")
def strip_paper_abstracts_command(
    apply: Annotated[
        bool, typer.Option("--apply", help="Write the records without them; else only count.")
    ] = False,
) -> None:
    """Count the papers' abstracts in every stored payload that is not a registry study (a
    follow-up paper's record, a retraction notice, a paper's or a trial paper's record)
    and, with --apply, store each without its abstract. The byline stays (docs/adr/0011).
    Running it again changes nothing."""
    engine = make_engine(settings_or_exit().database_url)
    with Session(engine) as session:
        if not apply:
            read_only(session)
        report = strip_abstracts(session, apply=apply)
        session.rollback()
    for table, source in sorted(report.rows):
        out.print(
            f"{table} {source}: {report.rows[(table, source)]:,} records,"
            f" {report.changed[(table, source)]:,} holding an abstract"
            + (" (written without)" if apply else " (counted only; --apply writes)"),
            markup=False,
        )
        for (t, s, key), count in sorted(report.before.items()):
            if (t, s) == (table, source):
                out.print(
                    f"  {key}: {count:,} before, {report.after[(t, s, key)]:,} after", markup=False
                )
    out.print(f'Prove it: psql "$DATABASE_URL" -f {ABSTRACTS_PROOF_SQL}', markup=False)


@store_app.command("drop-pending")
def drop_pending_command(
    state: Annotated[
        Path, typer.Option("--state", envvar="STORE_PUSH_STATE", help="The push state.")
    ],
    url: Annotated[
        str, typer.Option("--url", envvar="INGEST_URL", help="The ingest service's address.")
    ] = "",
) -> None:
    """Set aside a run left pending that the store undid for a constraint: the same
    records can never merge, so the next push forms them again. Refused unless its push
    marked it undone, the token may write the run's writer (GET /progress `writers`), and
    the store does not hold it merged. The file is moved aside, not deleted."""
    pending = pending_path(state)
    held = read_pending(pending)
    if held is None:
        err.print(f"No run is pending beside {state}.")
        raise typer.Exit(code=1)
    run = held[0]
    undone = undone_of(pending)
    if undone is None:
        err.print(
            f"Run {run} in {pending} was not undone by a constraint: push again, which"
            " settles it first."
        )
        raise typer.Exit(code=1)
    token = os.environ.get("INGEST_TOKEN", "")
    if not (url and token):
        err.print("drop-pending asks the store about the run: set INGEST_URL and INGEST_TOKEN.")
        raise typer.Exit(code=1)
    writer = run.split("-", 1)[0]
    with _client(url, token) as client:
        # The store answers "no such run" both for a run it does not hold and for one this
        # token may not see; only a token that may write the run's writer can tell them apart.
        progress = client.get("/progress")
        writers = progress.json().get("writers") if progress.status_code == 200 else None
        if not isinstance(writers, list) or writer not in writers:
            err.print(
                f"Run {run} is a {writer} run; the store does not say this token may write"
                f" {writer} runs ({', '.join(map(str, writers or [])) or 'it names none'}), so"
                f" its answer about the run cannot be trusted. Use a token of the {writer}"
                " writer."
            )
            raise typer.Exit(code=1)
        answer = client.get(f"/runs/{run}")
        status = answer.json().get("status") if answer.status_code == 200 else None
        if answer.status_code not in (200, 404):
            err.print(f"The store did not say what run {run} is: {answer.status_code}.")
            raise typer.Exit(code=1)
        if status == "merged":
            err.print(
                f"The store holds run {run} merged: push again, which settles it and takes"
                " its records as handed over."
            )
            raise typer.Exit(code=1)
        if status == "registered":
            # Still open at the store, with nothing merged: dropped there too.
            client.delete(f"/runs/{run}")
    aside = pending.with_name(
        f"{pending.name}.set-aside-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    pending.replace(aside)
    out.print(
        f"Set run {run} aside ({undone}): {aside}. The next push forms its records again.",
        markup=False,
    )


@store_app.command("fresh-state")
def fresh_state_command(
    file: Annotated[Path, typer.Argument(help="The store file the store was loaded from.")],
    url: Annotated[str, typer.Option("--url", help="The store's ingest service address.")],
    out_file: Annotated[Path, typer.Option("--out", help="The new push state file.")],
) -> None:
    """Start the push state of a store loaded from this build: what its hot file holds,
    named for that store. A push state names one store and is refused for any other, so
    preview and production, or a store loaded again, each get their own. With
    INGEST_TOKEN set, a store that says it was loaded from another build is refused."""
    base = base_state_path(file)
    if not base.is_file():
        err.print(f"No {base}: build the store again, which writes it.")
        raise typer.Exit(code=1)
    if out_file.exists():
        err.print(f"{out_file} exists: name another file, or delete it if it is stale.")
        raise typer.Exit(code=1)
    state = read_state(base)
    token = os.environ.get("INGEST_TOKEN", "")
    if token:
        with _client(url, token) as client:
            try:
                progress, _ = check_store(client, state)
            except PushFailed as fault:
                err.print(str(fault), markup=False)
                raise typer.Exit(code=1) from None
        held = store_build(progress)
        if held is None:
            out.print("The store gives no build id: the build is not compared.", markup=False)
    else:
        out.print("INGEST_TOKEN is not set: the store's build is not compared.", markup=False)
    state[TARGET_KEY] = target_of(url)
    write_state(out_file, state)
    out.print(
        f"Wrote {out_file}: the push state of {target_of(url)}, as build"
        f" {state.get(BUILD_KEY, '?')} left it.",
        markup=False,
    )
