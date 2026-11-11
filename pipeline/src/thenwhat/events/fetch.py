"""One-shot fetch of a claim's evidence. Behavior: openspec evidence-events.

Events are created only from registry records that an approved match points to.
Fetching again records nothing twice and never changes an existing event's review state.
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, EntityMatch, EvidenceEvent
from thenwhat.domain import Decider, EntityType, EventType, ReviewState
from thenwhat.events.draft import EventDraft
from thenwhat.events.papers import follow_up_confidence, follow_up_event, retraction_event
from thenwhat.events.trial import trial_events
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.crossref import Notice
from thenwhat.sources.europepmc import describe

TRIAL_REGISTRY = "clinicaltrials.gov"


class TrialRegistry(Protocol):
    def fetch_trial(self, nct_id: str) -> SourceRecord | None: ...


class LiteratureIndex(Protocol):
    def paper(self, doi: str) -> SourceRecord | None: ...
    def citing_papers(self, paper: SourceRecord) -> list[SourceRecord]: ...


class NoticeRegistry(Protocol):
    def notices(self, doi: str) -> list[Notice]: ...


def fetch_claim(
    session: Session,
    claim: Claim,
    *,
    trials: TrialRegistry,
    literature: LiteratureIndex,
    notices: NoticeRegistry,
    threshold: float,
    now: datetime,
    no_signal_years: int = 3,
) -> list[EvidenceEvent]:
    """Create the claim's new evidence events and re-derive its status. Returns the
    events this run created."""
    entities = entities_of(session, claim)
    approved: dict[int, list[EntityMatch]] = {}
    for match in session.scalars(
        select(EntityMatch)
        .where(
            EntityMatch.entity_id.in_([entity.id for entity in entities]),
            EntityMatch.review_state == ReviewState.APPROVED,
        )
        .order_by(EntityMatch.id)
    ):
        approved.setdefault(match.entity_id, []).append(match)

    created: list[EvidenceEvent] = []

    def store(draft: EventDraft, match: EntityMatch | None) -> None:
        event = _store(session, claim, draft, match, threshold, now)
        if event is not None:
            created.append(event)

    for entity in entities:
        if entity.type is not EntityType.INTERVENTION:
            continue
        for match in approved.get(entity.id, []):
            if match.source_name != TRIAL_REGISTRY:
                continue
            record = trials.fetch_trial(match.external_id)
            for draft in trial_events(record) if record else []:
                store(draft, match)

    origin_entity = next((entity for entity in entities if entity.is_origin_paper), None)
    origin_match = next(iter(approved.get(origin_entity.id, [])), None) if origin_entity else None
    if origin_entity is not None and origin_match is not None:
        origin_doi = origin_match.external_id
        origin = literature.paper(origin_doi)
        names = [
            name
            for entity in entities
            if entity.type is EntityType.INTERVENTION
            for name in (entity.name, *entity.synonyms)
        ]
        if origin is not None:
            for citing in literature.citing_papers(origin):
                confidence = follow_up_confidence(describe(citing), describe(origin), names)
                draft = follow_up_event(citing, confidence) if confidence else None
                if draft is not None:
                    store(draft, origin_match)

        papers = {origin_doi.lower(): describe(origin).title if origin else origin_entity.name}
        for event in session.scalars(
            select(EvidenceEvent).where(
                EvidenceEvent.claim_id == claim.id,
                EvidenceEvent.type == EventType.FOLLOWUP_PAPER,
                EvidenceEvent.review_state != ReviewState.REJECTED,
            )
        ):
            if event.external_id.startswith("10."):
                papers.setdefault(event.external_id.lower(), event.summary)
        for doi, title in papers.items():
            for notice in notices.notices(doi):
                if notice.type == "retraction":
                    store(retraction_event(doi, title, notice, now), origin_match)

    refresh_status(session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years)
    return created


def _store(
    session: Session,
    claim: Claim,
    draft: EventDraft,
    match: EntityMatch | None,
    threshold: float,
    now: datetime,
) -> EvidenceEvent | None:
    """Store the draft unless the claim already has an event for the same fact."""
    exists = session.scalars(
        select(EvidenceEvent.id).where(
            EvidenceEvent.claim_id == claim.id, EvidenceEvent.dedupe_key == draft.dedupe_key
        )
    ).first()
    if exists is not None:
        return None
    event = event_row(claim, draft, match)
    if not draft.always_review and draft.confidence >= threshold:
        record_decision(event, ReviewState.APPROVED, by=Decider.RULE, now=now)
    session.add(event)
    session.flush()
    return event


def event_row(claim: Claim, draft: EventDraft, match: EntityMatch | None = None) -> EvidenceEvent:
    return EvidenceEvent(
        claim_id=claim.id,
        entity_match_id=match.id if match else None,
        type=draft.type,
        event_date=draft.event_date,
        date_basis=draft.date_basis,
        source_name=draft.source_name,
        source_url=draft.source_url,
        external_id=draft.external_id,
        trial_phases=[phase.value for phase in draft.trial_phases] or None,
        trial_state=draft.trial_state,
        regulatory_outcome=draft.regulatory_outcome,
        summary=draft.summary,
        confidence=draft.confidence,
        raw_payload=draft.raw_payload,
        fetched_at=draft.fetched_at,
        dedupe_key=draft.dedupe_key,
    )
