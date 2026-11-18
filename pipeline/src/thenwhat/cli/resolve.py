"""Commands for a claim's entities and for proposing registry matches."""

from datetime import UTC, datetime
from typing import Annotated

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.corrections import rename_intervention
from thenwhat.claims.entities import (
    add_entity,
    add_search_phrase,
    add_synonym,
    delete_people,
    people,
    set_origin_paper,
)
from thenwhat.claims.entry import EntryError, claim_by_slug
from thenwhat.claimsteps.run import SUBSTANCE, TRIALS
from thenwhat.claimsteps.search import ClaimPapers, PapersFound, TrialsFound
from thenwhat.claimsteps.step import Research
from thenwhat.cli import extract
from thenwhat.cli.claim_steps import outcome_line, run_for_claims, unfinished
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import entry_session
from thenwhat.cli.session import settings_or_exit
from thenwhat.db.models import Claim, EntityMatch
from thenwhat.decide.core import Backend, UnknownBackend, backend_named
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.resolve.codes import Codes, Listing, Substances, give_development_codes
from thenwhat.resolve.service import (
    DoiLookup,
    RuleRedo,
    TrialSearch,
    fill_record_facts,
)
from thenwhat.sources.base import (
    MissingContact,
    MissingKey,
    SourceError,
    TermsNotRecorded,
)
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref
from thenwhat.sources.europepmc import EuropePmc
from thenwhat.sources.gsrs import Gsrs
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.ror import Ror
from thenwhat.sources.rxnorm import RxNorm, vaccine_codes
from thenwhat.sources.terms import SOURCES

entity_app = typer.Typer(help="Add entities, synonyms and the origin paper.", no_args_is_help=True)


def make_backend(session: Session) -> Backend:
    from thenwhat.llm.cache import ModelCache
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
        cache=ModelCache(settings.llm_cache_dir) if settings.llm_cache_dir is not None else None,
    )
    try:
        return backend_named(settings.decision_backend, extract.make_llm(session), decisions)
    except UnknownBackend as unknown:
        raise EntryError(str(unknown)) from None


def _say_redone(claim: Claim, redone: RuleRedo) -> None:
    """What scoring a rule's approvals again changed, and what it left to be looked at."""
    out.print(
        f"Scored again {redone.scored} trial match(es) a rule had approved for"
        f" '{claim.slug}'; {len(redone.withdrawn)} no longer approved.",
        markup=False,
    )
    for said, trials in (
        ("Now waiting for review", redone.pending),
        ("Rejected by the rule", redone.rejected),
        ("Still approved, but not returned by the search and so not scored", redone.not_returned),
    ):
        if trials:
            out.print(f"{said}: {', '.join(trials)}.", markup=False)
    if redone.events_kept:
        kept = ", ".join(str(event) for event in redone.events_kept)
        out.print(
            "Events a person or an assistant decided, left as they were on a match that"
            f" is no longer approved: {kept}.",
            markup=False,
        )
    if redone.withdrawn:
        out.print(f"Status of '{claim.slug}': {claim.current_status.value}.", markup=False)


def make_registries(session: Session) -> tuple[TrialSearch, DoiLookup]:
    contact = settings_or_exit().contact_email
    return (
        ClinicalTrials(session, contact_email=contact),
        Crossref(session, contact_email=contact),
    )


def make_substances(session: Session) -> Substances:
    return Gsrs(session, contact_email=settings_or_exit().contact_email)


def make_brands(session: Session) -> Substances | None:
    """The source of brands, or None when the list of sources does not record its terms
    as accepted by the operator: a source whose terms are read but not accepted is not
    asked."""
    if not SOURCES[RxNorm.name].accepted:
        return None
    return RxNorm(session, contact_email=settings_or_exit().contact_email)


# What each source of substances is called in a line to the operator.
SOURCE_TITLES = {Gsrs.name: "GSRS", RxNorm.name: "RxNorm"}


