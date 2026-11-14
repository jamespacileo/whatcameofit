"""the substance an intervention is listed under, with its development codes

Revision ID: 0013
Revises: 0011

Numbered 0013 because the organisations change holds 0012 and is not merged yet. When
it is, this revision is re-chained onto 0012.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0013"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_substance",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("codes", ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_entity_substance_entity_id_entity")
        ),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_entity_substance")),
    )


def downgrade() -> None:
    op.drop_table("entity_substance")
