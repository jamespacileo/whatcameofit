"""Note when a paper the index no longer answered for was asked, so it waits its age.

Revision ID: 0035
Revises: 0034

Only adds one empty column. A stored paper the index answered nothing for is kept as it
was; this says when it was asked, so it is not asked again on every run.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("paper_record", sa.Column("asked_at", sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_record", "asked_at")
