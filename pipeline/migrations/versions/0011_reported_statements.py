"""reported statements: what a source article says, in the site's own words

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _choice(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def upgrade() -> None:
    op.create_table(
        "reported_statement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("source_article_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_key", sa.Text(), nullable=False),
        sa.Column(
            "kind",
            _choice(
                "kind",
                "effect",
                "safety",
                "how_it_works",
                "who_it_could_help",
                "comparison",
                "what_it_could_lead_to",
            ),
            nullable=False,
        ),
        sa.Column("firmness", _choice("firmness", "fact", "possibility"), nullable=False),
        sa.Column(
            "speaker",
            _choice("speaker", "article", "researcher", "company", "patient", "other_expert"),
            nullable=False,
        ),
        sa.Column(
            "basis", _choice("basis", "people", "animals", "laboratory", "not_said"), nullable=False
        ),
        sa.Column("confidence", sa.Double(), nullable=False),
        sa.Column("decision_ref", sa.Text(), nullable=False),
        sa.Column("article_read_at", sa.DateTime(timezone=True), nullable=False),
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
            name=op.f("ck_reported_statement_review_decision_recorded"),
        ),
        sa.CheckConstraint(
            "char_length(text) BETWEEN 1 AND 200", name=op.f("ck_reported_statement_text_length")
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_reported_statement_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.id"], name=op.f("fk_reported_statement_claim_id_claim")
        ),
        sa.ForeignKeyConstraint(
            ["source_article_id"],
            ["source_article.id"],
            name=op.f("fk_reported_statement_source_article_id_source_article"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reported_statement")),
        sa.UniqueConstraint(
            "source_article_id", "text_key", name="uq_reported_statement_article_text_key"
        ),
    )
    op.create_index(
        op.f("ix_reported_statement_claim_id"), "reported_statement", ["claim_id"], unique=False
    )
    op.create_index(
        op.f("ix_reported_statement_source_article_id"),
        "reported_statement",
        ["source_article_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reported_statement_source_article_id"), table_name="reported_statement")
    op.drop_index(op.f("ix_reported_statement_claim_id"), table_name="reported_statement")
    op.drop_table("reported_statement")
