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
from thenwhat.domain import EntityType
from thenwhat.resolve.service import DoiLookup, TrialSearch, resolve_claim
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref

entity_app = typer.Typer(help="Add entities, synonyms and the origin paper.", no_args_is_help=True)


def make_backend(session: Session) -> Backend:
    try:
        return backend_named(settings_or_exit().decision_backend, extract.make_llm(session))
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
) -> None:
    """Search the registries for a claim's interventions and papers.

    Every hit becomes a pending candidate match for you to approve or reject.
    """
    with entry_session() as session:
        claim = find_claim(session, claim_slug)
        if claim is None:
            raise ClaimNotFound(f"No claim has the slug '{claim_slug}'.")
        backend = make_backend(session)
        trials, dois = make_registries(session)
        now = datetime.now(UTC)
        try:
            added = resolve_claim(
                session, claim, trials=trials, dois=dois, backend=backend, now=now
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
        out.print(f"Found {len(added)} new {noun} for {claim.slug}. All are pending review.")
        for match in sorted(added, key=lambda m: m.score, reverse=True):
            out.print(
                f"  {match.score:.2f}  {match.source_name}  {match.external_id}", markup=False
            )
