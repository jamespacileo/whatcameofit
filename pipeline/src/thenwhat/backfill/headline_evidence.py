"""The three calibrated Decisions questions used for treatment headline triage."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from thenwhat.decide.core import Backend, decide_many
from thenwhat.decide.steps import lead_ref

INTRO = "Use only the headline."
OPTIONS = ("relevant", "review", "irrelevant")
QUESTIONS = {
    "lead_triage:J_assistive_devices": (
        "Does this headline report a treatment effect, approval, or a specific treatment "
        "study?\n"
        "- relevant: Identifiable treatment or prevention for a health problem, with a "
        "claim or study update. Everyday descriptions, study starts, negative results "
        "and harms count. An assistive device counts when tested or linked to a specific "
        "functional gain.\n"
        "- review: Plausible lead with a missing detail, or diagnostic research.\n"
        "- irrelevant: No treatment research lead. Drop business, access alone, advice, "
        "exposure-only risk, animal care and nonmedical uses."
    ),
    "lead_triage:K_test_finding": (
        "Does this headline report a treatment effect, approval, or a specific treatment "
        "study?\n"
        "- relevant: Identifiable treatment or prevention for a health problem, with a "
        "claim or study update. Everyday descriptions, study starts, negative results "
        "and harms count.\n"
        "- review: Plausible lead with a missing detail, or diagnostic research. "
        "Recovery after an unspecified drug, treatment, surgery or transplant goes to "
        "review. A test that detects disease or predicts response is review when that is "
        "the finding.\n"
        "- irrelevant: No treatment research lead. Drop business, access alone, advice, "
        "exposure-only risk, animal care and nonmedical uses."
    ),
    "lead_triage:X_specific_evidence": (
        "Could the headline alone point to a specific treatment result or study event?\n"
        "- relevant: It describes the intervention and health problem or identifies a "
        "specific intervention study. Results, harms, treatment starts, approvals and "
        "device trials count, including work in the lab.\n"
        "- review: An unspecified recovery, a vague promise, or a test that diagnoses or "
        "predicts rather than treating. Review general plans, sponsor claims lacking a "
        "specific outcome and study anecdotes with no identifiable intervention or "
        "health use.\n"
        "- irrelevant: No treatment evidence lead, including animal care, exposure-only "
        "associations, access, business and general advice."
    ),
}
EVIDENCE_TRIAGE_VERSION = 2


def score_evidence_headlines(
    session: Session,
    backend: Backend,
    *,
    headlines: Sequence[tuple[int, str]],
    now: datetime,
) -> list[float]:
    """Average the three independently scored relevance probabilities."""
    items = [(lead_ref(ident), headline) for ident, headline in headlines]
    questions = [
        decide_many(
            session,
            backend,
            step=step,
            intro=INTRO,
            question=question,
            items=items,
            options=list(OPTIONS),
            now=now,
        )
        for step, question in QUESTIONS.items()
    ]
    return [
        sum(answer.probabilities["relevant"] for answer in answers) / len(questions)
        for answers in zip(*questions, strict=True)
    ]
