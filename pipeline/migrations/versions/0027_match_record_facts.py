"""Keep a matched trial's record field by field beside its one-line summary.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Matches already stored stay empty until `thenwhat entity record-facts` reads them.
    op.add_column("entity_match", Column("record_facts", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("entity_match", "record_facts")
