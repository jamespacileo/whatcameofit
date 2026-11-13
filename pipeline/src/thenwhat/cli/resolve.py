"""Commands for a claim's entities and for proposing registry matches."""

from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_entity, add_synonym, set_origin_paper
from thenwhat.claims.entry import ClaimNotFound, EntryError, find_claim
from thenwhat.cli import extract
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.decide.core import Backend, DecisionFailed, UnknownBackend, backend_named
from thenwhat.decide.steps import has_stage_suggestion, suggest_evidence_stage
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.resolve.service import DoiLookup, TrialSearch, rescore_claim, resolve_claim
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref

entity_app = typer.Typer(help="Add entities, synonyms and the origin paper.", no_args_is_help=True)


def make_backend(session: Session) -> Backend:
    from thenwhat.llm.decisions import Decisions, DecisionsSettings

    settings = settings_or_exit()
    named = settings.llm_model or ""
    decisions = Decisions(
        session,
        DecisionsSettings(
            model=settings.decisions_model
            or (named.removeprefix("openai:") if named.startswith("openai:") else None),
            monthly_budget_usd=settings.llm_monthly_budget_usd,
            input_usd_per_mtok=settings.decisions_input_usd_per_mtok,
        ),
    )
    try:
        return backend_named(settings.decision_backend, extract.make_llm(session), decisions)
    except UnknownBackend as unknown:
        raise EntryError(str(unknown)) from None


def make_registries(session: Session) -> tuple[TrialSearch, DoiLookup]:
    contact = settings_or_exit().contact_email
    return (
        ClinicalTrials(session, contact_email=contact),
        Crossref(session, contact_email=contact),
    )


@entity_app.command("add")
def entity_add(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    type: Annotated[EntityType, typer.Option(help="paper, person, institution or company.")],
    name: Annotated[str, typer.Option(help="Name, or title for a paper.")],
    doi: Annotated[str | None, typer.Option(help="DOI, for a paper.")] = None,
) -> None:
    """Add a paper, person, institution or company to a claim."""
    with entry_session() as session:
        entity = add_entity(session, claim_slug, type=type, name=name, doi=doi)
        out.print(f"Added {entity.type.value} {entity.name} to {claim_slug}.", markup=False)


@entity_app.command("synonym")
def entity_synonym(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    entity_name: Annotated[str, typer.Argument(help="Current name of the entity.")],
    synonym: Annotated[str, typer.Argument(help="Another name it goes by.")],
) -> None:
    """Record another name for an entity. Registry searches use every name."""
    with entry_session() as session:
        entity = add_synonym(session, claim_slug, entity_name, synonym)
        names = ", ".join(entity.synonyms)
        out.print(f"{entity.name} is also known as: {names}.", markup=False)


@entity_app.command("origin-paper")
def entity_origin_paper(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    paper_name: Annotated[str, typer.Argument(help="Name of one of the claim's papers.")],
) -> None:
    """Mark the paper the first news reports were about. Replaces any earlier choice."""
    with entry_session() as session:
        paper = set_origin_paper(session, claim_slug, paper_name)
        out.print(f"Origin paper of {claim_slug}: {paper.name}.", markup=False)


def resolve_command(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    rescore: Annotated[
        bool,
        typer.Option(
            "--rescore",
            help="Also score again the pending trial candidates the search still returns.",
        ),
    ] = False,
) -> None:
    """Search the registries for a claim's interventions and papers.

    Every hit becomes a pending candidate match for you to approve or reject. A trial
    scores as a match only when it tests the intervention for the claim's indication.
    """
    with entry_session() as session:
        claim = find_claim(session, claim_slug)
        if claim is None:
            raise ClaimNotFound(f"No claim has the slug '{claim_slug}'.")
        backend = make_backend(session)
        trials, dois = make_registries(session)
        now = datetime.now(UTC)
        settings = settings_or_exit()
        reject_below = settings.match_reject_below
        accept_above = settings.match_accept_above
        try:
            added = resolve_claim(
                session,
                claim,
                trials=trials,
                dois=dois,
                backend=backend,
                now=now,
                reject_below=reject_below,
                accept_above=accept_above,
            )
            again = (
                rescore_claim(
                    session,
                    claim,
                    trials=trials,
                    backend=backend,
                    now=now,
                    skip=added,
                    reject_below=reject_below,
                    accept_above=accept_above,
                )
                if rescore
                else []
            )
            if claim.evidence_stage is None and not has_stage_suggestion(session, claim):
                stage = suggest_evidence_stage(session, backend, claim, now=now)
                out.print(f"Suggested evidence stage: {stage.choice}. Confirm it in review.")
        except DecisionFailed as failed:
            # Leave through a clean exit so the logged failure is committed with the session.
            err.print(str(failed), markup=False)
            err.print("No candidates were stored.")
            raise typer.Exit(code=1) from None
        noun = "candidate match" if len(added) == 1 else "candidate matches"
        by_rule = [m for m in [*added, *again] if m.reviewed_by is Decider.RULE]
        rejected = [m for m in by_rule if m.review_state is ReviewState.REJECTED]
        approved = [m for m in by_rule if m.review_state is ReviewState.APPROVED]
        waiting = "All are pending review." if not by_rule else "The rest are pending review."
        out.print(f"Found {len(added)} new {noun} for {claim.slug}. {waiting}")
        if rescore:
            candidates = "candidate" if len(again) == 1 else "candidates"
            out.print(f"Scored {len(again)} pending {candidates} again.")
        if approved:
            out.print(
                f"{len(approved)} approved by rule for scoring {accept_above:g} or more"
                " for the claim's indication. They are published with the next export.",
                markup=False,
            )
        if rejected:
            out.print(
                f"{len(rejected)} rejected by rule for scoring under {reject_below:g}."
                " See them with `review list --by-rule`.",
                markup=False,
            )
        for match in sorted(added, key=lambda m: m.score, reverse=True):
            if match.reviewed_by is Decider.RULE:
                continue
            out.print(
                f"  {match.score:.2f}  {match.source_name}  {match.external_id}", markup=False
            )
