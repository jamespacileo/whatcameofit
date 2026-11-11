"""The prepare command: everything a claim needs before review, for many claims at once."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

import typer

from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.prepare import ClaimPlan, plan_claims, steps_for


def run_step(arguments: list[str]) -> tuple[bool, str]:
    """Run one command of this program on its own, so each has its own transaction and a
    failure stays with its claim. Returns whether it succeeded and its last line."""
    done = subprocess.run(
        [sys.argv[0], *arguments], capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    lines = [line.strip() for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return done.returncode == 0, lines[-1] if lines else ""


def _prepare(plan: ClaimPlan) -> list[str]:
    started = time.monotonic()
    report: list[str] = []
    for step in steps_for(plan):
        succeeded, said = run_step(step)
        name = "read" if step[0] == "extract" else step[0]
        report.append(f"  {name}: {said}" if succeeded else f"  {name} failed: {said}")
    return [f"{plan.slug} ({time.monotonic() - started:.0f}s)", *report]


def prepare_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    pending: Annotated[
        bool, typer.Option("--pending", help="Every claim that awaits review.")
    ] = False,
    workers: Annotated[
        int, typer.Option(min=1, max=8, help="How many claims to work on at once.")
    ] = 4,
) -> None:
    """Get claims ready for review: read their unread articles, search the registries,
    and read the registries for matches already approved.

    Claims are worked on side by side. A step that fails is reported and the claim's
    other steps still run. Nothing is approved here.
    """
    if not slugs and not pending:
        err.print("Name the claims to prepare, or use --pending for every claim awaiting review.")
        raise typer.Exit(code=1)
    with entry_session() as session:
        plans = plan_claims(session, slugs or None)
    if not plans:
        out.print("No claim awaits review.")
        return
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for report in pool.map(_prepare, plans):
            for line in report:
                out.print(line, markup=False)
