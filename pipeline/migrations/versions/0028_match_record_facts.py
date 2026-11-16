"""Keep a matched trial's record field by field beside its one-line summary.

Revision ID: 0028
Revises: 0027

This migration and `0027_link_lead_url_key_version` were written on two branches and
both numbered 0027. A database migrated on either branch records "0027" and so has only
that branch's column. Both columns are therefore added here only where missing, which
brings a database from either branch, or from neither, to the same tables.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Matches already stored stay empty until `thenwhat entity record-facts` reads them.
    op.execute("ALTER TABLE entity_match ADD COLUMN IF NOT EXISTS record_facts JSONB")
    # Already there unless this database took the other 0027; see the note above.
    op.execute(
        "ALTER TABLE link_lead ADD COLUMN IF NOT EXISTS url_key_version INTEGER NOT NULL DEFAULT 1"
    )


def downgrade() -> None:
    op.drop_column("entity_match", "record_facts")
