"""What language model calls cost, and the month's total. Behavior: openspec llm-usage.

Every door to a model writes here and checks the same ceiling.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.db.models import LlmUsage

MICRO_DOLLAR = Decimal("0.000001")


def spent_this_month(session: Session, now: datetime) -> Decimal:
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = session.scalar(
        select(func.coalesce(func.sum(LlmUsage.cost_usd), 0)).where(
            LlmUsage.created_at >= month_start
        )
    )
    return Decimal(total or 0)


def record_usage(
    session: Session,
    *,
    purpose: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: Decimal,
    now: datetime,
) -> None:
    session.add(
        LlmUsage(
            purpose=purpose,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd.quantize(MICRO_DOLLAR),
            created_at=now,
        )
    )
    session.flush()
