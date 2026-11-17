"""Keep how much a lead's link to a trial says, and what it was made on.

Revision ID: 0034
Revises: 0033

Only adds: three empty columns, a check on one of them and a partial index. A link made
before screening version 3 keeps them empty until its lead is screened again.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STRENGTHS = "strength IN ('exact', 'strong')"


def upgrade() -> None:
    for column in ("strength", "term", "beside"):
        op.add_column("link_lead_link", sa.Column(column, sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_link_lead_link_strength_is_known"),
        "link_lead_link",
        "strength IS NULL OR strength IN ('exact', 'strong', 'named', 'candidate')",
    )
    op.create_index(
        "ix_link_lead_link_strong",
        "link_lead_link",
        ["record_id", "link_lead_id"],
        postgresql_where=sa.text(STRENGTHS),
    )


def downgrade() -> None:
    op.drop_index("ix_link_lead_link_strong", table_name="link_lead_link")
    op.drop_constraint(op.f("ck_link_lead_link_strength_is_known"), "link_lead_link")
    for column in ("beside", "term", "strength"):
        op.drop_column("link_lead_link", column)
