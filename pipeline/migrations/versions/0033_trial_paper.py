"""Keep the papers a paper index returns for a stored trial's registry number.

Revision ID: 0033
Revises: 0032

Only adds a table. Nothing already stored is read or rewritten.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trial_paper",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "registry_trial_id", sa.Integer(), sa.ForeignKey("registry_trial.id"), nullable=False
        ),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("pubmed_id", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "registry_trial_id",
            "source_name",
            "pubmed_id",
            name="uq_trial_paper_trial_source_paper",
        ),
    )
    op.create_index("ix_trial_paper_registry_trial_id", "trial_paper", ["registry_trial_id"])
    op.create_index("ix_trial_paper_pubmed_id", "trial_paper", ["pubmed_id"])


def downgrade() -> None:
    op.drop_table("trial_paper")
