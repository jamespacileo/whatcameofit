"""Figures the daily job reads from the database. Reads only; decides and changes nothing.

    cd pipeline
    uv run --env-file ../.env python ../scripts/daily_run_figures.py spend
    uv run --env-file ../.env python ../scripts/daily_run_figures.py counts
    uv run --env-file ../.env python ../scripts/daily_run_figures.py published

spend      two numbers: what model calls cost this month and today (UTC), in US dollars
counts     three numbers: claims published, claims awaiting review, claims awaiting audit
published  the slug of every published claim, one a line

"Published" is what the export publishes: approved, not archived, not awaiting audit.
Used by scripts/daily-run.sh (docs/daily-run.md).
"""

import sys
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.cli.session import open_session
from thenwhat.db.models import Claim, LlmUsage
from thenwhat.domain import ReviewState
from thenwhat.llm.ledger import spent_this_month

PUBLISHED = (
    Claim.review_state == ReviewState.APPROVED,
    Claim.archived_at.is_(None),
    Claim.awaiting_audit_at.is_(None),
)


def number_of(session: Session, *conditions) -> int:
    return session.scalar(select(func.count()).select_from(Claim).where(*conditions)) or 0


def spend(session: Session) -> None:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = session.scalar(
        select(func.coalesce(func.sum(LlmUsage.cost_usd), 0)).where(
            LlmUsage.created_at >= day_start
        )
    )
    print(f"{spent_this_month(session, now):.4f} {Decimal(today or 0):.4f}")


def counts(session: Session) -> None:
    print(
        number_of(session, *PUBLISHED),
        number_of(session, Claim.review_state == ReviewState.PENDING),
        number_of(session, Claim.awaiting_audit_at.is_not(None)),
    )


def published(session: Session) -> None:
    for slug in session.scalars(select(Claim.slug).where(*PUBLISHED).order_by(Claim.slug)):
        print(slug)


FIGURES = {"spend": spend, "counts": counts, "published": published}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in FIGURES:
        raise SystemExit(__doc__)
    with open_session() as session:
        FIGURES[sys.argv[1]](session)


if __name__ == "__main__":
    main()
