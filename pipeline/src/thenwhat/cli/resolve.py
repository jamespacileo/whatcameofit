"""Commands for a claim's entities and for proposing registry matches."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import (
    add_entity,
    add_search_phrase,
    add_synonym,
    delete_people,
    people,
    set_origin_paper,
)
from thenwhat.claims.entry import EntryError, claim_by_slug
from thenwhat.cli import extract
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.db.models import Claim, EntityMatch
from thenwhat.decide.core import Backend, DecisionFailed, UnknownBackend, backend_named
from thenwhat.decide.steps import has_stage_suggestion, suggest_evidence_stage
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.resolve.organisations import OrganisationRegistry, match_organisations
from thenwhat.resolve.papers import (
    PaperSearch,
    RegistryNumbers,
    TrialRegistry,
    choose_origin,
    find_papers,
    rescore_papers,
    trials_from_papers,
)
from thenwhat.resolve.service import DoiLookup, TrialSearch, rescore_claim, resolve_claim
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref
from thenwhat.sources.europepmc import EuropePmc
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.ror import Ror

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


@dataclass(frozen=True, slots=True)
class Research:
    """The sources behind related papers and organisations."""

    # None while OPENALEX_API_KEY is empty: paper search is then off.
    papers: PaperSearch | None
    numbers: RegistryNumbers
    registry: TrialRegistry
    organisations: OrganisationRegistry


def make_research(session: Session) -> Research:
    settings = settings_or_exit()
    contact = settings.contact_email
    return Research(
        papers=(
            OpenAlex(session, contact_email=contact, api_key=settings.openalex_api_key)
            if settings.openalex_api_key
            else None
        ),
        numbers=EuropePmc(session, contact_email=contact),
        registry=ClinicalTrials(session, contact_email=contact),
        organisations=Ror(session, contact_email=contact),
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


@entity_app.command("phrase")
def entity_phrase(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    entity_name: Annotated[str, typer.Argument(help="Name of the intervention.")],
    phrase: Annotated[str, typer.Argument(help="Words a registry would use for it.")],
) -> None:
    """Record a search phrase for an intervention that has no product name. The registry
    is searched for it within the claim's indication. It is never shown as a name."""
    with entry_session() as session:
        entity = add_search_phrase(session, claim_slug, entity_name, phrase)
        phrases = ", ".join(entity.search_phrases)
        out.print(f"{entity.name} is searched for as: {phrases}.", markup=False)


@entity_app.command("phrases")
def entity_phrases(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    missing: Annotated[
        bool, typer.Option("--missing", help="Every claim whose intervention has none.")
    ] = False,
) -> None:
    """Have the model give search phrases to claims whose intervention has none.

    It reads what the claim says of itself, not the article. A claim that already has
    a phrase is left alone. Search the registry afterwards with `resolve`.
    """
    # Imported here: the model library is slow to load and most commands never need it.
    from thenwhat.extract.phrases import backfill_search_phrases, needs_phrases

    if not slugs and not missing:
        err.print("Name the claims, or use --missing for every claim without a phrase.")
        raise typer.Exit(code=1)
    with entry_session() as session:
        if slugs:
            claims = []
            for slug in slugs:
                claim = claim_by_slug(session, slug)
                claims.append(claim)
        else:
            claims = list(session.scalars(select(Claim).order_by(Claim.slug)))
        llm = extract.make_llm(session)
        given = 0
        for claim in claims:
            if needs_phrases(session, claim) is None:
                continue
            phrases = backfill_search_phrases(session, llm, claim)
            if phrases:
                given += 1
                out.print(f"{claim.slug}: {', '.join(phrases)}", markup=False)
        out.print(f"{given} of {len(claims)} claims were given search phrases.")


@entity_app.command("people")
def entity_people() -> None:
    """List every stored person with their claim. Only researchers belong: delete a
    patient, relative, reporter or commentator with `entity delete-people`."""
    with entry_session() as session:
        listed = people(session)
        for entity, claim in listed:
            out.print(f"{entity.id}\t{claim.slug}\t{entity.name}", markup=False)
        out.print(f"{len(listed)} person entities.")


@entity_app.command("delete-people")
def entity_delete_people(
    ids: Annotated[list[int], typer.Argument(help="Ids from `entity people`.")],
) -> None:
    """Delete the person entities you name. Refused, deleting none, if an id is not a
    person."""
    with entry_session() as session:
        for entity in delete_people(session, ids):
            out.print(f"Deleted person {entity.name} ({entity.id}).", markup=False)


@entity_app.command("origin-paper")
def entity_origin_paper(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    paper_name: Annotated[str, typer.Argument(help="Name of one of the claim's papers.")],
) -> None:
    """Mark the paper the first news reports were about. Replaces any earlier choice."""
    with entry_session() as session:
        paper = set_origin_paper(session, claim_slug, paper_name)
        out.print(f"Origin paper of {claim_slug}: {paper.name}.", markup=False)


