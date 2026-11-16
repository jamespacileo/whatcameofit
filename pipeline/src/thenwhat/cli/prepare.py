"""The prepare command: everything a claim needs before review, for many claims at once."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Annotated

import typer

from thenwhat.claims.entry import find_claim
from thenwhat.claims.mesh_areas import suggestion_line
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import ReviewState
from thenwhat.measure import spans as measure
from thenwhat.prepare import (
    NOT_NEEDED_TO_DECIDE,
    ClaimPlan,
    claim_sharing_its_substance,
    decide_prepared_lead_claim,
    plan_claims,
    steps_for,
)


def run_step(arguments: list[str]) -> tuple[bool, str]:
    """Run one command of this program on its own, so each has its own transaction and a
    failure stays with its claim. Returns whether it succeeded and its last line."""
    done = subprocess.run(
        [sys.argv[0], *arguments], capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    lines = [line.strip() for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return done.returncode == 0, lines[-1] if lines else ""


def _prepare(plan: ClaimPlan) -> list[str]:
    with measure.measured("prepare", trace=measure.claim_trace(plan.slug)) as span:
        return _prepare_measured(plan, span)


def _prepare_measured(plan: ClaimPlan, span: measure.Running) -> list[str]:
    started = time.monotonic()
    report: list[str] = []
    every_step_succeeded = True
    for step in steps_for(plan):
        step_started = time.monotonic()
        succeeded, said = run_step(step)
        if step[0] not in NOT_NEEDED_TO_DECIDE:
            every_step_succeeded = every_step_succeeded and succeeded
        name = "read" if step[0] == "extract" else step[0]
        # The step ran as its own process and measured itself: its time is its own.
        span.add_inner(time.monotonic() - step_started)
        took = f"{time.monotonic() - step_started:.0f}s"
        report.append(
            f"  {name} ({took}): {said}" if succeeded else f"  {name} failed ({took}): {said}"
        )
    with entry_session() as session:
        claim = find_claim(session, plan.slug)
        if claim is not None:
            report.append(f"  {suggestion_line(session, claim)}")
        # A claim a link lead's read drafted waits for this: its registries searched and
        # read. Only then is it decided by the rule for drafts, so it is never published
        # with a status no search stands behind. A failed step leaves it waiting.
        if every_step_succeeded and settings_or_exit().approve_drafts_by_rule:
            decided = decide_prepared_lead_claim(session, plan.slug, now=datetime.now(UTC))
            if decided is ReviewState.APPROVED:
                report.append(
                    "  approved by rule, now that its registries have been searched;"
                    " held off the site until audited"
                )
            elif decided is ReviewState.REJECTED:
                claim = find_claim(session, plan.slug)
                twin = claim_sharing_its_substance(session, claim) if claim else None
                report.append(
                    f"  rejected by rule: {twin} stands for the same substance and condition"
                    if twin
                    else "  rejected by rule: its intervention is a description, not a name"
                )
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
    read the registries for matches already approved, read the stored trial records
    into record readings, and propose subject terms, which background cards come from.

    Claims are worked on side by side. A step that fails is reported and the claim's
    other steps still run. Nothing is approved here beyond what those steps approve by
    rule, with one exception: a claim that a link lead's read drafted is decided by the
    rule for drafts once every step for it has succeeded, the terms step aside.
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
