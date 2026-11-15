"""The read outcome for an article that is not about one treatment for one condition.

It replaces "not a new treatment": an article about an established treatment now becomes
a claim, so the outcome that refuses says what is still refused.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEPT = ("added_to_claim", "new_claim", "cannot_be_read", "needs_vertical", "enough_articles")
OLD, NEW = "not_a_new_treatment", "not_one_treatment"


def _rename(before: str, after: str) -> None:
    op.drop_constraint(op.f("ck_link_lead_read_outcome"), "link_lead", type_="check")
    op.execute(f"UPDATE link_lead SET read_outcome = '{after}' WHERE read_outcome = '{before}'")
    listed = ", ".join(f"'{value}'" for value in (*KEPT, after))
    op.create_check_constraint(
        op.f("ck_link_lead_read_outcome"), "link_lead", f"read_outcome IN ({listed})"
    )


def upgrade() -> None:
    _rename(OLD, NEW)


def downgrade() -> None:
    _rename(NEW, OLD)