def say_codes(slug: str, answer: Codes) -> None:
    """One line on what the registry of substances lists for a claim's intervention,
    naming the source that answered. An intervention it does not list is said to have
    no code; none is guessed."""
    name = answer.asked
    titles = [SOURCE_TITLES.get(source, source) for source in answer.sources] or ["GSRS"]
    first, by = titles[0], titles[-1]
    # The registry of substances listed nothing, and the source of brands was asked.
    fell_back = len(titles) > 1
    nothing = f"{first} lists no substance named '{name}'"
    if answer.listing is Listing.NOT_LISTED:
        also = f", and {by} lists no brand of that name" if fell_back else ""
        said = f"{nothing}{also}. No development code was added."
    elif fell_back and answer.listing is Listing.SEVERAL_SUBSTANCES:
        said = (
            f"{nothing}. {by} lists it as a brand of more than one ingredient"
            f" ({'; '.join(answer.substances)}), so none was taken. No development code"
            " was added."
        )
    elif fell_back and answer.record is not None and vaccine_codes(answer.record.payload):
        said = (
            f"{nothing}. {by} lists it as a brand of {answer.substances[0]}, and as a"
            f" vaccine (CVX {', '.join(vaccine_codes(answer.record.payload))}): the"
            " ingredient is an antigen, kept but not searched as a name. No development"
            " code was added."
        )
    elif fell_back:
        said = (
            f"{nothing}. {by} lists it as a brand of {answer.substances[0]}, which is"
            " searched as a name. No development code was added."
        )
    elif answer.listing is Listing.SEVERAL_SUBSTANCES:
        said = (
            f"{by} lists the names of '{name}' under more than one substance"
            f" ({'; '.join(answer.substances)}). No development code was added."
        )
    elif answer.codes:
        said = (
            f"{by} lists '{name}' as {answer.substances[0]}, with the development"
            f" code(s): {', '.join(answer.codes)}. Each is searched within the indication."
        )
    else:
        said = (
            f"{by} lists '{name}' as {answer.substances[0]}, with no development code"
            " beyond its names."
        )
    out.print(f"{slug}: {said}", markup=False)


