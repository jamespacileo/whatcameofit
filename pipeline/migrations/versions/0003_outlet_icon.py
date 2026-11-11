"""keep one icon per outlet domain

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outlet_icon",
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("icon_url", sa.Text(), nullable=True),
        sa.Column("media_type", sa.Text(), nullable=True),
        sa.Column("content", sa.LargeBinary(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(content IS NULL) = (media_type IS NULL) AND (content IS NULL) = (icon_url IS NULL)",
            name=op.f("ck_outlet_icon_icon_is_whole"),
        ),
        sa.PrimaryKeyConstraint("domain", name=op.f("pk_outlet_icon")),
    )


def downgrade() -> None:
    op.drop_table("outlet_icon")
