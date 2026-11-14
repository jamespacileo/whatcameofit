"""The terms command: subject terms, the intervention kind and named genes for claims."""

from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entry import claim_by_slug
from thenwhat.cli import resolve
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.decide.steps import NONE_OF_THESE
from thenwhat.domain import ReviewState, TermFit
from thenwhat.sources.mesh import Mesh
from thenwhat.sources.opentargets import OpenTargets
from thenwhat.terms.service import (
    Genes,
    KindTermMissing,
    Vocabulary,
    claims_without_terms,
    link_kind,
    link_targets,
    link_terms,
    published_claims,
)


def make_vocabulary(session: Session) -> Vocabulary:
    return Mesh(session, contact_email=settings_or_exit().contact_email)


def make_genes(session: Session) -> Genes:
    return OpenTargets(session, contact_email=settings_or_exit().contact_email)


def _state(state: ReviewState) -> str:
    return "pending review" if state is ReviewState.PENDING else f"{state.value} by rule"


def terms_command(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    missing: Annotated[
        bool,
        typer.Option("--missing", help="Every published claim with no candidate subject term."),
    ] = False,
    every: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Every published claim. New candidates are gathered and scored; ones"
            " that already have a score are left as they are.",
        ),
    ] = False,
) -> None:
    """Propose subject terms, the intervention kind and named genes for claims.

    Subject terms: candidates are gathered by rule, from the terms the registry files
    the claim's approved trials under and from vocabulary terms whose label or entry
    term equals one of the claim's names. Each is scored for the claim and read as
    exact or broader.

    Intervention kind: for an intervention with no approved exact term, its kind is
    chosen from a fixed list (drug, antibody, device, surgical procedure and so on) or
    none of them, once per claim. The kind's vocabulary term becomes a kind link.

    Named genes: a word of the intervention's names that equals a human gene's symbol,
    or a listed synonym of it, makes that gene a candidate target, checked for the
    claim.

    A rule approves a link scored high and rejects one scored near zero; the rest wait
    in `review list`. Reject a wrong approved one with `review reject term ID`. Nothing
    here changes a claim's status.
    """
    if sum([bool(slugs), missing, every]) != 1:
        err.print(
            "Name the claims, or use --missing for every published claim without a"
            " subject term, or --all for every published claim. Give one of the three."
        )
        raise typer.Exit(code=1)
    settings = settings_or_exit()
    failed = 0
    with entry_session() as session:
        if slugs:
            claims = [claim_by_slug(session, slug) for slug in slugs]
        elif every:
            claims = published_claims(session)
        else:
            claims = claims_without_terms(session)
        if not claims:
            out.print(
                "There is no published claim."
                if every
                else "Every published claim has a candidate subject term."
            )
            return
        vocabulary = make_vocabulary(session)
        genes = make_genes(session)
        backend = resolve.make_backend(session)
        accept, reject = settings.match_accept_above, settings.match_reject_below
        for claim in claims:
            now = datetime.now(UTC)
            run = link_terms(
                session,
                claim,
                vocabulary=vocabulary,
                backend=backend,
                now=now,
                limit=settings.term_candidates_max,
                accept_above=accept,
                reject_below=reject,
            )
            try:
                kind = link_kind(
                    session,
                    claim,
                    vocabulary=vocabulary,
                    backend=backend,
                    now=now,
                    accept_above=accept,
                    reject_below=reject,
                )
            except KindTermMissing as error:
                err.print(str(error), markup=False)
                raise typer.Exit(code=1) from error
            targets = link_targets(
                session,
                claim,
                genes=genes,
                backend=backend,
                now=now,
                limit=settings.target_candidates_max,
                accept_above=accept,
                reject_below=reject,
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
            for name in run.unresolved:
                out.print(
                    f"  '{name}' equals an entry term whose record the vocabulary did not"
                    " give. It made no candidate; a later run asks again.",
                    markup=False,
                )

            if kind.failed:
                kind_line = "not answered"
            elif not kind.asked:
                kind_line = "not asked"
            elif kind.chosen == NONE_OF_THESE:
                kind_line = "none of these"
            elif kind.link is None:
                kind_line = f"{kind.chosen}, whose term is already a link for this claim"
            else:
                assert kind.link.score is not None
                kind_line = (
                    f"{kind.chosen} {kind.link.score:.2f}, {_state(kind.link.review_state)}"
                    f" ({kind.link.external_id} {kind.link.label})"
                )
            genes_approved = [t for t in targets.scored if t.review_state is ReviewState.APPROVED]
            genes_rejected = sum(t.review_state is ReviewState.REJECTED for t in targets.scored)
            out.print(
                f"  Kind: {kind_line}. Named genes: {targets.gathered} candidate(s),"
                f" {len(targets.added)} new. Approved by rule: {len(genes_approved)}."
                f" Rejected by rule: {genes_rejected}."
                f" Pending review: {len(targets.scored) - len(genes_approved) - genes_rejected}.",
                markup=False,
            )
            for term in genes_approved:
                assert term.score is not None
                out.print(
                    f"  approved {term.score:.2f}  target  {term.external_id}  {term.label}",
                    markup=False,
                )

            unscored = len(run.unscored) + len(targets.unscored) + int(kind.failed)
            if unscored:
                failed += unscored
                err.print(
                    f"  {unscored} could not be scored and stay without a score."
                    " Run this again for them.",
                    markup=False,
                )
    if failed:
        # Raised once the session has committed what was stored and logged.
        raise typer.Exit(code=1)
