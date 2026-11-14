"""Papers about a claim that its article did not cite by DOI: finding them, scoring them,
deciding them by rule, and what an approved paper leads to. Behavior: openspec
related-research.

A paper candidate is a candidate match on the claim's intervention whose source is the
literature search. It is never an evidence event and never enters status derivation.
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import name_key
from thenwhat.db.models import Claim, Entity, EntityMatch
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import (
    NO_PAPER,
    choose_origin_paper,
    has_origin_choice,
    score_matches,
    score_papers,
)
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.resolve.reasons import paper_reasons
from thenwhat.resolve.service import (
    MAX_SUMMARY_CHARACTERS,
    approve_confident,
    reject_near_zero,
    what_it_says,
)
from thenwhat.review.decisions import record_decision
from thenwhat.sources import openalex
from thenwhat.sources.base import AllowanceUsedUp, SourceRecord
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.ror import Ror

# The source name a paper candidate carries.
PAPER_SOURCE = OpenAlex.name
MAX_PAPERS_PER_CLAIM = 20


class PaperSearch(Protocol):
    """The literature search. One source stands behind it, and it can be swapped."""

    def search_papers(self, words: str, limit: int = ...) -> list[SourceRecord]: ...

    def paper(self, external_id: str) -> SourceRecord | None: ...


class RegistryNumbers(Protocol):
    def trial_numbers(
        self, *, doi: str | None = None, pubmed_id: str | None = None
    ) -> list[str]: ...


class TrialRegistry(Protocol):
    def fetch_trial(self, nct_id: str) -> SourceRecord | None: ...


def paper_line(record: SourceRecord) -> str:
    """One line on what a paper is: title, year, kind of paper and journal."""
    paper = openalex.describe(record)
    parts = [paper.title.rstrip("."), str(paper.year or ""), paper.kind, paper.journal]
    return ". ".join(part for part in parts if part)[:MAX_SUMMARY_CHARACTERS]


def _intervention(session: Session, claim: Claim) -> Entity | None:
    return next((e for e in entities_of(session, claim) if e.type is EntityType.INTERVENTION), None)


def _paper_matches(
    session: Session, entity: Entity, state: ReviewState | None = None
) -> list[EntityMatch]:
    query = select(EntityMatch).where(
        EntityMatch.entity_id == entity.id, EntityMatch.source_name == PAPER_SOURCE
    )
    if state is not None:
        query = query.where(EntityMatch.review_state == state)
    return list(session.scalars(query.order_by(EntityMatch.score.desc(), EntityMatch.id)))


def _named_organisations(session: Session, claim: Claim) -> tuple[list[str], frozenset[str]]:
    """The institutions and companies the article named, and the registry identifiers
    matched to them and not rejected."""
    named = [
        entity
        for entity in entities_of(session, claim)
        if entity.type in (EntityType.INSTITUTION, EntityType.COMPANY)
    ]
    identifiers = session.scalars(
        select(EntityMatch.external_id).where(
            EntityMatch.entity_id.in_([entity.id for entity in named]),
            EntityMatch.source_name == Ror.name,
            EntityMatch.review_state != ReviewState.REJECTED,
        )
    )
    return [entity.name for entity in named], frozenset(identifiers)


def find_papers(
    session: Session,
    claim: Claim,
    *,
    papers: PaperSearch,
    backend: Backend,
    now: datetime,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
) -> list[EntityMatch]:
    """Search the literature for the claim's intervention and indication and store each
    new paper as a scored candidate with its reasons. Returns the candidates this run
    added; an empty list means no new paper was found.

    The intervention's name, other names and search phrases are each searched together
    with the indication. A claim keeps at most twenty papers, taken in the source's own
    order of relevance, in turn from each term. A paper the claim already has is left as
    it is, whatever its state.

    A candidate scored under `reject_below` is rejected by rule. One scored at or above
    `accept_above` is approved by rule, with or without a reason; 0 turns that off. If a
    candidate cannot be scored, none of this run's candidates are kept.
    """
    intervention = _intervention(session, claim)
    if intervention is None or not claim.indication.strip():
        return []
    had = {match.external_id for match in _paper_matches(session, intervention)}
    room = MAX_PAPERS_PER_CLAIM - len(had)
    if room <= 0:
        return []

    terms: dict[str, str] = {}
    for term in [intervention.name, *intervention.synonyms, *intervention.search_phrases]:
        terms.setdefault(name_key(term), term)
    ranked: list[list[SourceRecord]] = []
    for term in terms.values():
        try:
            ranked.append(papers.search_papers(f"{term} {claim.indication}", MAX_PAPERS_PER_CLAIM))
        except AllowanceUsedUp:
            if not any(ranked):
                raise
            break  # Keep what the earlier terms found; the source is not asked again.

    found: dict[str, SourceRecord] = {}
    for rank in range(max((len(records) for records in ranked), default=0)):
        for records in ranked:
            if rank < len(records) and len(found) < room:
                record = records[rank]
                if record.external_id not in had:
                    found.setdefault(record.external_id, record)

    names, identifiers = _named_organisations(session, claim)
    added: list[tuple[EntityMatch, SourceRecord]] = []
    for record in found.values():
        match = EntityMatch(
            entity_id=intervention.id,
            source_name=PAPER_SOURCE,
            external_id=record.external_id,
            score=0.0,
            record_summary=paper_line(record),
            reasons=paper_reasons(
                openalex.describe(record),
                terms=list(terms.values()),
                indication=claim.indication,
                institutions=names,
                institution_ids=identifiers,
                first_reported=claim.first_reported_date,
            ),
        )
        session.add(match)
        added.append((match, record))
    session.flush()
    matches = [match for match, _ in added]
    try:
        score_papers(session, backend, claim=claim, candidates=added, now=now)
    except DecisionFailed:
        # The decision log keeps the failure; the unscored candidates are withdrawn.
        for match in matches:
            session.delete(match)
        session.flush()
        raise
    reject_near_zero(matches, reject_below, now)
    if accept_above > 0:
        for match in matches:
            if match.review_state is ReviewState.PENDING and match.score >= accept_above:
                record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=now)
    session.flush()
    return matches


def trials_from_papers(
    session: Session,
    claim: Claim,
    *,
    numbers: RegistryNumbers,
    registry: TrialRegistry,
    backend: Backend,
    now: datetime,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
) -> list[EntityMatch]:
    """Store, as trial candidates, the trials whose registry numbers the claim's approved
    papers state. Returns the candidates this run added.

    Every approved paper is read, so one the operator approved since the last run is
    covered too. A paper that states more than three numbers is a review and contributes
    none. A trial the claim already has a candidate for is left as it is. Each new one is
    scored and decided by rule exactly as a trial the registry search found.
    """
    intervention = _intervention(session, claim)
    if intervention is None:
        return []
    had = set(
        session.scalars(
            select(EntityMatch.external_id).where(
                EntityMatch.entity_id == intervention.id,
                EntityMatch.source_name == ClinicalTrials.name,
            )
        )
    )
    found: list[tuple[Entity, SourceRecord]] = []
    for paper in _paper_matches(session, intervention, ReviewState.APPROVED):
        if not paper.external_id.startswith("10."):
            continue  # Europe PMC is asked by DOI; a paper without one is not looked up.
        for number in numbers.trial_numbers(doi=paper.external_id):
            if number in had:
                continue
            had.add(number)
            record = registry.fetch_trial(number)
            if record is not None:
                found.append((intervention, record))

    added = [
        EntityMatch(
            entity_id=entity.id,
            source_name=record.source_name,
            external_id=record.external_id,
            score=0.0,
            record_summary=what_it_says(record),
        )
        for entity, record in found
    ]
    session.add_all(added)
    session.flush()
    try:
        score_matches(
            session,
            backend,
            claim=claim,
            candidates=[
                (entity, match, record)
                for (entity, record), match in zip(found, added, strict=True)
            ],
            now=now,
        )
    except DecisionFailed:
        for match in added:
            session.delete(match)
        session.flush()
        raise
    reject_near_zero(added, reject_below, now)
    approve_confident(session, added, accept_above, now)
    session.flush()
    return added


def choose_origin(
    session: Session,
    claim: Claim,
    *,
    papers: PaperSearch,
    backend: Backend,
    now: datetime,
    accept_above: float = 0.0,
) -> Entity | None:
    """Set the claim's origin paper by rule when one approved paper is confidently the
    one first reported on. Returns the origin paper it set, or None.

    Nothing is asked when the claim has an origin paper, when the rule is off, when no
    approved paper with a DOI was published on or before the first report, or when the
    same papers were already asked about. A choice below `accept_above`, or of none,
    leaves the claim without one. The operator replaces the paper with `entity
    origin-paper` and removes it by rejecting its match.
    """
    entities = entities_of(session, claim)
    intervention = _intervention(session, claim)
    reported = claim.first_reported_date
    if (
        accept_above <= 0
        or intervention is None
        or reported is None
        or any(entity.is_origin_paper for entity in entities)
    ):
        return None

    offered: dict[str, tuple[EntityMatch, SourceRecord]] = {}
    for match in _paper_matches(session, intervention, ReviewState.APPROVED):
        if not match.external_id.startswith("10."):
            continue
        record = papers.paper(match.external_id)
        published = openalex.describe(record).published_date if record else None
        if record is not None and published is not None and published <= reported:
            offered[match.external_id] = (match, record)
    if not offered or has_origin_choice(session, claim, list(offered)):
        return None

    decision = choose_origin_paper(
        session,
        backend,
        claim,
        offered=[
            (doi, f"{paper_line(record)}. Published {openalex.describe(record).published_date}")
            for doi, (_, record) in offered.items()
        ],
        now=now,
    )
    probability = decision.probabilities[decision.choice]
    if decision.choice == NO_PAPER or probability < accept_above:
        return None

    _, record = offered[decision.choice]
    doi = decision.choice
    origin = next(
        (e for e in entities if e.type is EntityType.PAPER and (e.doi or "").lower() == doi), None
    )
    if origin is None:
        origin = Entity(
            claim_id=claim.id, type=EntityType.PAPER, name=openalex.describe(record).title, doi=doi
        )
        session.add(origin)
    origin.is_origin_paper = True
    session.flush()
    # The paper's identity is confirmed by an approved match, as for a paper the article
    # cited. This one records that a rule decided it, and on what probability.
    confirmed = EntityMatch(
        entity_id=origin.id,
        source_name=PAPER_SOURCE,
        external_id=doi,
        score=probability,
        record_summary=paper_line(record),
    )
    record_decision(confirmed, ReviewState.APPROVED, by=Decider.RULE, now=now)
    session.add(confirmed)
    session.flush()
    return origin
