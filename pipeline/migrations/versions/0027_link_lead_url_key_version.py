"""Record which form of the address key a link lead's key was made under.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import Column, Integer, text

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every lead already stored was keyed under the first form. Nothing is rewritten
    # here: `thenwhat backfill rekey-links` brings the leads to the current form.
    op.add_column(
        "link_lead",
        Column("url_key_version", Integer(), nullable=False, server_default=text("1")),
    )


def downgrade() -> None:
    op.drop_column("link_lead", "url_key_version")