def _related_research(
    session: Session,
    claim: Claim,
    research: Research,
    backend: Backend,
    now: datetime,
    reject_below: float,
    accept_above: float,
    rescore: bool = False,
) -> None:
    """Organisations, related papers, the trials those papers name and the origin paper,
    with a line on each. A step that fails is reported, what it had written is undone,
    and the rest goes on: the trial candidates found before this stand either way."""
    thresholds = {"reject_below": reject_below, "accept_above": accept_above}

    matched = _step(
        session,
        "Organisations were not looked up",
        lambda: match_organisations(session, claim, registry=research.organisations),
    )
    if matched:
        out.print(f"Matched {len(matched)} organisation(s) in ROR. They are pending review.")

    papers = research.papers
    if papers is None:
        out.print("Paper search is off: OPENALEX_API_KEY is not set.")
    else:
        found = _step(
            session,
            "Papers were not searched for",
            lambda: find_papers(
                session, claim, papers=papers, backend=backend, now=now, **thresholds
            ),
        )
        if found is not None:
            _say_papers(found, accept_above, reject_below)
        if rescore:
            again = _step(
                session,
                "Pending papers were not scored again",
                lambda: rescore_papers(
                    session,
                    claim,
                    papers=papers,
                    backend=backend,
                    now=now,
                    skip=found or [],
                    **thresholds,
                ),
            )
            if again is not None:
                noun = "paper" if len(again) == 1 else "papers"
                decided = sum(m.review_state is not ReviewState.PENDING for m in again)
                out.print(f"Scored {len(again)} pending {noun} again; a rule decided {decided}.")

    from_papers = _step(
        session,
        "Approved papers were not read for registry numbers",
        lambda: trials_from_papers(
            session,
            claim,
            numbers=research.numbers,
            registry=research.registry,
            backend=backend,
            now=now,
            papers=papers,
            **thresholds,
        ),
    )
    if from_papers:
        ids = ", ".join(match.external_id for match in from_papers)
        out.print(f"Trial candidates from approved papers: {ids}.", markup=False)

    if papers is not None:
        origin = _step(
            session,
            "The origin paper was not chosen",
            lambda: choose_origin(
                session, claim, papers=papers, backend=backend, now=now, accept_above=accept_above
            ),
        )
        if origin is not None:
            out.print(f"Origin paper set by rule: {origin.name}.", markup=False)
    if isinstance(papers, OpenAlex):
        out.print(papers.usage.line(), markup=False)


def _step[T](session: Session, what_failed: str, work: Callable[[], T]) -> T | None:
    """Run one step of related research in a savepoint. A decision that failed is
    reported and its log entry kept; anything else undoes the step and is reported."""
    try:
        with session.begin_nested():
            try:
                return work()
            except DecisionFailed as failed:
                err.print(f"{what_failed}: {failed}", markup=False)
                return None
    except Exception as failed:
        err.print(f"{what_failed}: {failed or type(failed).__name__}", markup=False)
        return None


def _say_papers(found: list[EntityMatch], accept_above: float, reject_below: float) -> None:
    if not found:
        out.print("No new related paper was found.")
        return
    approved = [m for m in found if m.review_state is ReviewState.APPROVED]
    rejected = [m for m in found if m.review_state is ReviewState.REJECTED]
    noun = "paper" if len(found) == 1 else "papers"
    out.print(
        f"Found {len(found)} related {noun}: {len(approved)} approved by rule for scoring"
        f" {accept_above:g} or more, {len(rejected)} rejected by rule for scoring under"
        f" {reject_below:g}, {len(found) - len(approved) - len(rejected)} pending review.",
        markup=False,
    )
    for match in sorted(approved, key=lambda m: m.score, reverse=True):
        out.print(f"  approved {match.score:.2f}  {match.external_id}", markup=False)


def resolve_command(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    rescore: Annotated[
        bool,
        typer.Option(
            "--rescore",
            help="Also score again the pending trial candidates the search still returns,"
            " and the pending related papers.",
        ),
    ] = False,
) -> None:
    """Search the registries for a claim's interventions and papers.

    Every hit becomes a scored candidate match. A rule rejects one scored near zero and
    approves a trial scored high; the rest wait for you to approve or reject. A trial
    scores as a match only when it tests the intervention for the claim's indication.

    The literature is then searched for papers about the intervention and indication.
    Each is scored, carries the reasons found by rule, and is approved by rule when it
    scores high. A registry number an approved paper states becomes a trial candidate,
    and a paper that is confidently the one first reported on becomes the origin paper.
    Institutions and companies are looked up in the organisation registry.
    """
    with entry_session() as session:
        claim = claim_by_slug(session, claim_slug)
        backend = make_backend(session)
        trials, dois = make_registries(session)
        research = make_research(session)
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
            _related_research(
                session, claim, research, backend, now, reject_below, accept_above, rescore
            )
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
