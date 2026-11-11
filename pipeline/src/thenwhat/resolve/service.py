"""Proposing registry matches for a claim's entities. Behavior: openspec entity-resolution.

Every candidate is stored pending. Only an operator can approve one.
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.db.models import Claim, Entity, EntityMatch
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import score_match
from thenwhat.domain import EntityType
from thenwhat.sources.base import SourceRecord


class TrialSearch(Protocol):
    def search_trials(self, intervention: str) -> list[SourceRecord]: ...


class DoiLookup(Protocol):
    def work(self, doi: str) -> SourceRecord | None: ...


def resolve_claim(
    session: Session,
    claim: Claim,
    *,
    trials: TrialSearch,
    dois: DoiLookup,
    backend: Backend,
    now: datetime,
) -> list[EntityMatch]:
    """Search the registries for the claim's interventions and papers and store each new
    hit as a scored, pending candidate. Returns the candidates this run added.

    Candidates that already exist are left exactly as they are, whatever their state.
    If a candidate cannot be scored, none of this run's candidates are kept.
    """
    entities = entities_of(session, claim)
    seen = {
        (match.entity_id, match.source_name, match.external_id)
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id.in_([e.id for e in entities]))
        )
    }
    found: list[tuple[Entity, SourceRecord]] = []

    def consider(entity: Entity, record: SourceRecord) -> None:
        key = (entity.id, record.source_name, record.external_id)
        if key not in seen:
            seen.add(key)
            found.append((entity, record))

    for entity in entities:
        if entity.type is EntityType.INTERVENTION:
            for term in [entity.name, *entity.synonyms]:
                for record in trials.search_trials(term):
                    consider(entity, record)
        elif entity.type is EntityType.PAPER and entity.doi:
            record = dois.work(entity.doi)
            if record is not None:
                consider(entity, record)

    added: list[EntityMatch] = []
    try:
        for entity, record in found:
            match = EntityMatch(
                entity_id=entity.id,
                source_name=record.source_name,
                external_id=record.external_id,
                score=0.0,
            )
            session.add(match)
            session.flush()
            added.append(match)
            match.score = score_match(
                session, backend, claim=claim, entity=entity, match=match, candidate=record, now=now
            )
    except DecisionFailed:
        # The decision log keeps the failure; the unscored candidates are withdrawn.
        for match in added:
            session.delete(match)
        session.flush()
        raise
    session.flush()
    return added
