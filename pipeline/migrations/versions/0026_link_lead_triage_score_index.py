"""Index a link lead's triage score, which reading picks its next lead by.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The index was first made by hand on the working database on 2026-11-16, while a
    # batch was running; there it already exists.
    op.create_index(
        op.f("ix_link_lead_triage_score"),
        "link_lead",
        ["triage_score"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_link_lead_triage_score"), table_name="link_lead")
