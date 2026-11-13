"""search phrases for an intervention with no product name, and a match's reasons

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entity",
        sa.Column("search_phrases", ARRAY(sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column(
        "entity_match",
        sa.Column("reasons", ARRAY(sa.Text()), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("entity_match", "reasons")
    op.drop_column("entity", "search_phrases")
