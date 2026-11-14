"""Stores a claim's derived status. The rules themselves live in `thenwhat.status`."""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent, FailureFlag
from thenwhat.domain import ReviewState, TrialPhase
from thenwhat.status.rules import Derivation, Evidence, Flag, StatusChange, derive, history


def refresh_status(
    session: Session,
    claim: Claim,
    *,
    as_of: date,
    now: datetime,
    no_signal_years: int = 3,
) -> Derivation:
    """Derive the claim's status from its approved events and confirmed evidence stage,
    and store it.

    The stored status and its updated-at time change only when the derived status
    or overlay differs from what is stored. `as_of` and `now` are passed in so that
    the caller owns the clock.
    """
    derivation = derive(
        _approved_evidence(session, claim),
        _flags(session, claim),
        first_reported_date=claim.first_reported_date,
        as_of=as_of,
        origin_paper_ids=_origin_paper_ids(session, claim),
        no_signal_years=no_signal_years,
        evidence_stage=claim.evidence_stage,
    )

    stored = (claim.current_status, claim.overlay_years)
    if (derivation.status, derivation.overlay_years) != stored:
        claim.current_status = derivation.status
        claim.overlay_years = derivation.overlay_years
        claim.status_updated_at = now
    return derivation


def status_history(session: Session, claim: Claim) -> list[StatusChange]:
    """The claim's status over time, by the same rules and the same approved events."""
    return history(
        _approved_evidence(session, claim),
        _flags(session, claim),
        first_reported_date=claim.first_reported_date,
        origin_paper_ids=_origin_paper_ids(session, claim),
        evidence_stage=claim.evidence_stage,
    )


def _approved_evidence(session: Session, claim: Claim) -> list[Evidence]:
    rows = session.scalars(
        select(EvidenceEvent).where(
            EvidenceEvent.claim_id == claim.id,
            EvidenceEvent.review_state == ReviewState.APPROVED,
        )
    )
    return [
        Evidence(
            id=row.id,
            type=row.type,
            event_date=row.event_date,
            external_id=row.external_id,
            review_state=row.review_state,
            trial_phases=tuple(TrialPhase(phase) for phase in row.trial_phases or ()),
            trial_state=row.trial_state,
            regulatory_outcome=row.regulatory_outcome,
        )
        for row in rows
    ]


def _flags(session: Session, claim: Claim) -> list[Flag]:
    rows = session.scalars(select(FailureFlag).where(FailureFlag.claim_id == claim.id))
    return [Flag(row.trial_external_id, row.evidence_event_id) for row in rows]


def _origin_paper_ids(session: Session, claim: Claim) -> frozenset[str]:
    """Identifiers of the origin paper, taken from its approved matches."""
    return frozenset(
        session.scalars(
            select(EntityMatch.external_id)
            .join(Entity, Entity.id == EntityMatch.entity_id)
            .where(
                Entity.claim_id == claim.id,
                Entity.is_origin_paper,
                EntityMatch.review_state == ReviewState.APPROVED,
            )
        )
    )
