"""The steps that use decisions, and what each is shown."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, DecisionLog, Entity, EntityMatch
from thenwhat.decide.core import Backend, Decision, decide, decide_many
from thenwhat.domain import EntityType, EvidenceStage
from thenwhat.sources.base import SourceRecord

EVIDENCE_STAGE = "evidence_stage"
ENTITY_MATCH = "entity_match"
MATCH = "match"
NOT_A_MATCH = "not_a_match"
# The record is about the claim's intervention, but for a different condition.
OTHER_INDICATION = "other_indication"
MAX_CANDIDATE_CHARACTERS = 1500

# What is asked about a trial record: a claim is one intervention for one indication,
# so the same intervention in another condition is its own answer.
TRIAL_OPTIONS = [MATCH, OTHER_INDICATION, NOT_A_MATCH]
TRIAL_QUESTION = (
    "Is this record a trial of the claim's intervention for the claim's indication?\n"
    f"- {MATCH}: it tests this intervention in the claim's indication, in a form of"
    " that condition, or in patients who have it.\n"
    f"- {OTHER_INDICATION}: it tests this intervention for a different condition,"
    " or only in healthy volunteers.\n"
    f"- {NOT_A_MATCH}: it is not a trial of this intervention."
)


def match_ref(match_id: int) -> str:
    """The decision log's reference to a candidate match."""
    return f"{ENTITY_MATCH}:{match_id}"


def latest_scoring(session: Session, match: EntityMatch) -> DecisionLog | None:
    """The latest decision that scored the candidate without an error, if any."""
    return session.scalars(
        select(DecisionLog)
        .where(
            DecisionLog.step == ENTITY_MATCH,
            DecisionLog.input_ref == match_ref(match.id),
            DecisionLog.error.is_(None),
        )
        .order_by(DecisionLog.id.desc())
    ).first()


def candidate_text(record: SourceRecord) -> str:
    """A registry record as it is shown to the backend."""
    return (
        f"Candidate record from {record.source_name} ({record.external_id}):\n{_describe(record)}"
    )


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


def score_matches(
    session: Session,
    backend: Backend,
    *,
    claim: Claim,
    candidates: list[tuple[Entity, EntityMatch, SourceRecord]],
    now: datetime,
) -> None:
    """Set each candidate's score: the probability that its registry record is evidence
    for the claim. Scores order the review queue, and the resolver's rules approve or
    reject on them; this function decides nothing.

    A claim is one intervention for one indication, so a trial is a match only when it
    tests that intervention for that indication. The same intervention in another
    condition is its own answer, so the reviewer can be told which it was. A paper is
    only asked whether it is the same paper. An entity's candidates are scored together,
    several to a backend call.
    """
    by_entity: dict[int, list[tuple[Entity, EntityMatch, SourceRecord]]] = {}
    for candidate in candidates:
        by_entity.setdefault(candidate[0].id, []).append(candidate)
    for group in by_entity.values():
        entity = group[0][0]
        if entity.type is EntityType.INTERVENTION:
            options = TRIAL_OPTIONS
            question = TRIAL_QUESTION
        else:
            options = [MATCH, NOT_A_MATCH]
            question = "Is this record about the same entity as the claim?"
        decisions = decide_many(
            session,
            backend,
            step=ENTITY_MATCH,
            intro=(
                f"{_claim_text(session, claim)}\n\nEntity to match ({entity.type}): {entity.name}"
            ),
            question=question,
            items=[(match_ref(match.id), candidate_text(record)) for _, match, record in group],
            options=options,
            now=now,
        )
        for (_, match, _), decision in zip(group, decisions, strict=True):
            match.score = decision.probabilities[MATCH]


def _describe(candidate: SourceRecord) -> str:
    """What the record says, with a trial's conditions and interventions first so that a
    long record is never cut off before them."""
    section = candidate.payload.get("protocolSection")
    if isinstance(section, dict):
        identification = section.get("identificationModule", {})
        described = {
            "title": identification.get("briefTitle"),
            "official_title": identification.get("officialTitle"),
            "conditions": section.get("conditionsModule", {}).get("conditions", []),
            "interventions": [
                intervention.get("name")
                for intervention in section.get("armsInterventionsModule", {}).get(
                    "interventions", []
                )
            ],
            "phases": section.get("designModule", {}).get("phases", []),
            "status": section.get("statusModule", {}).get("overallStatus"),
            "sponsor": section.get("sponsorCollaboratorsModule", {})
            .get("leadSponsor", {})
            .get("name"),
        }
        text = json.dumps(
            {name: value for name, value in described.items() if value}, ensure_ascii=False
        )
    else:
        text = json.dumps(candidate.payload, ensure_ascii=False, sort_keys=True)
    return text[:MAX_CANDIDATE_CHARACTERS]
