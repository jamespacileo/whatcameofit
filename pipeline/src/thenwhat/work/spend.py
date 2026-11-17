"""What a step that calls a model would cost, and the ceiling that stops it.
Behavior: openspec work-ledger. The cost itself is recorded where the call is made
(openspec llm-usage); this only estimates before a run and checks before each call."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from thenwhat.config import Settings
from thenwhat.llm.ledger import spent_this_month
from thenwhat.work.errors import BackfillError, SpendCeilingReached
from thenwhat.work.steps import DECISION_DOOR, ModelSpend

MILLION = Decimal(1_000_000)
OPENAI_DECISIONS = "openai-decisions"


class PricesNotSet(BackfillError):
    """A model step's cost cannot be estimated: a price is not configured."""


@dataclass(frozen=True, slots=True)
class Prices:
    input_usd_per_mtok: Decimal
    output_usd_per_mtok: Decimal


def prices_for(settings: Settings, door: str) -> Prices:
    """The configured prices of the model behind a door. Refuses, naming the setting,
    when one is missing: no price is assumed."""
    if door == DECISION_DOOR and settings.decision_backend == OPENAI_DECISIONS:
        if settings.decisions_input_usd_per_mtok is None:
            raise PricesNotSet("DECISIONS_INPUT_USD_PER_MTOK is not set")
        # The Decisions API charges for input only.
        return Prices(settings.decisions_input_usd_per_mtok, Decimal(0))
    if settings.llm_input_usd_per_mtok is None:
        raise PricesNotSet("LLM_INPUT_USD_PER_MTOK is not set")
    if settings.llm_output_usd_per_mtok is None:
        raise PricesNotSet("LLM_OUTPUT_USD_PER_MTOK is not set")
    return Prices(settings.llm_input_usd_per_mtok, settings.llm_output_usd_per_mtok)


def cost_of(spend: ModelSpend, prices: Prices, records: int) -> Decimal:
    """The estimated cost in US dollars of a number of records."""
    one = (
        spend.input_tokens * prices.input_usd_per_mtok
        + spend.output_tokens * prices.output_usd_per_mtok
    ) / MILLION
    return one * records


def records_covered(spend: ModelSpend, prices: Prices, left: Decimal) -> int | None:
    """How many records the ceiling's remainder pays for, or None when a record is free."""
    one = cost_of(spend, prices, 1)
    if one <= 0:
        return None
    return int(max(left, Decimal(0)) // one)


def left_this_month(session: Session, settings: Settings, now: datetime) -> Decimal:
    return max(settings.llm_monthly_budget_usd - spent_this_month(session, now), Decimal(0))


def ceiling_check(settings: Settings, now: Callable[[], datetime]) -> Callable[[Session], None]:
    """A check to run before each call of a model step. It raises when the month's
    recorded cost has reached the ceiling, so the run stops with its records still due."""

    def check(session: Session) -> None:
        if spent_this_month(session, now()) >= settings.llm_monthly_budget_usd:
            raise SpendCeilingReached(
                f"The monthly ceiling of ${settings.llm_monthly_budget_usd} for language "
                "model calls has been reached. No call was made."
            )

    return check
