"""One interface for bounded classification choices. Behavior: openspec decision-steps.

A decision is advisory: it suggests or scores, and never approves or publishes anything.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from sqlalchemy.orm import Session

from thenwhat.db.models import DecisionLog
from thenwhat.llm.errors import LlmError

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm

SUM_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class BackendAnswer:
    choice: str
    probabilities: dict[str, float]
    confidence: float | None = None
    model: str | None = None


class Backend(Protocol):
    name: str

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer: ...


@dataclass(frozen=True, slots=True)
class Decision:
    choice: str
    probabilities: dict[str, float]
    confidence: float
    log_id: int


class DecisionFailed(Exception):
    """The backend gave no usable answer. Nothing is substituted for it."""


class UnknownBackend(Exception):
    pass


def decide(
    session: Session,
    backend: Backend,
    *,
    step: str,
    state: str,
    options: Sequence[str],
    input_ref: str,
    now: datetime,
) -> Decision:
    """Ask the backend to choose one of the options, and log the call whatever happens."""
    offered = list(options)
    entry = DecisionLog(
        step=step, input_ref=input_ref, backend=backend.name, options=offered, created_at=now
    )
    answer: BackendAnswer | None = None
    try:
        answer = backend.answer(step, state, offered)
        entry.model = answer.model
        problem = _problem(answer, offered)
    except LlmError as error:
        problem = str(error)
    except Exception as error:
        problem = f"The {backend.name} backend failed ({type(error).__name__})."

    if problem or answer is None:
        entry.error = problem
        session.add(entry)
        session.flush()
        raise DecisionFailed(problem)

    confidence = answer.probabilities[answer.choice]
    if answer.confidence is not None:
        confidence = answer.confidence
    entry.output = {"choice": answer.choice, "probabilities": answer.probabilities}
    entry.confidence = confidence
    session.add(entry)
    session.flush()
    return Decision(answer.choice, answer.probabilities, confidence, entry.id)


def _problem(answer: BackendAnswer, options: list[str]) -> str | None:
    """Why the answer cannot be used, or None if it can."""
    if answer.choice not in options:
        return f"The backend chose '{answer.choice}', which was not offered."
    if set(answer.probabilities) != set(options):
        return "The backend's probabilities do not match the options offered."
    if any(not 0 <= value <= 1 for value in answer.probabilities.values()):
        return "The backend gave a probability outside 0 to 1."
    if abs(sum(answer.probabilities.values()) - 1) > SUM_TOLERANCE:
        return "The backend's probabilities do not sum to 1."
    if answer.confidence is not None and not 0 <= answer.confidence <= 1:
        return "The backend gave a confidence outside 0 to 1."
    return None


def backend_named(name: str, llm: "Llm") -> Backend:
    """The backend the configuration names. Only the model-backed one exists so far."""
    from thenwhat.decide.llm_backend import LlmBackend

    if name == "llm":
        return LlmBackend(llm)
    raise UnknownBackend(f"Unknown decision backend '{name}'. Available: llm.")
