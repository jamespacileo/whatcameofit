"""`thenwhat backfill runs`: a backfill from bulk files as a run in a folder, with no
database (openspec backfill-run-files, change file-based-backfill).

Named `runs` because `backfill run <step>` is the work ledger's command, which stays for
the registry-first route.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from thenwhat.backfill.run.folder import (
    device_name,
    mounted_folder,
    open_run,
    record_stage,
    start_run,
)
from thenwhat.backfill.run.load import LINKS, TALLY, LoadReport, load
from thenwhat.cli.backfill import backfill_app, refusals
from thenwhat.cli.console import err, out
from thenwhat.config import BackfillRunSettings

runs_app = typer.Typer(
    help="A backfill from bulk files, run in a folder of files: start, load.",
    no_args_is_help=True,
)
backfill_app.add_typer(runs_app, name="runs")


def run_settings() -> BackfillRunSettings:
    try:
        return BackfillRunSettings()
    except ValidationError as error:
        err.print(f"A setting is not valid: {error}", markup=False)
        raise typer.Exit(code=1) from None


@runs_app.command("start")
def start_command(
    platform: Annotated[str, typer.Argument(help="Link source: hackernews or reddit.")],
    files: Annotated[list[Path], typer.Argument(help="The bulk files the run reads.")],
) -> None:
    """Start a run over bulk files of one platform: make its folder under
    BACKFILL_RUNS_DIR and record its inputs. Reads no file's rows yet."""
    settings = run_settings()
    with refusals():
        runs_dir = mounted_folder(settings.backfill_runs_dir, "BACKFILL_RUNS_DIR")
        folder, record = start_run(
            runs_dir,
            platform,
            files,
            device=device_name(settings.work_device_name),
            communities=settings.chosen_subreddits(),
            now=datetime.now(UTC),
        )
    size = sum(item.size for item in record.inputs)
    out.print(
        f"Started run {record.run_id} over {len(record.inputs)} {platform} file(s), "
        f"{size:,} bytes, in {folder}.",
        markup=False,
    )
    out.print(f"Next: thenwhat backfill runs load {record.run_id} --dry-run", markup=False)


def _say(report: LoadReport) -> None:
    out.print(
        f"Read {report.read:,} posts: {report.shares:,} shares on listed outlets, "
        f"{report.addresses:,} distinct addresses, {report.quarantined:,} quarantined.",
        markup=False,
    )
    for reason, number in sorted(report.skipped.items()):
        out.print(f"  left out, {reason}: {number:,}", markup=False)


@runs_app.command("load")
def load_command(
    run: Annotated[str, typer.Argument(help="The run's identifier, as `runs start` gave it.")],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Report what a load would write; write only the tally."),
    ] = False,
) -> None:
    """Load a run's bulk files: keep the shares on listed outlets, tally the domains of
    the rest, and set aside rows that cannot be read. Sends no request."""
    settings = run_settings()
    with refusals():
        runs_dir = mounted_folder(settings.backfill_runs_dir, "BACKFILL_RUNS_DIR")
        folder, record = open_run(runs_dir, run)
        report = load(folder, record, error_budget=settings.load_error_budget, dry_run=dry_run)
        if not dry_run:
            record_stage(folder, "load", report.as_json())
    _say(report)
    if dry_run:
        out.print(f"Dry run: only {TALLY} was written.", markup=False)
    else:
        out.print(f"Wrote {LINKS} and {TALLY} in {folder}.", markup=False)
