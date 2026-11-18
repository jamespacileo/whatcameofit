"""The prepare command: every part of a claim's preparation that is due, for many claims
at once. Behavior: openspec claim-extraction, "Preparing many claims"."""

from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy import ColumnElement, and_, select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import claim_by_slug
from thenwhat.claimsteps.decide import ClaimDecide
from thenwhat.claimsteps.inputs import notice_changes
from thenwhat.claimsteps.run import (
    StepRun,
    claim_steps,
    handled_since,
    left_by,
    never_searched,
    search_due,
)
from thenwhat.claimsteps.step import named, prepared
from thenwhat.cli.claim_steps import run_steps
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.clinical.service import prepared_line, suggestion_line
from thenwhat.db.models import Claim
from thenwhat.domain import DraftedFrom, ReviewState, WorkOutcome
from thenwhat.prepare import claim_sharing_its_substance, registry_draft_matches

OUTCOME_WORDS = {
    WorkOutcome.FAILED: "failed",
    WorkOutcome.LATER: "put off",
    WorkOutcome.NEEDS_FIX: "needs a fix",
}


def step_line(run: StepRun) -> str:
    """How many claims a step did, put off, left needing a fix and failed, how many are
    still due, and how long it took."""
    report = run.report
    return (
        f"{run.step.name}: {report.done:,} done, {report.nothing_found:,} found nothing,"
        f" {report.later:,} put off, {report.needs_fix:,} need a fix,"
        f" {report.failed:,} failed; {report.remaining_due:,} still due, in {run.seconds:.0f}s."
    )


def prepare_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    pending: Annotated[
        bool,
        typer.Option(
            "--pending",
            help="Every claim that awaits review, and every approved claim not archived"
            " with a part of its preparation due.",
        ),
    ] = False,
    due: Annotated[
        bool,
        typer.Option(
            "--due",
            help="Every claim whose registry search is due again, after a merge or a"
            " rename or because it never finished.",
        ),
    ] = False,
    workers: Annotated[
        int, typer.Option(min=1, max=8, help="How many claims to work on at once.")
    ] = 4,
) -> None:
    """Get claims ready: read their unread articles, look up their substance, search the
    trial registry, search for papers, look up the records their articles' pages name,
    fetch their approved records, read their trial records and propose their terms.

    Each part is a step of the work ledger, done once for a claim's current input: a run
    does only the parts that are due, and a run stopped anywhere is started again
    without redoing what finished. A part whose source failed is put off and comes back
    by itself; a source that cannot be asked at all stops that part, and the others
    still run. A claim a link lead's read drafted is decided by the rule for drafts once
    its articles are read, its substance looked up, its registry searched and its
    approved records fetched. It does not wait for its papers, readings or terms, which
    stay due until they finish. Nothing else is approved here beyond what the steps
    approve by rule.
    """
    if not slugs and not pending and not due:
        err.print(
            "Name the claims to prepare, or use --pending for every claim awaiting review"
            " and every published claim with a part due, or --due for every claim whose"
            " registry search is due."
        )
        raise typer.Exit(code=1)
    settings = settings_or_exit()
    claims: ColumnElement[bool]
    with entry_session() as session:
        if slugs:
            claims = named([claim_by_slug(session, slug).id for slug in slugs])
        elif pending:
            claims = prepared()
        else:
            steps = claim_steps(settings)
            notice_changes(session, steps)
            ids = search_due(session, steps, settings.backfill_attempt_limit)
            if not ids:
                out.print("No claim's registry search is due.")
                return
            claims = and_(prepared(), named(ids))
    started = datetime.now(UTC)
    steps = claim_steps(settings, claims=claims)
    for run in run_steps(steps, workers=workers):
        out.print(step_line(run), markup=False)
        if run.report.stopped:
            out.print(f"  stopped: {run.report.stopped}", markup=False)
    with entry_session() as session:
        for left in left_by(session, steps, started):
            until = (
                f" until {left.not_before:%Y-%m-%d %H:%M} UTC"
                if left.outcome is WorkOutcome.LATER and left.not_before
                else ""
            )
            out.print(
                f"{left.slug}: {left.step} {OUTCOME_WORDS[left.outcome]}{until}: {left.said}",
                markup=False,
            )
        for step in steps:
            if isinstance(step, ClaimDecide):
                _say_decided(session, step)
        _say_pending_registry_drafts(session, claims)
        handled = handled_since(session, steps, started)
        if handled:
            out.print(prepared_line(session, handled), markup=False)
        never = never_searched(session, claims)
        if never:
            out.print(
                f"Never searched: {len(never):,} claim(s) have no record of a registry"
                f" search: {', '.join(never)}.",
                markup=False,
            )


def _say_decided(session: Session, step: ClaimDecide) -> None:
    """What the rule for drafts decided for each claim, and why."""
    for claim_id, decided in sorted(step.results.items()):
        claim = session.get(Claim, claim_id)
        if claim is None:
            continue
        if decided is ReviewState.APPROVED:
            said = (
                "approved by rule, now that its registries have been searched; held off the"
                " site until audited"
            )
        else:
            twin = claim_sharing_its_substance(session, claim)
            said = (
                f"rejected by rule: {twin} stands for the same substance and condition"
                if twin
                else "rejected by rule: its intervention is a description, not a name"
            )
        out.print(f"{claim.slug}: {said}. {suggestion_line(session, claim)}", markup=False)


def _say_pending_registry_drafts(session: Session, scope: ColumnElement[bool]) -> None:
    for claim in session.scalars(
        select(Claim)
        .where(
            scope,
            Claim.drafted_from == DraftedFrom.REGISTRY,
            Claim.review_state == ReviewState.PENDING,
        )
        .order_by(Claim.slug)
    ):
        matches = registry_draft_matches(session, claim)
        details = []
        for identifier in claim.drafting_trial_ids:
            match = matches.get(identifier)
            if match is None:
                details.append(f"{identifier} has no score")
            else:
                reason = f" ({', '.join(match.reasons)})" if match.reasons else ""
                details.append(f"{identifier} {match.score:.2f} {match.review_state.value}{reason}")
        out.print(f"{claim.slug}: pending registry draft. {', '.join(details)}.", markup=False)
