"""record readings: what a model read from a trial's stored record, checked by rule

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _choice(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def upgrade() -> None:
    op.create_table(
        "trial_read",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("trial_id", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("instructions_version", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("refusals", JSONB(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trial_read")),
        sa.UniqueConstraint("source_name", "trial_id", name="uq_trial_read_trial"),
    )
    op.create_table(
        "reading",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trial_read_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.Integer(), nullable=False),
        sa.Column("kind", _choice("kind", "follow_up", "measure"), nullable=False),
        sa.Column("field", _choice("field", "time_frame", "measure"), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("unit", _choice("unit", "days", "weeks", "months", "years"), nullable=True),
        sa.Column(
            "code",
            _choice(
                "code",
                "symptom_score",
                "frequency",
                "body_measure",
                "scan_finding",
                "survival",
                "side_effects",
                "use_of_treatment",
                "quality_of_life",
                "other",
            ),
            nullable=True,
        ),
        sa.Column("confidence", sa.Double(), nullable=False),
        sa.Column("decided_by", _choice("decided_by", "model"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name=op.f("ck_reading_confidence_range")
        ),
        sa.CheckConstraint("outcome >= 0", name=op.f("ck_reading_outcome_index")),
        sa.CheckConstraint("char_length(words) > 0", name=op.f("ck_reading_words_present")),
        sa.CheckConstraint(
            "(kind = 'follow_up') = (number IS NOT NULL)"
            " AND (kind = 'follow_up') = (unit IS NOT NULL)"
            " AND (kind = 'measure') = (code IS NOT NULL)",
            name=op.f("ck_reading_value_fits_kind"),
        ),
        sa.CheckConstraint(
            "(kind = 'follow_up') = (field = 'time_frame')",
            name=op.f("ck_reading_field_fits_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["trial_read_id"],
            ["trial_read.id"],
            name=op.f("fk_reading_trial_read_id_trial_read"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reading")),
        sa.UniqueConstraint("trial_read_id", "outcome", "kind", name="uq_reading_outcome_kind"),
    )
    op.create_index(op.f("ix_reading_trial_read_id"), "reading", ["trial_read_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reading_trial_read_id"), table_name="reading")
    op.drop_table("reading")
    op.drop_table("trial_read")
