"""Keep each day's measurements as totals, and what each claim took.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "measure_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("step_version", sa.Integer(), nullable=False),
        sa.Column("writer", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("spans", sa.Integer(), nullable=False),
        sa.Column("records", sa.Integer(), nullable=False),
        sa.Column("reused", sa.Integer(), nullable=False),
        sa.Column("ran_seconds", sa.Float(), nullable=False),
        sa.Column("waited_seconds", sa.Float(), nullable=False),
        sa.Column("waited_by_cause", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requests_by_source", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("inner_cost_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("rows_written", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measure_daily")),
        sa.UniqueConstraint(
            "day", "step", "step_version", "writer", "outcome", name="uq_measure_daily_key"
        ),
    )
    op.create_index(op.f("ix_measure_daily_day"), "measure_daily", ["day"], unique=False)
    op.create_table(
        "measure_claim",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_step_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("spans", sa.Integer(), nullable=False),
        sa.Column("ran_seconds", sa.Float(), nullable=False),
        sa.Column("waited_seconds", sa.Float(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.id"], name=op.f("fk_measure_claim_claim_id_claim")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measure_claim")),
        sa.UniqueConstraint("claim_id", name=op.f("uq_measure_claim_claim_id")),
    )
    op.create_table(
        "measure_rolled_day",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("rolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("day", name=op.f("pk_measure_rolled_day")),
    )


def downgrade() -> None:
    op.drop_table("measure_rolled_day")
    op.drop_table("measure_claim")
    op.drop_index(op.f("ix_measure_daily_day"), table_name="measure_daily")
    op.drop_table("measure_daily")
