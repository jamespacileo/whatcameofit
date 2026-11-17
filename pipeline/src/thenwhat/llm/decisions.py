"""OpenAI's Decisions API: typed answers to bounded questions. Terms and limits: docs/sources.md.

One request carries shared evidence and up to 400 questions, and returns for each a
choice with a probability for every option. It is several times faster than asking a
general model for the same answers as text, because nothing is written out. Calls are
recorded in the same ledger and stopped by the same monthly ceiling as every other call,
and go through the one call policy (`work/calls.py`): a cause that passes is tried again,
and an API that cannot be asked is told apart from a failed call (`ModelCannotBeAsked`).
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy.orm import Session

from thenwhat.config import load_call_settings
from thenwhat.llm.errors import LlmCallFailed, LlmNotConfigured, ModelCannotBeAsked
from thenwhat.llm.ledger import check_ceiling, record_usage
from thenwhat.work.calls import CallRules, Calls, NotAnswered, Passing, passes, stated_wait
from thenwhat.work.clock import SystemTime, Time
from thenwhat.work.errors import SourcePaused
from thenwhat.work.pause import pause, refuse_if_paused

API = "https://api.openai.com/v1"
# Whom the API belongs to: its pause is kept under this name, shared with any general
# model of the same provider, since one account answers both.
PROVIDER = "openai"
# The error codes OpenAI gives when the account's quota or billing is used up.
QUOTA_USED_UP = frozenset({"insufficient_quota", "billing_hard_limit_reached"})
# The name of the environment variable that holds the provider's credential.
CREDENTIAL = "OPENAI_API_KEY"
# The most questions the API takes in one request.
MAX_QUESTIONS = 400


@dataclass(frozen=True, slots=True)
class DecisionsSettings:
    # The model by the provider's own name, without a provider prefix.
    model: str | None
    monthly_budget_usd: Decimal
    # Input is all that is charged for: the API bills no output.
    input_usd_per_mtok: Decimal | None


@dataclass(frozen=True, slots=True)
class Choice:
    """One question with a fixed set of answers: (value, when it applies)."""

    instructions: str
    options: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class Chosen:
    choice: str
    probabilities: dict[str, float]
    confidence: float


class Decisions:
    def __init__(
        self,
        session: Session,
        settings: DecisionsSettings,
        *,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        credential: str | None = None,
        time: Time | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._now = now
        self._credential = credential
        self._client = httpx.Client(transport=transport, timeout=120.0)
        # What a delay before another attempt is slept on.
        self._time = time or SystemTime()

    @property
    def model_name(self) -> str | None:
        return self._settings.model

    def choose(
        self, purpose: str, *, evidence: str, questions: list[Choice]
    ) -> list[Chosen | None]:
        """One answer per question, in order. None where the model declined to answer.

        Refuses before calling when the model, its price or the credential is not
        configured, or when this month's recorded cost has reached the ceiling.
        """
        settings = self._settings
        if settings.model is None:
            raise LlmNotConfigured(
                "DECISIONS_MODEL is not set and LLM_MODEL does not name an OpenAI model,"
                " so no decision call was made."
            )
        if settings.input_usd_per_mtok is None:
            raise LlmNotConfigured(
                "DECISIONS_INPUT_USD_PER_MTOK is not set, so no decision call was made."
            )
        credential = self._credential or os.environ.get(CREDENTIAL)
        if not credential:
            raise LlmNotConfigured(f"{CREDENTIAL} is not set, so no decision call was made.")

        answers: list[Chosen | None] = []
        for start in range(0, len(questions), MAX_QUESTIONS):
            check_ceiling(self._session, self._now(), settings.monthly_budget_usd)
            asked = questions[start : start + MAX_QUESTIONS]
            answers += self._ask(purpose, credential, evidence, asked)
        return answers

    def _ask(
        self, purpose: str, credential: str, evidence: str, questions: list[Choice]
    ) -> list[Chosen | None]:
        settings = self._settings
        assert settings.model is not None and settings.input_usd_per_mtok is not None
        body = {
            "model": settings.model,
            "input": evidence,
            "questions": [
                {
                    "type": "choice",
                    "name": f"item-{number}",
                    "instructions": question.instructions,
                    "choices": [
                        {"value": value, "description": description}
                        for value, description in question.options
                    ],
                }
                for number, question in enumerate(questions, 1)
            ],
        }

        def attempt() -> httpx.Response:
            try:
                response = self._client.post(
                    f"{API}/decisions",
                    json=body,
                    headers={"Authorization": f"Bearer {credential}"},
                )
            except httpx.TransportError as error:
                raise Passing(f"The decision call failed ({type(error).__name__}).") from error
            status = response.status_code
            if status == 200:
                return response
            # The provider's own message can echo what was sent, so it is not repeated.
            said = f"The decision call failed with status {status}."
            if status == 402 or _quota_used_up(response):
                raise ModelCannotBeAsked(f"{said} The account's quota is used up.")
            if status in (401, 403):
                raise ModelCannotBeAsked(f"{said} The key was refused.")
            if passes(status):
                raise Passing(said, status=status, wait=stated_wait(response, self._now()))
            raise LlmCallFailed(said)

        calls = Calls(
            PROVIDER,
            rules=CallRules(wait_ceiling_seconds=load_call_settings().call_wait_ceiling_seconds),
            now=self._now,
            sleep=self._time.sleep,
            admit=lambda: refuse_if_paused(self._session, PROVIDER, self._now()),
            keep_pause=lambda until: pause(self._session, PROVIDER, until, self._now()),
        )
        try:
            response = calls.send(attempt)
        except (NotAnswered, SourcePaused) as stop:
            raise ModelCannotBeAsked(
                f"The decision backend cannot be asked: {stop}", until=stop.until
            ) from None
        answered = response.json()
        used = int((answered.get("usage") or {}).get("input_tokens") or 0)
        record_usage(
            self._session,
            purpose=purpose,
            model=settings.model,
            input_tokens=used,
            output_tokens=0,
            cost_usd=Decimal(used) * settings.input_usd_per_mtok / 1_000_000,
            now=self._now(),
        )
        by_name = {answer.get("name"): answer for answer in answered.get("answers") or []}
        return [_chosen(by_name.get(f"item-{number}")) for number in range(1, len(questions) + 1)]


def _quota_used_up(response: httpx.Response) -> bool:
    """Whether the answer says the account's quota or billing is used up: waiting for a
    while would not help, so it is not tried again."""
    try:
        error = response.json().get("error") or {}
    except (ValueError, AttributeError):
        return False
    if not isinstance(error, dict):
        return False
    return bool({error.get("code"), error.get("type")} & QUOTA_USED_UP)


def _chosen(answer: dict[str, Any] | None) -> Chosen | None:
    """A usable answer, or None for a refusal, a missing answer or a malformed one."""
    if not answer or answer.get("type") != "choice":
        return None
    try:
        probabilities = {
            str(one["value"]): float(one["probability"]) for one in answer["probabilities"]
        }
        return Chosen(str(answer["choice"]), probabilities, float(answer["confidence"]))
    except (KeyError, TypeError, ValueError):
        return None
