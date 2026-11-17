"""Record who set a claim's approach, and what a rule set it on.

Revision ID: 0035
Revises: 0034

Only adds: two empty columns on the claim and two checks. An approach stored before
this keeps both empty, which marks it as not set by rule (openspec health-areas).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECIDERS = ("human", "rule", "seed", "assistant")


def upgrade() -> None:
    op.add_column(
        "claim",
        sa.Column(
            "approach_decided_by",
            sa.Enum(
                *DECIDERS,
                name="approach_decided_by",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "claim",
        sa.Column("approach_basis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_claim_approach_record_has_approach"),
        "claim",
        "approach IS NOT NULL OR (approach_decided_by IS NULL AND approach_basis IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_claim_approach_basis_is_a_rules"),
        "claim",
        "approach_basis IS NULL OR approach_decided_by = 'rule'",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_claim_approach_basis_is_a_rules"), "claim")
    op.drop_constraint(op.f("ck_claim_approach_record_has_approach"), "claim")
    op.drop_column("claim", "approach_basis")
    op.drop_column("claim", "approach_decided_by")
