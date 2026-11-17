"""The one door to a language model: configuration, usage ledger and monthly ceiling.

Behavior: openspec llm-usage. Provider credentials are read from the environment
by the provider library and never pass through this module. Every call goes through the
one call policy (`work/calls.py`, openspec decision-steps): the provider library makes a
single attempt, and the policy retries the causes that pass. A model that cannot be asked
is told apart from one that answered badly (`ModelCannotBeAsked`).
"""

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

import asyncio  # noqa: E402
from collections.abc import Callable, Sequence  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

import httpx  # noqa: E402
from pydantic import BaseModel, ValidationError  # noqa: E402
from pydantic_ai import Agent, capture_run_messages  # noqa: E402

# The library's own way onto the event loop for its synchronous calls. It is not part of
# its public interface: `Agent.run_sync` is, but takes one prompt. Using the same door
# keeps several calls at once on the loop the single calls use.
from pydantic_ai._utils import run_until_complete  # noqa: E402
from pydantic_ai.exceptions import (  # noqa: E402
    ModelAuthenticationError,
    ModelConnectionError,
    ModelQuotaExceededError,
    ModelRateLimitError,
    ModelRequestTimeout,
    ModelServerError,
    ModelUnavailableError,
    UnexpectedModelBehavior,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart  # noqa: E402
from pydantic_ai.models import Model, infer_model  # noqa: E402
from pydantic_ai.settings import ModelSettings  # noqa: E402
from pydantic_ai.usage import RunUsage  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from thenwhat.config import load_call_settings  # noqa: E402
from thenwhat.llm.errors import (  # noqa: E402
    BudgetExceeded,
    LlmCallFailed,
    LlmError,
    LlmNotConfigured,
    LlmOutputInvalid,
    ModelCannotBeAsked,
)
from thenwhat.llm.ledger import check_ceiling, record_usage  # noqa: E402
from thenwhat.work.calls import CallRules, Calls, NotAnswered, Passing, passes  # noqa: E402
from thenwhat.work.clock import SystemTime, Time  # noqa: E402
from thenwhat.work.errors import SourcePaused  # noqa: E402
from thenwhat.work.pause import pause, refuse_if_paused  # noqa: E402

# The provider library makes one attempt per call: the call policy owns retrying.
ONE_ATTEMPT = ModelSettings(max_retries=0)
# Failures of the provider that may pass if the call is made again.
PASSING = (
    ModelRateLimitError,
    ModelUnavailableError,
    ModelServerError,
    ModelConnectionError,
    ModelRequestTimeout,
    httpx.TransportError,
)


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
        time: Time | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._model = model
        self._now = now
        self._build_model = build_model
        # What a delay before another attempt is slept on.
        self._time = time or SystemTime()

    @property
    def model_name(self) -> str | None:
        return self._settings.model

    @property
    def provider(self) -> str:
        """Whom the model is asked of: the provider named before the model's own name.
        A pause is kept under it, so every process stops asking it."""
        model = self._settings.model or ""
        return model.split(":", 1)[0] if ":" in model else model

    def _calls(self) -> Calls:
        provider = self.provider
        return Calls(
            provider,
            rules=CallRules(wait_ceiling_seconds=load_call_settings().call_wait_ceiling_seconds),
            now=self._now,
            sleep=self._time.sleep,
            admit=lambda: refuse_if_paused(self._session, provider, self._now()),
            keep_pause=lambda until: pause(self._session, provider, until, self._now()),
        )

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
        check_ceiling(self._session, self._now(), settings.monthly_budget_usd)

        assert settings.model is not None
        model = self._model or self._build_model(settings.model)
        agent = Agent(model, output_type=output_type, instructions=instructions, retries=retries)

        def attempt() -> Output:
            usage = RunUsage()
            messages: list[ModelMessage] = []
            try:
                with capture_run_messages() as messages:
                    return agent.run_sync(prompt, usage=usage, model_settings=ONE_ATTEMPT).output
            except UnexpectedModelBehavior:
                raise LlmOutputInvalid(_failing_fields(messages, output_type)) from None
            except Exception as error:
                raise _failure(error) from None
            finally:
                self._record(purpose, usage)

        try:
            return self._calls().send(attempt)
        except (NotAnswered, SourcePaused) as stop:
            raise ModelCannotBeAsked(
                f"The language model cannot be asked: {stop}", until=stop.until
            ) from None

    def run_many[Output: BaseModel](
        self,
        purpose: str,
        *,
        instructions: str,
        prompts: Sequence[str],
        output_type: type[Output],
        retries: int = 2,
    ) -> list[Output | LlmError]:
        """Ask the configured model the same thing of several prompts at once, and record
        what each call cost. The answers come back in the prompts' order; a call that
        failed gives its error in its place, and the others stand. When the model cannot
        be asked for any of them, that is raised once every call is over: what the others
        cost is recorded, and their answers are not given.

        The refusals of `run` are made once, before any call: when the model or its
        prices are not configured, when it is paused, or when this month's recorded cost
        has reached the ceiling. The ceiling is not looked at again between the calls of
        one group, so a group can pass it by what its own calls cost.
        """
        settings = self._settings
        for value, name in (
            (settings.model, "LLM_MODEL"),
            (settings.input_usd_per_mtok, "LLM_INPUT_USD_PER_MTOK"),
            (settings.output_usd_per_mtok, "LLM_OUTPUT_USD_PER_MTOK"),
        ):
            if value is None:
                raise LlmNotConfigured(f"{name} is not set, so no language model call was made.")
        check_ceiling(self._session, self._now(), settings.monthly_budget_usd)

        assert settings.model is not None
        calls = self._calls()
        try:
            refuse_if_paused(self._session, calls.name, self._now())
        except SourcePaused as stop:
            raise ModelCannotBeAsked(
                f"The language model cannot be asked: {stop}", until=stop.until
            ) from None
        model = self._model or self._build_model(settings.model)
        agent = Agent(model, output_type=output_type, instructions=instructions, retries=retries)

        async def ask(prompt: str) -> tuple[Output | LlmError | NotAnswered, list[RunUsage]]:
            usages: list[RunUsage] = []

            async def attempt() -> Output:
                usage = RunUsage()
                usages.append(usage)
                messages: list[ModelMessage] = []
                try:
                    with capture_run_messages() as messages:
                        result = await agent.run(prompt, usage=usage, model_settings=ONE_ATTEMPT)
                except UnexpectedModelBehavior:
                    raise LlmOutputInvalid(_failing_fields(messages, output_type)) from None
                except Exception as error:
                    raise _failure(error) from None
                return result.output

            try:
                return await calls.send_async(attempt), usages
            except (LlmError, NotAnswered) as failed:
                return failed, usages

        async def ask_all() -> list[tuple[Output | LlmError | NotAnswered, list[RunUsage]]]:
            return list(await asyncio.gather(*(ask(prompt) for prompt in prompts)))

        # On the loop the single calls run on, so the model's connections are shared.
        answered = run_until_complete(ask_all())
        for _, usages in answered:
            for usage in usages:
                self._record(purpose, usage)
        for answer, _ in answered:
            if isinstance(answer, ModelCannotBeAsked):
                raise answer
            if isinstance(answer, NotAnswered):
                stop = calls.kept(answer)
                raise ModelCannotBeAsked(
                    f"The language model cannot be asked: {stop}", until=stop.until
                )
        return [answer for answer, _ in answered if not isinstance(answer, NotAnswered)]

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
        record_usage(
            self._session,
            purpose=purpose,
            model=settings.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost,
            now=self._now(),
        )


def _failure(error: Exception) -> Exception:
    """What a provider's failure means: the model cannot be asked (its key refused, its
    quota used up), a cause that passes and is tried again, or a failed call. The
    provider's own message can echo the credential, so it is never repeated."""
    status = getattr(error, "status_code", None)
    said = f"The language model call failed{f' with status {status}' if status else ''}"
    said = f"{said} ({type(error).__name__})."
    if isinstance(error, ModelQuotaExceededError) or status == 402:
        return ModelCannotBeAsked(f"{said} The account's quota is used up.")
    if isinstance(error, ModelAuthenticationError) or status in (401, 403):
        return ModelCannotBeAsked(f"{said} The key was refused.")
    if isinstance(error, PASSING) or (status is not None and passes(status)):
        return Passing(said, status=status, wait=getattr(error, "retry_after", None))
    return LlmCallFailed(said)


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
    "ModelCannotBeAsked",
]
