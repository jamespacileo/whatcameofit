"""Hold a claim that prepare approved off the site until its batch has been audited.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import TIMESTAMP, Column

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every claim already in the database stays as it is: nothing existing is held.
    op.add_column("claim", Column("awaiting_audit_at", TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("claim", "awaiting_audit_at")
