"""A read outcome for an article that is not a report of a new treatment.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BEFORE = ("added_to_claim", "new_claim", "cannot_be_read", "needs_vertical", "enough_articles")
AFTER = (*BEFORE, "not_a_new_treatment")


def _allow(values: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_link_lead_read_outcome"), "link_lead", type_="check")
    listed = ", ".join(f"'{value}'" for value in values)
    op.create_check_constraint(
        op.f("ck_link_lead_read_outcome"), "link_lead", f"read_outcome IN ({listed})"
    )


def upgrade() -> None:
    _allow(AFTER)


def downgrade() -> None:
    op.execute(
        "UPDATE link_lead SET read_outcome = NULL WHERE read_outcome = 'not_a_new_treatment'"
    )
    _allow(BEFORE)
