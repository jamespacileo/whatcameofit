"""OpenAI's Decisions API: typed answers to bounded questions. Terms and limits: docs/sources.md.

One request carries shared evidence and up to 400 questions, and returns for each a
choice with a probability for every option. It is several times faster than asking a
general model for the same answers as text, because nothing is written out. Calls are
recorded in the same ledger and stopped by the same monthly ceiling as every other call.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy.orm import Session

from thenwhat.llm.errors import LlmCallFailed, LlmNotConfigured
from thenwhat.llm.ledger import check_ceiling, record_usage

API = "https://api.openai.com/v1"
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
    ) -> None:
        self._session = session
        self._settings = settings
        self._now = now
        self._credential = credential
        self._client = httpx.Client(transport=transport, timeout=120.0)

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
        try:
            response = self._client.post(
                f"{API}/decisions", json=body, headers={"Authorization": f"Bearer {credential}"}
            )
        except httpx.TransportError as error:
            raise LlmCallFailed(f"The decision call failed ({type(error).__name__}).") from None
        if response.status_code != 200:
            # The provider's own message can echo what was sent, so it is not repeated.
            raise LlmCallFailed(f"The decision call failed with status {response.status_code}.")
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
