"""The one door to a language model: configuration, usage ledger and monthly ceiling.

Behavior: openspec llm-usage. Provider credentials are read from the environment
by the provider library and never pass through this module.
"""

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from collections.abc import Callable  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from pydantic import BaseModel, ValidationError  # noqa: E402
from pydantic_ai import Agent, capture_run_messages  # noqa: E402
from pydantic_ai.exceptions import UnexpectedModelBehavior  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart  # noqa: E402
from pydantic_ai.models import Model, infer_model  # noqa: E402
from pydantic_ai.usage import RunUsage  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from thenwhat.db.models import LlmUsage  # noqa: E402
from thenwhat.llm.errors import (  # noqa: E402
    BudgetExceeded,
    LlmCallFailed,
    LlmError,
    LlmNotConfigured,
    LlmOutputInvalid,
)

MICRO_DOLLAR = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class LlmSettings:
    model: str | None
    monthly_budget_usd: Decimal
    input_usd_per_mtok: Decimal | None
    output_usd_per_mtok: Decimal | None


class Llm:
    def __init__(
        self,
        session: Session,
        settings: LlmSettings,
        *,
        model: Model | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        build_model: Callable[[str], Model] = infer_model,
    ) -> None:
        self._session = session
        self._settings = settings
        self._model = model
        self._now = now
        self._build_model = build_model

    def run[Output: BaseModel](
        self,
        purpose: str,
        *,
        instructions: str,
        prompt: str,
        output_type: type[Output],
        retries: int = 2,
    ) -> Output:
        """Ask the configured model for output of the given shape and record what it cost.

        Refuses before calling when the model or its prices are not configured, or when
        this month's recorded cost has reached the ceiling.
        """
        settings = self._settings
        for value, name in (
            (settings.model, "LLM_MODEL"),
            (settings.input_usd_per_mtok, "LLM_INPUT_USD_PER_MTOK"),
            (settings.output_usd_per_mtok, "LLM_OUTPUT_USD_PER_MTOK"),
        ):
            if value is None:
                raise LlmNotConfigured(f"{name} is not set, so no language model call was made.")
        if self._spent_this_month() >= settings.monthly_budget_usd:
            raise BudgetExceeded(
                f"The monthly ceiling of ${settings.monthly_budget_usd} for language model"
                " calls has been reached. No call was made."
            )

        assert settings.model is not None
        model = self._model or self._build_model(settings.model)
        agent = Agent(model, output_type=output_type, instructions=instructions, retries=retries)
        usage = RunUsage()
        messages: list[ModelMessage] = []
        try:
            with capture_run_messages() as messages:
                result = agent.run_sync(prompt, usage=usage)
        except UnexpectedModelBehavior:
            raise LlmOutputInvalid(_failing_fields(messages, output_type)) from None
        except Exception as error:
            # The provider's own message can echo the credential, so it is not repeated.
            status = getattr(error, "status_code", None)
            detail = f" with status {status}" if status else ""
            raise LlmCallFailed(
                f"The language model call failed{detail} ({type(error).__name__})."
            ) from None
        finally:
            self._record(purpose, usage)
        return result.output

    def _spent_this_month(self) -> Decimal:
        month_start = self._now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = self._session.scalar(
            select(func.coalesce(func.sum(LlmUsage.cost_usd), 0)).where(
                LlmUsage.created_at >= month_start
            )
        )
        return Decimal(total or 0)

    def _record(self, purpose: str, usage: RunUsage) -> None:
        settings = self._settings
        assert settings.model and settings.input_usd_per_mtok is not None
        assert settings.output_usd_per_mtok is not None
        if not usage.requests:
            return
        cost = (
            Decimal(usage.input_tokens) * settings.input_usd_per_mtok
            + Decimal(usage.output_tokens) * settings.output_usd_per_mtok
        ) / 1_000_000
        self._session.add(
            LlmUsage(
                purpose=purpose,
                model=settings.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_usd=cost.quantize(MICRO_DOLLAR),
                created_at=self._now(),
            )
        )
        self._session.flush()


def _failing_fields(messages: list[ModelMessage], output_type: type[BaseModel]) -> list[str]:
    """Fields that failed validation in the model's last attempt."""
    for message in reversed(messages):
        if not isinstance(message, ModelResponse):
            continue
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                try:
                    output_type.model_validate(part.args_as_dict())
                except ValidationError as error:
                    return sorted(
                        {".".join(str(step) for step in e["loc"]) for e in error.errors()}
                    )
                return []
    return []


__all__ = [
    "BudgetExceeded",
    "Llm",
    "LlmCallFailed",
    "LlmError",
    "LlmNotConfigured",
    "LlmOutputInvalid",
    "LlmSettings",
]
