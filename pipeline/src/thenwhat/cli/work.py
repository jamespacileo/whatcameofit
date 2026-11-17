"""Commands about how work runs, for any step: making records due again by the reason
they wait for. Behavior: openspec work-ledger, "Records are made due by step and reason".
"""

from typing import Annotated, Any

import typer

from thenwhat.cli import backfill
from thenwhat.cli.backfill import open_session, refusals
from thenwhat.cli.console import err, out
from thenwhat.cli.session import settings_or_exit
from thenwhat.measure import events
from thenwhat.work.ledger import requeue
from thenwhat.work.outcome import ReasonClass, UndeclaredReason, declared
from thenwhat.work.steps import find_step

work_app = typer.Typer(
    help="How work runs, for any step: make records due again.", no_args_is_help=True
)


def _value(text: str) -> Any:
    """A value as a reason carries it: a whole number as a number, anything else as
    written."""
    return int(text) if text.lstrip("-").isdigit() else text


def _values(where: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for condition in where:
        key, equals, value = condition.partition("=")
        if not equals or not key or not value:
            err.print(f"--where takes key=value, not '{condition}'.", markup=False)
            raise typer.Exit(code=1)
        values[key] = _value(value)
    return values


@work_app.command("requeue")
def requeue_command(
    step_name: Annotated[str, typer.Argument(metavar="STEP", help="The step's name.")],
    reason: Annotated[
        str | None,
        typer.Option("--reason", help="The code of the reason the records wait for."),
    ] = None,
    where: Annotated[
        list[str] | None,
        typer.Option(
            "--where",
            help="Only records whose reason carries this value, as key=value. Repeatable.",
        ),
    ] = None,
    failed: Annotated[
        bool,
        typer.Option("--failed", help="The records that failed as often as the limit allows."),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Count the records and change nothing.")
    ] = False,
) -> None:
    """Make due again the records of a step that wait for one reason.

    For a cause that has been put right: a page parser that now reads the date, an
    outlet that now serves the reader. Asks no source and no model. The records are
    worked on by the next run of the step.
    """
    settings = settings_or_exit()
    if (reason is None) == (not failed):
        err.print("Give --reason with a reason's code, or --failed. One of the two.", markup=False)
        raise typer.Exit(code=1)
    values = _values(where or [])
    if failed and values:
        err.print("--where narrows a reason; it cannot be given with --failed.", markup=False)
        raise typer.Exit(code=1)
    with refusals(), open_session() as session:
        # Looked up at call time, as the backfill's commands do, so that tests can stand
        # in their own steps.
        step = find_step(backfill.steps_for(settings), step_name)
        said = "that failed as often as the limit allows"
        if reason is not None:
            try:
                known = declared(step, reason)
            except UndeclaredReason as unknown:
                err.print(str(unknown), markup=False)
                raise typer.Exit(code=1) from None
            if known.kind is ReasonClass.FINAL and not values and not dry_run:
                # A final reason says the record holds nothing for the step. Making every
                # such record due is a version's job, not a requeue's.
                err.print(
                    f"'{reason}' is a final reason: its records are finished. Narrow it "
                    "with --where, or raise the step's version to work on all of them again.",
                    markup=False,
                )
                raise typer.Exit(code=1)
            said = f"for '{reason}'"
        record_ids = requeue(
            session,
            step,
            reason=reason,
            values=values,
            failed=failed,
            attempt_limit=settings.backfill_attempt_limit if failed else None,
            dry_run=dry_run,
        )
        made_due = getattr(step, "made_due", None)
        if made_due is not None and record_ids and not dry_run:
            # A step may keep something of its own about a record it finished, which
            # must go when the record is to be worked on again.
            made_due(session, record_ids)
    if not dry_run:
        events.made_due(step.name, reason or events.FAILED, len(record_ids))
    narrowed = "".join(f", {key}={value}" for key, value in values.items())
    noun = "record" if len(record_ids) == 1 else "records"
    one = len(record_ids) == 1
    waiting = said if failed else f"{'waits' if one else 'wait'} {said}"
    if dry_run:
        out.print(
            f"{len(record_ids):,} {noun} of {step.name} {waiting}{narrowed}. Nothing was changed.",
            markup=False,
        )
        return
    out.print(
        f"{len(record_ids):,} {noun} of {step.name} {'' if failed else 'that '}{waiting}"
        f"{narrowed} {'is' if one else 'are'} due again."
        f" Run `thenwhat backfill run {step.name}`.",
        markup=False,
    )
