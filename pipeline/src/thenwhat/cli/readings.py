"""The readings command: record readings for the trials of claims."""

from typing import Annotated

import typer

from thenwhat.claims.entry import claim_by_slug
from thenwhat.claimsteps.evidence import ClaimReadings
from thenwhat.cli.claim_steps import outcome_line, run_for_claims, unfinished
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.readings.service import ReadingsRun, published_claims


def readings_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    every: Annotated[bool, typer.Option("--all", help="Every published claim.")] = False,
) -> None:
    """Have the configured model read the stored registry records of the claims' trials,
    now: the step `claim_readings` of `thenwhat prepare`.

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
        claims = [claim_by_slug(session, slug) for slug in slugs or []]
        if every:
            claims += [claim for claim in published_claims(session) if claim not in claims]
        named = {claim.id: claim.slug for claim in claims}
    [step] = run_for_claims(list(named), [ClaimReadings.name], alone=True)
    run = ReadingsRun()
    for claim_id in named:
        found: ReadingsRun | None = step.results.get(claim_id)
        if found is not None:
            run.read += found.read
            run.unchanged += found.unchanged
            run.stored += found.stored
            run.refused.update(found.refused)
    out.print(summary_line(run), markup=False)
    with entry_session() as session:
        left = False
        for claim_id, slug in named.items():
            if unfinished(session, [step], claim_id):
                left = True
                found = step.results.get(claim_id)
                if found is not None and found.unread:
                    err.print(f"{slug}: Not read: {', '.join(found.unread)}.", markup=False)
                else:
                    err.print(outcome_line(session, step, claim_id, slug) or slug, markup=False)
    if left:
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
