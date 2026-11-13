"""let the operator take a published claim off the site by archiving it

Revision ID: 0007
Revises: 0006
"""

from alembic import op
from sqlalchemy import TIMESTAMP, Column, Text

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claim", Column("archived_at", TIMESTAMP(timezone=True), nullable=True))
    op.add_column("claim", Column("archive_reason", Text, nullable=True))
    op.create_check_constraint(
        op.f("ck_claim_archive_has_reason"),
        "claim",
        "(archived_at IS NULL) = (archive_reason IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_claim_archive_has_reason"), "claim", type_="check")
    op.drop_column("claim", "archive_reason")
    op.drop_column("claim", "archived_at")
