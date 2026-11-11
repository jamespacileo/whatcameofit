"""keep what a candidate's registry record says, for the review queue

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("entity_match", sa.Column("record_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("entity_match", "record_summary")
