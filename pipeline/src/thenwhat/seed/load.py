"""Loads a checked-in seed claim as already reviewed.

A seed exists so that a fresh checkout shows a real claim page. Its review
decisions are recorded as made by the seed loader, never as a human's, and it
writes nothing to the decision log, so the human labels stay human.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_entity, add_synonym, set_origin_paper
from thenwhat.claims.entry import add_article, add_claim, add_promise, find_claim
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, EntityMatch, EvidenceEvent
from thenwhat.domain import (
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.manual import add_manual_event
from thenwhat.review.decisions import record_decision


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SeedClaim(Strict):
    slug: str
    headline: str
    summary: str
    vertical: str
    intervention: str
    synonyms: list[str] = []
    indication: str
    evidence_stage: EvidenceStage | None = None


class SeedArticle(Strict):
    url: str
    outlet: str
    title: str
    published_date: date


class SeedPromise(Strict):
    article_url: str
    description: str
    parsed_date: date | None = None


class SeedPaper(Strict):
    title: str
    doi: str


class SeedEvent(Strict):
    type: EventType
    event_date: date
    date_basis: str
    source_name: str
    source_url: str
    external_id: str | None = None
    trial_phases: list[TrialPhase] = []
    trial_state: TrialState | None = None
    regulatory_outcome: RegulatoryOutcome | None = None
    summary: str


class SeedFile(Strict):
    compiled_by: str
    checked_on: date
    note: str
    trial_registration: dict[str, Any]
    claim: SeedClaim
    articles: list[SeedArticle]
    promises: list[SeedPromise] = []
    origin_paper: SeedPaper | None = None
    events: list[SeedEvent] = []


def load_seed(session: Session, content: dict[str, Any], *, now: datetime) -> Claim | None:
    """Create the seed's claim with everything approved by the seed loader.

    Returns None, changing nothing, when a claim with its slug already exists.
    """
    seed = SeedFile.model_validate(content)
    slug = seed.claim.slug
    if find_claim(session, slug) is not None:
        return None

    claim = add_claim(
        session,
        slug=slug,
        headline=seed.claim.headline,
        vertical=seed.claim.vertical,
        intervention=seed.claim.intervention,
        indication=seed.claim.indication,
        summary=seed.claim.summary,
    )
    for synonym in seed.claim.synonyms:
        add_synonym(session, slug, seed.claim.intervention, synonym)
    for article in seed.articles:
        add_article(
            session,
            slug,
            url=article.url,
            outlet=article.outlet,
            title=article.title,
            published_date=article.published_date,
        )
    for promise in seed.promises:
        add_promise(
            session,
            slug,
            article_url=promise.article_url,
            description=promise.description,
            parsed_date=promise.parsed_date,
        )
    if seed.origin_paper is not None:
        paper = add_entity(
            session,
            slug,
            type=EntityType.PAPER,
            name=seed.origin_paper.title,
            doi=seed.origin_paper.doi,
        )
        set_origin_paper(session, slug, seed.origin_paper.title)
        match = EntityMatch(
            entity_id=paper.id,
            source_name="crossref",
            external_id=seed.origin_paper.doi.lower(),
            score=1.0,
        )
        record_decision(match, ReviewState.APPROVED, by=Decider.SEED, now=now)
        session.add(match)
    for entry in seed.events:
        event = add_manual_event(
            session,
            slug,
            type=entry.type,
            event_date=entry.event_date,
            source_url=entry.source_url,
            summary=entry.summary,
            source_name=entry.source_name,
            external_id=entry.external_id,
            trial_phases=entry.trial_phases,
            trial_state=entry.trial_state,
            regulatory_outcome=entry.regulatory_outcome,
            now=now,
        )
        event.date_basis = entry.date_basis
        event.raw_payload = event.raw_payload | {
            "entered_by": "seed file",
            "checked_on": str(seed.checked_on),
        }
        record_decision(event, ReviewState.APPROVED, by=Decider.SEED, now=now)

    claim.evidence_stage = seed.claim.evidence_stage
    record_decision(claim, ReviewState.APPROVED, by=Decider.SEED, now=now)
    session.flush()
    refresh_status(session, claim, as_of=now.date(), now=now)
    return claim


def seeded_events(session: Session, claim: Claim) -> list[EvidenceEvent]:
    return list(
        session.scalars(
            select(EvidenceEvent)
            .where(EvidenceEvent.claim_id == claim.id)
            .order_by(EvidenceEvent.event_date, EvidenceEvent.id)
        )
    )
