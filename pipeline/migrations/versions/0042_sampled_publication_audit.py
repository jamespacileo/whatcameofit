"""Record the population, draw and judgments for a publication audit.

Revision ID: 0042
Revises: 0041
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_batch",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column("claim", sa.Column("audit_batch", sa.Text()))
    op.create_foreign_key(
        "fk_claim_audit_batch_audit_batch", "claim", "audit_batch", ["audit_batch"], ["name"]
    )
    op.create_index("ix_claim_audit_batch", "claim", ["audit_batch"])
    op.add_column("claim", sa.Column("audit_cleared_at", sa.DateTime(timezone=True)))
    op.create_table(
        "audit_sample",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch", sa.Text(), sa.ForeignKey("audit_batch.name"), nullable=False),
        sa.Column("seed", sa.Text(), nullable=False),
        sa.Column("population_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("claim_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("drawn_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("spot_seed", sa.Text()),
        sa.Column("spot_claim_ids", postgresql.ARRAY(sa.Integer())),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("max_wrong_share", sa.Numeric()),
        sa.CheckConstraint("cardinality(claim_ids) > 0", name="has_claims"),
        sa.CheckConstraint("claim_ids <@ population_ids", name="sample_in_population"),
        sa.CheckConstraint("spot_claim_ids <@ claim_ids", name="spot_check_in_sample"),
        sa.CheckConstraint(
            "(spot_seed IS NULL) = (spot_claim_ids IS NULL)", name="spot_check_has_seed"
        ),
        sa.CheckConstraint(
            "max_wrong_share >= 0 AND max_wrong_share <= 1", name="figure_is_fraction"
        ),
    )
    op.create_index("ix_audit_sample_batch", "audit_sample", ["batch"])
    op.create_table(
        "audit_judgement",
        sa.Column("sample_id", sa.Integer(), sa.ForeignKey("audit_sample.id"), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claim.id"), primary_key=True),
        sa.Column(
            "judged_by",
            sa.Enum(
                "human",
                "rule",
                "seed",
                "assistant",
                name="judged_by",
                length=32,
                native_enum=False,
                create_constraint=True,
            ),
            primary_key=True,
        ),
        sa.Column("reviewer", sa.Text(), nullable=False),
        sa.Column("judged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("facts_sha256", sa.Text(), nullable=False),
        sa.Column("is_right", sa.Boolean(), nullable=False),
        sa.Column("category", sa.Text()),
        sa.Column("detail", sa.Text()),
        sa.CheckConstraint("judged_by IN ('human', 'assistant')", name="judged_by_a_reader"),
        sa.CheckConstraint(
            "(is_right AND category IS NULL AND detail IS NULL)"
            " OR (NOT is_right AND category IS NOT NULL AND detail IS NOT NULL)",
            name="wrong_has_defect",
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_judgement")
    op.drop_table("audit_sample")
    op.drop_column("claim", "audit_cleared_at")
    op.drop_column("claim", "audit_batch")
    op.drop_table("audit_batch")