def make_research(session: Session) -> Research:
    settings = settings_or_exit()
    contact = settings.contact_email
    return Research(
        papers=(
            OpenAlex(session, contact_email=contact, api_key=settings.openalex_api_key)
            if settings.research_papers_enabled and settings.openalex_api_key
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


@entity_app.command("rename")
def entity_rename(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    old_name: Annotated[str, typer.Argument(help="What the intervention is called now.")],
    new_name: Annotated[str, typer.Argument(help="Its name alone: no maker, dose or brackets.")],
    old_is_description: Annotated[
        bool,
        typer.Option(
            "--old-is-description",
            help="The old name is a description, a dose or carries brackets: drop it."
            " Without this it is kept as a synonym.",
        ),
    ] = False,
    reslug: Annotated[
        bool,
        typer.Option(
            "--reslug",
            help="Make the slug again by rule from the new name. The old address leads"
            " to the new one.",
        ),
    ] = False,
    as_assistant: Annotated[
        bool,
        typer.Option(
            "--as-assistant",
            help="Record the rename as decided by an AI assistant, not by the operator.",
        ),
    ] = False,
) -> None:
    """Correct the name of a claim's intervention. Its registries are due to be searched
    again under the new name (`thenwhat prepare --due`)."""
    with entry_session() as session:
        done = rename_intervention(
            session,
            claim_slug,
            old_name,
            new_name,
            by=Decider.ASSISTANT if as_assistant else Decider.HUMAN,
            now=datetime.now(UTC),
            old_is_description=old_is_description,
            reslug=reslug,
        )
        by = ", decided by the assistant" if as_assistant else ""
        kept = "kept as a synonym" if done.kept_as_synonym else "dropped"
        out.print(
            f"Renamed the intervention of {done.claim.slug} to {done.entity.name}{by}."
            f" '{done.old_name}' was {kept}.",
            markup=False,
        )
        if done.old_slug is not None:
            out.print(
                f"The slug is now {done.claim.slug}. After the next export and deploy,"
                f" /{done.old_slug} leads to it.",
                markup=False,
            )
        out.print(
            f"Its registry search is due again: run `thenwhat prepare {done.claim.slug}`"
            " or `thenwhat prepare --due`.",
            markup=False,
        )


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


@entity_app.command("codes")
def entity_codes(
    slugs: Annotated[list[str] | None, typer.Argument(help="Slugs of the claims.")] = None,
    every: Annotated[bool, typer.Option("--all", help="Every claim.")] = False,
) -> None:
    """Look each claim's intervention up in the substance registry (GSRS) and keep the
    development codes it lists, such as CIN-107 for baxdrostat. A brand GSRS does not
    list is asked of RxNorm, which gives its one ingredient as a name to search for.

    A code is kept only when the registry lists the intervention's names, letter for
    letter, under exactly one substance. Nothing is matched loosely and no model is
    asked. `resolve` does this itself; use this to do it for many claims, then resolve.
    """
    if not slugs and not every:
        err.print("Name the claims, or use --all for every claim.")
        raise typer.Exit(code=1)
    with entry_session() as session:
        if slugs:
            claims = [claim_by_slug(session, slug) for slug in slugs]
        else:
            claims = list(session.scalars(select(Claim).order_by(Claim.slug)))
        substances, brands = make_substances(session), make_brands(session)
        if brands is None:
            out.print(
                "RxNorm is not asked about brands: its terms are not accepted (docs/sources.md)."
            )
        listed = coded = by_brand = failed = 0
        for claim in claims:
            try:
                # In a savepoint, so a source that fails leaves this claim as it was.
                with session.begin_nested():
                    answer = give_development_codes(
                        session, claim, substances=substances, brands=brands
                    )
            except (MissingContact, MissingKey, TermsNotRecorded):
                # The setup is wrong, not the source: no claim could be looked up.
                raise
            except SourceError as not_asked:
                failed += 1
                err.print(
                    f"{claim.slug}: development codes were not looked up: {not_asked}",
                    markup=False,
                )
                continue
            if answer is None:
                out.print(f"{claim.slug}: the claim has no intervention.", markup=False)
                continue
            say_codes(claim.slug, answer)
            one = answer.listing is Listing.ONE_SUBSTANCE
            listed += one and answer.source == Gsrs.name
            by_brand += one and answer.source == RxNorm.name
            coded += bool(answer.codes)
        out.print(
            f"{len(claims)} claims: GSRS lists the intervention of {listed} under one"
            f" substance, and gave {coded} of them at least one development code."
            f" RxNorm lists {by_brand} more as a brand of one ingredient."
        )
    # Outside the session, so what was kept for the other claims is not undone.
    if failed:
        err.print(
            f"{failed} were not looked up, and what was kept for them is unchanged."
            " Run this again for them."
        )
        raise typer.Exit(code=1)


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


@entity_app.command("record-facts")
def entity_record_facts() -> None:
    """Read the registry record of every shown trial match stored before its facts were
    kept, so the claim page can lay it out field by field. Run once after migration 0028;
    a match stored since then has its facts already."""
    with entry_session() as session:
        filled, missing = fill_record_facts(session, make_research(session).registry)
    out.print(f"Read the facts of {filled} trial matches.")
    for external_id in missing:
        err.print(f"No registry record for {external_id}; its facts stay empty.", markup=False)
    if missing:
        raise typer.Exit(1)


@entity_app.command("origin-paper")
def entity_origin_paper(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    paper_name: Annotated[str, typer.Argument(help="Name of one of the claim's papers.")],
) -> None:
    """Mark the paper the first news reports were about. Replaces any earlier choice."""
    with entry_session() as session:
        paper = set_origin_paper(session, claim_slug, paper_name)
        out.print(f"Origin paper of {claim_slug}: {paper.name}.", markup=False)


def _say_papers(
    found: list[EntityMatch], accept_above: float, reject_below: float, has_papers: bool
) -> None:
    if not found and not has_papers:
        # Said as it is, and left at that: no looser search is tried in its place.
        out.print(
            "The paper search found nothing for this claim. It has no related paper."
            " Give the intervention a search phrase with `entity phrase` to search again."
        )
        return
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


def _say_matches(
    slug: str,
    added: list[EntityMatch],
    again: list[EntityMatch],
    refused: dict[str, str],
    *,
    rescore: bool,
    accept_above: float,
    reject_below: float,
) -> None:
    """Say what a search found: how many candidates are new, how many a rule decided,
    the terms the registry refused, and each candidate left for review with its score."""
    noun = "candidate match" if len(added) == 1 else "candidate matches"
    by_rule = [m for m in [*added, *again] if m.reviewed_by is Decider.RULE]
    rejected = [m for m in by_rule if m.review_state is ReviewState.REJECTED]
    approved = [m for m in by_rule if m.review_state is ReviewState.APPROVED]
    waiting = "All are pending review." if not by_rule else "The rest are pending review."
    out.print(f"Found {len(added)} new {noun} for {slug}. {waiting}")
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
    if refused:
        terms = "; ".join(f"'{term}'" for term in refused)
        out.print(
            f"{len(refused)} term(s) the registry could not search for, and nothing was"
            f" searched in their place: {terms}. Reword them and resolve again.",
            markup=False,
        )
    for match in sorted(added, key=lambda m: m.score, reverse=True):
        if match.reviewed_by is Decider.RULE:
            continue
        out.print(f"  {match.score:.2f}  {match.source_name}  {match.external_id}", markup=False)


PAPERS = ClaimPapers.name


def _say_trials(
    slug: str, found: TrialsFound, *, rescore: bool, accept_above: float, reject_below: float
) -> None:
    """What the search of the trial registry found, and the evidence stage it read."""
    for term, reason in found.refused.items():
        err.print(
            f"Not searched for: {ClinicalTrials.name} cannot search for '{term}': {reason}",
            markup=False,
        )
    _say_matches(
        slug,
        found.added,
        found.again,
        found.refused,
        rescore=rescore,
        accept_above=accept_above,
        reject_below=reject_below,
    )
    if found.stage is not None and found.stage_confirmed:
        out.print(f"Evidence stage confirmed by rule: {found.stage.choice}.")
    elif found.stage is not None and found.stage_newly_read:
        out.print(f"Suggested evidence stage: {found.stage.choice}. Confirm it in review.")


def _say_research(
    slug: str, found: PapersFound, *, accept_above: float, reject_below: float
) -> None:
    """What the search for organisations and papers found."""
    if found.by_doi:
        _say_matches(
            slug,
            found.by_doi,
            [],
            {},
            rescore=False,
            accept_above=accept_above,
            reject_below=reject_below,
        )
    if found.organisations:
        chosen = sum(match.review_state is ReviewState.APPROVED for match in found.organisations)
        out.print(
            f"Matched {len(found.organisations)} organisation(s) in ROR: {chosen} approved by"
            f" rule as ROR's chosen record, {len(found.organisations) - chosen} pending review."
        )
    if found.papers is None:
        out.print("Paper search is off: OPENALEX_API_KEY is not set.")
    else:
        _say_papers(found.papers, accept_above, reject_below, found.has_papers)
    if found.again is not None:
        noun = "paper" if len(found.again) == 1 else "papers"
        decided = sum(match.review_state is not ReviewState.PENDING for match in found.again)
        out.print(f"Scored {len(found.again)} pending {noun} again; a rule decided {decided}.")
    if found.from_papers:
        ids = ", ".join(match.external_id for match in found.from_papers)
        out.print(f"Trial candidates from approved papers: {ids}.", markup=False)
    if found.origin is not None:
        out.print(f"Origin paper set by rule: {found.origin.name}.", markup=False)
    if found.usage:
        out.print(found.usage, markup=False)


def resolve_command(
    claim_slug: Annotated[str, typer.Argument(help="Slug of the claim.")],
    rescore: Annotated[
        bool,
        typer.Option(
            "--rescore",
            help="Also score again the pending trial candidates the search still returns,"
            " the ones a rule rejected whose record files the intervention under another"
            " name, and the pending related papers.",
        ),
    ] = False,
    redo_rule: Annotated[
        bool,
        typer.Option(
            "--redo-rule",
            help="Also score again the trial matches a rule approved, as the question is"
            " asked now, and let the rule decide them again. A match it no longer approves"
            " loses its events and the status is derived again. Matches you or an"
            " assistant decided are left alone.",
        ),
    ] = False,
) -> None:
    """Search the registries for a claim's intervention and papers, now, whatever was
    searched before: the steps `claim_substance`, `claim_trials` and `claim_papers` of
    `thenwhat prepare`, in that order, each reported.

    The intervention is first looked up in the substance registry, and the development
    codes it lists for that one substance are searched for as well, within the claim's
    indication. A search waits for the lookup to finish.

    Every hit becomes a scored candidate match. A rule rejects one scored near zero and
    approves a trial scored high; the rest wait for you to approve or reject. A trial
    scores as a match only when it tests the intervention for the claim's indication.
    Every term searched, cut by a limit or not sent leaves a record of the search.

    The literature is then searched for papers about the intervention and indication.
    Each is scored, carries the reasons found by rule, and is approved by rule when it
    scores high. A registry number an approved paper states becomes a trial candidate,
    and a paper that is confidently the one first reported on becomes the origin paper.
    Institutions and companies are looked up in the organisation registry.

    A step that did not finish is said, and the command exits with 1: a source that
    failed puts it off, and `thenwhat prepare` takes it up again.
    """
    with entry_session() as session:
        claim = claim_by_slug(session, claim_slug)
        claim_id, slug = claim.id, claim.slug
    steps = run_for_claims(
        [claim_id], [SUBSTANCE, TRIALS, PAPERS], rescore=rescore, redo_rule=redo_rule
    )
    settings = settings_or_exit()
    accept_above, reject_below = settings.match_accept_above, settings.match_reject_below
    substance, trials, papers = steps
    with entry_session() as session:
        codes = substance.results.get(claim_id)
        if codes is not None:
            say_codes(slug, codes)
        found = trials.results.get(claim_id)
        if found is not None:
            _say_trials(
                slug,
                found,
                rescore=rescore,
                accept_above=accept_above,
                reject_below=reject_below,
            )
            if found.redone is not None:
                claim = claim_by_slug(session, slug)
                _say_redone(claim, found.redone)
        research = papers.results.get(claim_id)
        if research is not None:
            _say_research(slug, research, accept_above=accept_above, reject_below=reject_below)
        for step in steps:
            line = outcome_line(session, step, claim_id, slug)
            if line is not None:
                err.print(line, markup=False)
        if unfinished(session, steps, claim_id):
            raise typer.Exit(code=1)
