"""The measure command, and starting to measure when a command runs.
Behavior: openspec processing-metrics."""

import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from thenwhat.cli.console import err, out
from thenwhat.cli.session import open_session, settings_or_exit
from thenwhat.config import Settings, load_settings
from thenwhat.llm.ledger import spent_this_month
from thenwhat.measure import spans
from thenwhat.measure.files import FileWriter, remove_old
from thenwhat.measure.live import LiveView, Stored, lines_of, paused_sources, watch
from thenwhat.measure.report import Report, gather
from thenwhat.measure.totals import roll

KEEP_NOT_SET = (
    "MEASURE_DIR is set, so MEASURE_KEEP_DAYS and MEASURE_LOOKUP_KEEP_DAYS must be set"
    " too: how many days single-step measurements are kept. Nothing is being measured."
)


def keep_days_of(settings: Settings) -> tuple[int, int] | None:
    """The two numbers of days measurements are kept, or None when either is missing."""
    if settings.measure_keep_days is None or settings.measure_lookup_keep_days is None:
        return None
    return settings.measure_keep_days, settings.measure_lookup_keep_days


def start_measuring() -> None:
    """Record this command's steps when a folder for measurements is configured. A
    command must never fail because of measuring, so a missing setting is said once and
    the command goes on unmeasured."""
    try:
        settings = load_settings()
    except ValidationError:
        return
    if settings.measure_dir is None:
        spans.use(None)
        return
    if keep_days_of(settings) is None:
        err.print(KEEP_NOT_SET)
        spans.use(None)
        return
    writer = settings.measure_writer
    spans.use(spans.Recorder(out=FileWriter(settings.measure_dir, writer=writer), writer=writer))


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def _lines(report: Report) -> list[str]:
    lines = [
        f"Measurements, {report.first} to {report.last}",
        f"  time working {_duration(report.total_ran_seconds)},"
        f" waiting {_duration(report.total_waited_seconds)},"
        f" model cost ${report.total_cost_usd:.4f}",
        "",
        "By step and writer (records; working; waiting; cost; share of time, of cost;"
        " answered from stored work):",
    ]
    for line in report.steps:
        ended = ", ".join(f"{count} {name}" for name, count in sorted(line.outcomes.items()))
        lines.append(
            f"  {line.step} [{line.writer}]: {line.records} records ({ended});"
            f" {_duration(line.ran_seconds)}; {_duration(line.waited_seconds)};"
            f" ${line.cost_usd:.4f}; {line.share_of_time:.0%}, {line.share_of_cost:.0%};"
            f" {line.reused_share:.0%}"
        )
    if report.waited_on:
        lines += ["", "Waited on, longest first:"]
        lines += [f"  {cause}: {_duration(seconds)}" for cause, seconds in report.waited_on]
    if report.requests:
        lines += ["", "Requests sent:"]
        lines += [f"  {source}: {count}" for source, count in report.requests]
    if report.not_written:
        lines += ["", "Measurements that could not be written:"]
        lines += [
            f"  {gap.measurements:,} from {gap.since:%Y-%m-%d %H:%M} to {gap.until:%H:%M} UTC"
            f" ({gap.lines:,} lines in all)"
            for gap in report.not_written
        ]
    lines.append("")
    if report.claims is None:
        lines.append("No claim published in this range has measurements.")
    else:
        took = report.claims
        lines += [
            f"Published claims with measurements: {took.claims}",
            f"  cost of a claim: median ${took.median_cost_usd:.4f},"
            f" most ${took.worst_cost_usd:.4f}",
            f"  first seen to published: median {_duration(took.median_elapsed_seconds)},"
            f" longest {_duration(took.worst_elapsed_seconds)}",
            f"  of which working {_duration(took.median_ran_seconds)}"
            f" and waiting {_duration(took.median_waited_seconds)} at the median",
        ]
    return lines


def _watch(folder: Path, settings: Settings, *, once: bool) -> None:
    """Draw the live view until stopped, or once."""

    def stored(moment: datetime) -> Stored:
        with open_session() as session:
            return Stored(paused_sources(session, moment), spent_this_month(session, moment))

    def draw(view: LiveView) -> None:
        if not once and out.is_terminal:
            out.clear()
        for line in lines_of(view, folder):
            out.print(line, markup=False)

    try:
        watch(
            folder,
            stored=stored,
            ceiling_usd=settings.llm_monthly_budget_usd,
            draw=draw,
            now=lambda: datetime.now(UTC),
            sleep=time.sleep,
            once=once,
        )
    except KeyboardInterrupt:
        return


def measure_command(
    days: Annotated[int, typer.Option(min=1, help="How many days back, today included.")] = 7,
    since: Annotated[
        str | None, typer.Option(help="First day of the range, as YYYY-MM-DD.")
    ] = None,
    until: Annotated[str | None, typer.Option(help="Last day of the range, as YYYY-MM-DD.")] = None,
    live: Annotated[
        bool,
        typer.Option(
            "--live",
            help="Watch the runs at work: each step in the last 1, 5 and 15 minutes, drawn"
            " again every five seconds until Ctrl-C. Changes nothing and asks no source.",
        ),
    ] = False,
    once: Annotated[
        bool, typer.Option("--once", help="With --live: draw the view once and exit.")
    ] = False,
) -> None:
    """Report time, waiting and cost by step, and what a published claim took.

    Finished days are first added into the totals that are kept, and single-step
    measurements past their number of days are removed. Nothing is sent anywhere.
    With --live, nothing is added up or removed: the day's files are only read.
    """
    settings = settings_or_exit()
    if once and not live:
        err.print("--once goes with --live.", markup=False)
        raise typer.Exit(code=1)
    if live:
        if since is not None or until is not None:
            err.print("--live shows the last fifteen minutes: it takes no days.", markup=False)
            raise typer.Exit(code=1)
        if settings.measure_dir is None:
            err.print("MEASURE_DIR is not set, so there is nothing to watch.", markup=False)
            raise typer.Exit(code=1)
        _watch(settings.measure_dir, settings, once=once)
        return
    today = datetime.now(UTC).date()
    try:
        last = date.fromisoformat(until) if until else today
        first = date.fromisoformat(since) if since else last - timedelta(days=days - 1)
    except ValueError:
        err.print("Give days as YYYY-MM-DD.")
        raise typer.Exit(code=1) from None
    if first > last:
        err.print("The range ends before it begins.")
        raise typer.Exit(code=1)
    folder = settings.measure_dir
    keep = keep_days_of(settings)
    with open_session() as session:
        if folder is not None and keep is not None:
            # Totals first, so nothing is removed before it has been added up.
            roll(session, folder, today=today, now=datetime.now(UTC))
            remove_old(folder, today=today, keep_days=keep[0], lookup_keep_days=keep[1])
        report = gather(session, folder, first, last)
    if report.empty:
        why = " MEASURE_DIR is not set, so nothing is being measured." if folder is None else ""
        out.print(f"No measurements from {first} to {last}.{why}", markup=False)
        return
    for line in _lines(report):
        out.print(line, markup=False)
