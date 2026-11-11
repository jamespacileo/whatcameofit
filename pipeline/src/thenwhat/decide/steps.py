"""The steps that use decisions, and what each is shown."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, DecisionLog, Entity, EntityMatch
from thenwhat.decide.core import Backend, Decision, decide
from thenwhat.domain import EntityType, EvidenceStage
from thenwhat.sources.base import SourceRecord

EVIDENCE_STAGE = "evidence_stage"
ENTITY_MATCH = "entity_match"
MATCH = "match"
NOT_A_MATCH = "not_a_match"
MAX_CANDIDATE_CHARACTERS = 1500


def _claim_text(session: Session, claim: Claim) -> str:
    intervention = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).first()
    names = ""
    if intervention is not None:
        also = (
            f" (also known as: {', '.join(intervention.synonyms)})" if intervention.synonyms else ""
        )
        names = f"Intervention: {intervention.name}{also}.\n"
    summary = f"{claim.summary}\n" if claim.summary else ""
    return f"Claim: {claim.headline}\n{summary}{names}Indication: {claim.indication}."


def has_stage_suggestion(session: Session, claim: Claim) -> bool:
    return (
        session.scalars(
            select(DecisionLog.id).where(
                DecisionLog.step == EVIDENCE_STAGE,
                DecisionLog.input_ref == f"claim:{claim.id}",
                DecisionLog.error.is_(None),
            )
        ).first()
        is not None
    )


def suggest_evidence_stage(
    session: Session, backend: Backend, claim: Claim, *, now: datetime
) -> Decision:
    """Suggest the stage of evidence at announcement. The claim's stage is not set here:
    it stays empty until an operator confirms it."""
    return decide(
        session,
        backend,
        step=EVIDENCE_STAGE,
        state=_claim_text(session, claim)
        + "\n\nHow far had the evidence come when this was announced?",
        options=[stage.value for stage in EvidenceStage],
        input_ref=f"claim:{claim.id}",
        now=now,
    )


def score_match(
    session: Session,
    backend: Backend,
    *,
    claim: Claim,
    entity: Entity,
    match: EntityMatch,
    candidate: SourceRecord,
    now: datetime,
) -> float:
    """Probability that the registry record is about the claim's entity. Orders the
    review queue; it approves nothing."""
    state = (
        f"{_claim_text(session, claim)}\n\n"
        f"Entity to match ({entity.type}): {entity.name}\n\n"
        f"Candidate record from {candidate.source_name} ({candidate.external_id}):\n"
        f"{_describe(candidate)}\n\n"
        "Is this record about the same entity as the claim?"
    )
    decision = decide(
        session,
        backend,
        step=ENTITY_MATCH,
        state=state,
        options=[MATCH, NOT_A_MATCH],
        input_ref=f"entity_match:{match.id}",
        now=now,
    )
    return decision.probabilities[MATCH]


def _describe(candidate: SourceRecord) -> str:
    return json.dumps(candidate.payload, ensure_ascii=False, sort_keys=True)[
        :MAX_CANDIDATE_CHARACTERS
    ]
