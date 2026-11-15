"""Evidence-stage confirmation by rule, through its session-taking seam."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from thenwhat.claims.entry import add_claim
from thenwhat.claims.stages import confirm_stage_by_rule
from thenwhat.db.models import DecisionLog
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import suggest_evidence_stage
from thenwhat.domain import ClaimStatus, EvidenceStage
from thenwhat.review.queue import confirm_stage

NOW = datetime(2026, 11, 15, tzinfo=UTC)


class StageReader:
    name = "fake"

    def __init__(self, probability: float, confidence: float) -> None:
        self.probability = probability
        self.confidence = confidence

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        return BackendAnswer(
            "early_human",
            {
                option: self.probability
                if option == "early_human"
                else (1 - self.probability) / (len(options) - 1)
                for option in options
            },
            confidence=self.confidence,
        )


@pytest.mark.parametrize(
    ("probability", "confidence", "threshold", "confirmed"),
    [
        (0.95, 0.95, 0.95, True),
        (0.94, 0.99, 0.95, False),
        (0.99, 0.94, 0.95, False),
        (1.0, 1.0, 0.0, False),
    ],
)
def test_confirmation_requires_both_certainties_and_a_positive_threshold(
    session: Session, probability: float, confidence: float, threshold: float, confirmed: bool
):
    claim = add_claim(
        session,
        slug="example-human-study",
        headline="EX-1 studied in volunteers",
        vertical="mouth-and-teeth",
        intervention="EX-1",
        indication="tooth agenesis",
    )
    decision = suggest_evidence_stage(session, StageReader(probability, confidence), claim, now=NOW)
    log = session.get(DecisionLog, decision.log_id)
    assert log is not None
    original_output = dict(log.output or {})

    assert (
        confirm_stage_by_rule(session, claim, decision, threshold=threshold, now=NOW) is confirmed
    )

    assert claim.evidence_stage is (EvidenceStage.EARLY_HUMAN if confirmed else None)
    if confirmed:
        assert claim.current_status is ClaimStatus.NO_TRIAL_FOUND
    assert log.output == original_output and log.human_label is None


def test_a_confirmed_stage_and_its_human_label_are_never_overwritten(session: Session):
    claim = add_claim(
        session,
        slug="example-confirmed-stage",
        headline="EX-1 at announcement",
        vertical="mouth-and-teeth",
        intervention="EX-1",
        indication="tooth agenesis",
    )
    decision = suggest_evidence_stage(session, StageReader(1.0, 1.0), claim, now=NOW)
    confirm_stage(session, claim.slug, EvidenceStage.ANIMAL, now=NOW)

    assert not confirm_stage_by_rule(session, claim, decision, threshold=0.95, now=NOW)

    assert claim.evidence_stage is EvidenceStage.ANIMAL
    log = session.get(DecisionLog, decision.log_id)
    assert log is not None and log.human_label == "animal"
