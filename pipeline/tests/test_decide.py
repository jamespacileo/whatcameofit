"""Bounded decisions, tested through `decide` with fake backends and through the
model-backed backend with a scripted model. Scenario names are from openspec decision-steps."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import DecisionLog
from thenwhat.decide.core import (
    BackendAnswer,
    DecisionFailed,
    UnknownBackend,
    backend_named,
    decide,
)
from thenwhat.decide.llm_backend import LlmBackend
from thenwhat.llm.client import Llm, LlmSettings

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
STAGES = ["in_vitro", "animal", "early_human", "late_human"]
ANIMAL = {"in_vitro": 0.05, "animal": 0.8, "early_human": 0.1, "late_human": 0.05}


class FixedBackend:
    def __init__(self, answer: BackendAnswer | Exception, name: str = "fixed") -> None:
        self.name = name
        self._answer = answer

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


def ask(session: Session, backend, options: list[str] = STAGES):
    return decide(
        session,
        backend,
        step="evidence_stage",
        state="An antibody regrew teeth in mice.",
        options=options,
        input_ref="claim:1",
        now=NOW,
    )


def log(session: Session) -> list[DecisionLog]:
    return list(session.scalars(select(DecisionLog).order_by(DecisionLog.id)))


# --- result shape ----------------------------------------------------------------


def test_decision_has_a_choice_a_probability_per_option_and_a_confidence(session: Session):
    """Scenario: Evidence stage decision"""
    decision = ask(session, FixedBackend(BackendAnswer("animal", ANIMAL)))

    assert decision.choice == "animal"
    assert set(decision.probabilities) == set(STAGES)
    assert sum(decision.probabilities.values()) == pytest.approx(1.0)
    assert decision.confidence == pytest.approx(0.8)


def test_backend_may_state_its_own_confidence(session: Session):
    decision = ask(session, FixedBackend(BackendAnswer("animal", ANIMAL, confidence=0.6)))

    assert decision.confidence == pytest.approx(0.6)


# --- invalid results ---------------------------------------------------------------


def test_choice_outside_the_options_fails_without_a_default(session: Session):
    """Scenario: Choice outside the options"""
    answer = BackendAnswer("in_rabbits", ANIMAL)

    with pytest.raises(DecisionFailed, match="in_rabbits"):
        ask(session, FixedBackend(answer))


@pytest.mark.parametrize(
    "probabilities",
    [
        {"animal": 1.0},  # does not cover the options
        ANIMAL | {"in_rabbits": 0.0},  # names an option that was not offered
        ANIMAL | {"animal": 0.5},  # does not sum to 1
        ANIMAL | {"animal": 1.4, "in_vitro": -0.55},  # outside 0 to 1
    ],
)
def test_probabilities_that_do_not_fit_the_options_fail(session: Session, probabilities):
    with pytest.raises(DecisionFailed):
        ask(session, FixedBackend(BackendAnswer("animal", probabilities)))


# --- log -----------------------------------------------------------------------------


def test_successful_call_is_logged_with_an_empty_human_label(session: Session):
    """Scenario: Successful call"""
    decision = ask(session, FixedBackend(BackendAnswer("animal", ANIMAL, model="model-x")))

    [entry] = log(session)
    assert entry.id == decision.log_id
    assert (entry.step, entry.input_ref, entry.backend, entry.model) == (
        "evidence_stage",
        "claim:1",
        "fixed",
        "model-x",
    )
    assert entry.options == STAGES
    assert entry.output == {"choice": "animal", "probabilities": ANIMAL}
    assert entry.confidence == pytest.approx(0.8)
    assert (entry.error, entry.human_label, entry.created_at) == (None, None, NOW)


def test_failed_call_is_logged_with_its_error(session: Session):
    """Scenario: Failed call"""
    with pytest.raises(DecisionFailed):
        ask(session, FixedBackend(RuntimeError("backend exploded")))

    [entry] = log(session)
    assert entry.output is None and entry.confidence is None
    assert entry.error and "RuntimeError" in entry.error


def test_invalid_result_is_logged_as_a_failure(session: Session):
    with pytest.raises(DecisionFailed):
        ask(session, FixedBackend(BackendAnswer("in_rabbits", ANIMAL)))

    [entry] = log(session)
    assert entry.output is None
    assert entry.error and "in_rabbits" in entry.error


# --- backends ------------------------------------------------------------------------


def test_backend_can_be_replaced_without_changing_the_caller(session: Session):
    """Scenario: Backend replaced"""
    first = ask(session, FixedBackend(BackendAnswer("animal", ANIMAL), name="backend-a"))
    second = ask(session, FixedBackend(BackendAnswer("animal", ANIMAL), name="backend-b"))

    assert (first.choice, set(first.probabilities)) == (second.choice, set(second.probabilities))
    assert [entry.backend for entry in log(session)] == ["backend-a", "backend-b"]


def test_configured_backend_name_selects_the_backend(session: Session):
    llm = Llm(session, LlmSettings(None, Decimal("10"), None, None))

    assert isinstance(backend_named("llm", llm), LlmBackend)
    with pytest.raises(UnknownBackend, match="llm"):
        backend_named("crystal-ball", llm)


# --- the model-backed backend ----------------------------------------------------------


def model_backend(session: Session, output: dict[str, Any], model: str | None = "test:scripted"):
    def respond(messages, info) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    settings = LlmSettings(model, Decimal("10"), Decimal("3"), Decimal("15"))
    return LlmBackend(Llm(session, settings, model=FunctionModel(respond), now=lambda: NOW))


def test_model_backend_returns_the_models_choice_and_names_the_model(session: Session):
    decision = ask(session, model_backend(session, {"choice": "animal", "probabilities": ANIMAL}))

    [entry] = log(session)
    assert decision.choice == "animal"
    assert (entry.backend, entry.model) == ("llm", "test:scripted")


def test_model_backend_scales_probabilities_that_nearly_sum_to_one(session: Session):
    loose = {"in_vitro": 0.05, "animal": 0.75, "early_human": 0.1, "late_human": 0.05}

    decision = ask(session, model_backend(session, {"choice": "animal", "probabilities": loose}))

    assert sum(decision.probabilities.values()) == pytest.approx(1.0)
    assert decision.probabilities["animal"] == pytest.approx(0.75 / 0.95)


def test_model_backend_without_a_configured_model_fails_and_is_logged(session: Session):
    backend = model_backend(session, {"choice": "animal", "probabilities": ANIMAL}, model=None)

    with pytest.raises(DecisionFailed, match="LLM_MODEL"):
        ask(session, backend)

    [entry] = log(session)
    assert entry.error and "LLM_MODEL" in entry.error
