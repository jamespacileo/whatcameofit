"""subject terms proposed for a claim, and each term's own record

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _choice(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def upgrade() -> None:
    op.create_table(
        "term_record",
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_name", "external_id", name=op.f("pk_term_record")),
    )
    op.create_table(
        "claim_term",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("role", _choice("role", "condition", "intervention"), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("fit", _choice("fit", "exact", "broader"), nullable=True),
        sa.Column("reasons", JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "review_state",
            _choice("review_state", "pending", "approved", "rejected"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by",
            _choice("reviewed_by", "human", "rule", "seed", "assistant"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(review_state = 'pending') = (reviewed_at IS NULL)"
            " AND (reviewed_at IS NULL) = (reviewed_by IS NULL)",
            name=op.f("ck_claim_term_review_decision_recorded"),
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name=op.f("ck_claim_term_score_range")),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.id"], name=op.f("fk_claim_term_claim_id_claim")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim_term")),
        sa.UniqueConstraint(
            "claim_id",
            "role",
            "source_name",
            "external_id",
            name="uq_claim_term_claim_role_source_external",
        ),
    )
    op.create_index(op.f("ix_claim_term_claim_id"), "claim_term", ["claim_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_term_claim_id"), table_name="claim_term")
    op.drop_table("claim_term")
    op.drop_table("term_record")
