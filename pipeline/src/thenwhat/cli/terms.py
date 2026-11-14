"""The terms command: subject terms for claims."""

from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import claim_by_slug
from thenwhat.cli import resolve
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.domain import ReviewState, TermFit
from thenwhat.sources.mesh import Mesh
from thenwhat.terms.service import Vocabulary, claims_without_terms, link_terms


def make_vocabulary(session: Session) -> Vocabulary:
    return Mesh(session, contact_email=settings_or_exit().contact_email)


def terms_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    missing: Annotated[
        bool,
        typer.Option("--missing", help="Every published claim with no candidate subject term."),
    ] = False,
) -> None:
    """Propose subject terms for claims: for each claim's condition and intervention.

    Candidates are gathered by rule: the terms the registry files the claim's approved
    trials under, and vocabulary terms whose label equals one of the claim's names. Each
    is scored for the claim and read as exact or broader. A rule approves one scored
    high and rejects one scored near zero; the rest wait in `review list`. Reject a wrong
    approved one with `review reject term ID`. Nothing here changes a claim's status.
    """
    if not slugs and not missing:
        err.print("Name the claims, or use --missing for every claim without a subject term.")
        raise typer.Exit(code=1)
    settings = settings_or_exit()
    failed = 0
    with entry_session() as session:
        if slugs:
            claims = [claim_by_slug(session, slug) for slug in slugs]
        else:
            claims = claims_without_terms(session)
        if not claims:
            out.print("Every published claim has a candidate subject term.")
            return
        vocabulary = make_vocabulary(session)
        backend = resolve.make_backend(session)
        for claim in claims:
            run = link_terms(
                session,
                claim,
                vocabulary=vocabulary,
                backend=backend,
                now=datetime.now(UTC),
                limit=settings.term_candidates_max,
                accept_above=settings.match_accept_above,
                reject_below=settings.match_reject_below,
            )
            approved = [t for t in run.scored if t.review_state is ReviewState.APPROVED]
            exact = sum(term.fit is TermFit.EXACT for term in approved)
            rejected = sum(t.review_state is ReviewState.REJECTED for t in run.scored)
            pending = len(run.scored) - len(approved) - rejected
            out.print(
                f"{claim.slug}: {run.gathered} candidate subject term(s), {len(run.added)} new."
                f" Approved by rule: {exact} exact, {len(approved) - exact} broader."
                f" Rejected by rule: {rejected}. Pending review: {pending}.",
                markup=False,
            )
            for term in approved:
                assert term.score is not None and term.fit is not None
                out.print(
                    f"  approved {term.score:.2f}  {term.role.value}  {term.fit.value}"
                    f"  {term.external_id}  {term.label}",
                    markup=False,
                )
            if run.unscored:
                failed += len(run.unscored)
                err.print(
                    f"  {len(run.unscored)} could not be scored and stay without a score."
                    " Run this again for them.",
                    markup=False,
                )
    if failed:
        # Raised once the session has committed what was stored and logged.
        raise typer.Exit(code=1)
