"""Confirming a recorded evidence stage by rule. Behavior: openspec review."""

from datetime import datetime

from sqlalchemy.orm import Session

from thenwhat.db.models import Claim
from thenwhat.decide.core import Decision
from thenwhat.domain import Decider, EvidenceStage
from thenwhat.review.queue import confirm_stage


def confirm_stage_by_rule(
    session: Session,
    claim: Claim,
    suggestion: Decision,
    *,
    threshold: float,
    now: datetime,
    no_signal_years: int = 3,
) -> bool:
    """Confirm only an empty stage with a sufficiently certain, valid reading.

    The suggestion stays in its original log and gains no human label. No model is
    called here; a confirmed stage is never overwritten by this rule.
    """
    probability = suggestion.probabilities.get(suggestion.choice, 0.0)
    if (
        claim.evidence_stage is not None
        or not 0 < threshold <= 1
        or not threshold <= probability <= 1
        or not threshold <= suggestion.confidence <= 1
        or suggestion.choice not in {stage.value for stage in EvidenceStage}
    ):
        return False
    confirm_stage(
        session,
        claim.slug,
        EvidenceStage(suggestion.choice),
        now=now,
        no_signal_years=no_signal_years,
        by=Decider.RULE,
    )
    return True
