"""Keep the applied plan and decisions of a registry drafting batch.

Revision ID: 0043
Revises: 0042
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_batch", sa.Column("draft_record", postgresql.JSONB(none_as_null=True)))


def downgrade() -> None:
    op.drop_column("audit_batch", "draft_record")
