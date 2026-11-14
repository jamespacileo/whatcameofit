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
    from thenwhat.llm.decisions import Decisions

SUM_TOLERANCE = 1e-6
# Models often return probabilities that sum to 0.98 or 1.01; a sum this far from 1 is
# rescaled. Further off, the answer is left for the caller to refuse.
RESCALE_WITHIN = 0.1
# How many items a backend is asked about in one call.
BATCH_SIZE = 20


def rescaled(probabilities: dict[str, float]) -> dict[str, float]:
    """The probabilities scaled to sum to 1 when their sum is within RESCALE_WITHIN of 1,
    else as given."""
    total = sum(probabilities.values())
    if total > 0 and abs(total - 1) <= RESCALE_WITHIN:
        return {option: value / total for option, value in probabilities.items()}
    return probabilities


@dataclass(frozen=True, slots=True)
class BackendAnswer:
    choice: str
    probabilities: dict[str, float]
    confidence: float | None = None
    model: str | None = None


class Backend(Protocol):
    name: str

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer: ...


class BatchBackend(Backend, Protocol):
    """A backend that can make the same choice for several items in one call."""

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> Sequence[BackendAnswer | None]: ...


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
    return _record(session, entry, answer)


def decide_many(
    session: Session,
    backend: Backend,
    *,
    step: str,
    intro: str,
    question: str,
    items: Sequence[tuple[str, str]],
    options: Sequence[str],
    now: datetime,
) -> list[Decision]:
    """Make the same choice for each item, given as (input reference, text).

    A backend that answers in batches is asked about up to BATCH_SIZE items per call, or
    as many as the backend says it takes; any other backend is asked item by item. Every
    item gets its own log entry either way. If any item of a batch has no usable answer,
    the batch fails once all of its items are logged, and later batches are not asked.
    """
    offered = list(options)
    answer_many = getattr(backend, "answer_many", None)
    if answer_many is None:
        return [
            decide(
                session,
                backend,
                step=step,
                state=f"{intro}\n\n{text}\n\n{question}",
                options=offered,
                input_ref=input_ref,
                now=now,
            )
            for input_ref, text in items
        ]

    decisions: list[Decision] = []
    size = getattr(backend, "batch_size", BATCH_SIZE)
    for start in range(0, len(items), size):
        batch = items[start : start + size]
        answers: Sequence[BackendAnswer | None] = []
        failure: str | None = None
        try:
            answers = answer_many(step, intro, question, [text for _, text in batch], offered)
        except LlmError as error:
            failure = str(error)
        except Exception as error:
            failure = f"The {backend.name} backend failed ({type(error).__name__})."

        problems: list[str] = []
        for index, (input_ref, _) in enumerate(batch):
            entry = DecisionLog(
                step=step,
                input_ref=input_ref,
                backend=backend.name,
                options=offered,
                created_at=now,
            )
            answer = answers[index] if index < len(answers) else None
            problem = failure
            if problem is None:
                problem = (
                    "The backend gave no answer for this item."
                    if answer is None
                    else _problem(answer, offered)
                )
            if problem or answer is None:
                entry.error = problem
                session.add(entry)
                problems.append(problem or "")
                continue
            entry.model = answer.model
            decisions.append(_record(session, entry, answer))
        session.flush()
        if problems:
            raise DecisionFailed(problems[0])
    return decisions


def _record(session: Session, entry: DecisionLog, answer: BackendAnswer) -> Decision:
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


def backend_named(name: str, llm: "Llm", decisions: "Decisions | None" = None) -> Backend:
    """The backend the configuration names: a general model answering in text ("llm"),
    or OpenAI's Decisions API ("openai-decisions")."""
    from thenwhat.decide.decisions_backend import NAME, DecisionsBackend
    from thenwhat.decide.llm_backend import LlmBackend

    if name == "llm":
        return LlmBackend(llm)
    if name == NAME and decisions is not None:
        return DecisionsBackend(decisions)
    raise UnknownBackend(f"Unknown decision backend '{name}'. Available: llm, {NAME}.")
