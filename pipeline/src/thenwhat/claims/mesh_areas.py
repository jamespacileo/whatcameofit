"""The stored registry records of a claim's approved trials.

The group suggested for a claim used to be made here from a table of MeSH heading names.
It now comes from the claim's clinical categories and the topic mapping
(`thenwhat.clinical`, openspec health-areas "Suggested group from matched trials").
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, EntityMatch, EvidenceEvent
from thenwhat.domain import ReviewState
from thenwhat.sources.clinicaltrials import ClinicalTrials


def approved_trial_payloads(session: Session, claim: Claim) -> list[dict[str, Any]]:
    """The stored registry records of the claim's trials whose match was approved."""
    return list(
        session.scalars(
            select(EvidenceEvent.raw_payload)
            .join(EntityMatch, EntityMatch.id == EvidenceEvent.entity_match_id)
            .where(
                EvidenceEvent.claim_id == claim.id,
                EvidenceEvent.source_name == ClinicalTrials.name,
                EntityMatch.review_state == ReviewState.APPROVED,
            )
            .order_by(EvidenceEvent.id)
        )
    )
