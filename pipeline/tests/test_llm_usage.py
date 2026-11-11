"""Language model configuration, ledger and ceiling, tested through `Llm.run`
with a scripted model. Scenario names are from openspec llm-usage."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel, Field
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import LlmUsage
from thenwhat.llm.client import (
    BudgetExceeded,
    Llm,
    LlmCallFailed,
    LlmNotConfigured,
    LlmOutputInvalid,
    LlmSettings,
)

NOVEMBER = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SECRET = "sk-test-do-not-leak-0123456789"


class Answer(BaseModel):
    word: str = Field(max_length=5)


def scripted(*outputs: dict | Exception, name: str = "scripted-model") -> FunctionModel:
    """A model that returns the given structured outputs in turn, repeating the last."""
    remaining = list(outputs)

    def respond(messages, info) -> ModelResponse:
        output = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        if isinstance(output, Exception):
            raise output
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    return FunctionModel(respond, model_name=name)


def settings(**overrides) -> LlmSettings:
    values: dict[str, Any] = {
        "model": "test:scripted-model",
        "monthly_budget_usd": Decimal("10"),
        "input_usd_per_mtok": Decimal("3"),
        "output_usd_per_mtok": Decimal("15"),
    }
    return LlmSettings(**(values | overrides))


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def llm(session: Session, model: FunctionModel | None, clock=None, **overrides) -> Llm:
    return Llm(session, settings(**overrides), model=model, now=clock or Clock(NOVEMBER))


def ask(client: Llm, purpose: str = "extraction") -> Answer:
    return client.run(purpose, instructions="Answer.", prompt="Say ok.", output_type=Answer)


def ledger(session: Session) -> list[LlmUsage]:
    return list(session.scalars(select(LlmUsage).order_by(LlmUsage.id)))


# --- configuration ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("missing", "setting"),
    [
        ("model", "LLM_MODEL"),
        ("input_usd_per_mtok", "LLM_INPUT_USD_PER_MTOK"),
        ("output_usd_per_mtok", "LLM_OUTPUT_USD_PER_MTOK"),
    ],
)
def test_missing_configuration_refuses_the_call_and_names_the_setting(
    session: Session, missing: str, setting: str
):
    """Scenario: Model not configured"""
    called = []

    def build(name: str) -> FunctionModel:
        called.append(name)
        return scripted({"word": "ok"})

    client = Llm(
        session, settings(**{missing: None}), model=None, now=Clock(NOVEMBER), build_model=build
    )

    with pytest.raises(LlmNotConfigured, match=setting):
        ask(client)

    assert called == [] and ledger(session) == []


def test_configured_model_name_is_the_one_used(session: Session):
    """Scenario: Model changed"""
    built = []

    def build(name: str) -> FunctionModel:
        built.append(name)
        return scripted({"word": "ok"}, name=name)

    for name in ("test:first", "test:second"):
        Llm(session, settings(model=name), model=None, now=Clock(NOVEMBER), build_model=build).run(
            "extraction", instructions="i", prompt="p", output_type=Answer
        )

    assert built == ["test:first", "test:second"]
    assert [entry.model for entry in ledger(session)] == ["test:first", "test:second"]


# --- ledger ------------------------------------------------------------------------


def test_call_is_recorded_with_purpose_model_tokens_and_cost(session: Session):
    """Scenario: Extraction call"""
    answer = ask(llm(session, scripted({"word": "ok"})), purpose="extraction")

    [entry] = ledger(session)
    assert answer.word == "ok"
    assert (entry.purpose, entry.model, entry.created_at) == (
        "extraction",
        "test:scripted-model",
        NOVEMBER,
    )
    assert entry.input_tokens > 0 and entry.output_tokens > 0
    expected = (Decimal(entry.input_tokens) * 3 + Decimal(entry.output_tokens) * 15) / 1_000_000
    assert entry.cost_usd == expected.quantize(Decimal("0.000001"))


def test_failed_call_is_still_recorded_with_what_it_used(session: Session):
    client = llm(session, scripted({"word": "far too long"}))

    with pytest.raises(LlmOutputInvalid):
        ask(client)

    [entry] = ledger(session)
    assert entry.input_tokens > 0 and entry.cost_usd > 0


# --- ceiling -----------------------------------------------------------------------


def spend(session: Session, amount: str, when: datetime) -> None:
    session.add(
        LlmUsage(
            purpose="extraction",
            model="m",
            input_tokens=1,
            output_tokens=1,
            cost_usd=Decimal(amount),
            created_at=when,
        )
    )
    session.flush()


def test_ceiling_reached_refuses_further_calls(session: Session):
    """Scenario: Ceiling reached"""
    spend(session, "10", datetime(2026, 11, 3, tzinfo=UTC))
    calls = []

    def respond(messages, info) -> ModelResponse:
        calls.append(1)
        return ModelResponse(parts=[])

    model = FunctionModel(respond, model_name="never-called")

    with pytest.raises(BudgetExceeded, match="monthly ceiling"):
        ask(llm(session, model, monthly_budget_usd=Decimal("10")))

    assert calls == []


def test_spend_below_the_ceiling_allows_the_call(session: Session):
    spend(session, "9.99", datetime(2026, 11, 3, tzinfo=UTC))

    assert ask(llm(session, scripted({"word": "ok"}), monthly_budget_usd=Decimal("10"))).word


def test_new_month_starts_a_new_allowance(session: Session):
    """Scenario: New month"""
    spend(session, "10", datetime(2026, 11, 30, 23, 59, tzinfo=UTC))
    december = Clock(datetime(2026, 12, 1, 0, 0, tzinfo=UTC))

    answer = ask(llm(session, scripted({"word": "ok"}), december, monthly_budget_usd=Decimal("10")))

    assert answer.word == "ok"


# --- failures ----------------------------------------------------------------------


def test_provider_rejection_is_reported_without_the_credential(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Provider rejects the key"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    rejection = ModelHTTPError(401, "scripted-model", {"error": f"invalid x-api-key {SECRET}"})

    with pytest.raises(LlmCallFailed) as raised:
        ask(llm(session, scripted(rejection)))

    assert SECRET not in str(raised.value)
    assert "401" in str(raised.value)


def test_output_that_never_validates_names_the_failing_fields(session: Session):
    with pytest.raises(LlmOutputInvalid) as raised:
        ask(llm(session, scripted({"word": "far too long"})))

    assert raised.value.fields == ["word"]
    assert "word" in str(raised.value)


def test_output_is_accepted_once_a_retry_validates(session: Session):
    client = llm(session, scripted({"word": "far too long"}, {"word": "ok"}))

    assert ask(client).word == "ok"
