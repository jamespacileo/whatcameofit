"""The readings command: record readings for the trials of claims."""

from datetime import UTC, datetime
from typing import Annotated

import typer

from thenwhat.claims.entry import claim_by_slug
from thenwhat.cli import extract
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.readings.service import ReadingsRun, published_claims, read_trials, trials_of


def readings_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    every: Annotated[bool, typer.Option("--all", help="Every published claim.")] = False,
) -> None:
    """Have the configured model read the stored registry records of the claims' trials.

    For each planned primary outcome the model gives how long it was followed, as a
    number with a unit, and what kind of measure it is, as a code, each with the words
    it read. A rule checks every reading against the stored record before it is kept: one
    whose words are not in the record, or whose number, unit or code does not hold, is
    not stored. A trial whose record and instructions have not changed is not read again.
    Readings change no status, no match score and no trial's facts. The run stops when
    the monthly spend ceiling is reached.
    """
    if not slugs and not every:
        err.print("Name the claims, or use --all for every published claim.")
        raise typer.Exit(code=1)

    with entry_session() as session:
        claims = [claim_by_slug(session, slug) for slug in slugs] if slugs else []
        if every:
            claims += [claim for claim in published_claims(session) if claim not in claims]
        trials = [trial for claim in claims for trial in trials_of(session, claim)]
        if not trials:
            out.print(
                "Record readings: no trial of the claims named has a stored registry record"
                " with a planned primary outcome."
            )
            return
        run = read_trials(
            session,
            extract.make_llm(session),
            trials,
            now=datetime.now(UTC),
            at_once=settings_or_exit().readings_at_once,
        )
        for trial_id, said in run.failed:
            err.print(f"{trial_id} was not read: {said}", markup=False)
        out.print(summary_line(run), markup=False)
        if run.stopped:
            err.print(
                f"{run.stopped} The run stopped. Not read: {', '.join(run.unread)}.",
                markup=False,
            )
    if run.failed or run.stopped:
        # Raised once the session has committed what was stored.
        raise typer.Exit(code=1)


def summary_line(run: ReadingsRun) -> str:
    """What became of the trials and their readings, for the operator."""
    refused = sum(run.refused.values())
    reasons = ", ".join(
        f"{reason.value.replace('_', ' ')}: {count}"
        for reason, count in sorted(run.refused.items())
    )
    return (
        f"Record readings: {len(run.read)} trial(s) read, {len(run.unchanged)} unchanged"
        f" and not read again, {len(run.stored)} reading(s) stored, {refused} refused by rule"
        + (f" ({reasons})" if reasons else "")
        + "."
    )
