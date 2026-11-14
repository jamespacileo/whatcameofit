"""the index record a paper's facts are read from, without abstract or authors

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("pubmed_id", sa.Text(), nullable=True),
        sa.Column("payload", JSONB(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_record")),
        sa.UniqueConstraint("identifier", name=op.f("uq_paper_record_identifier")),
    )
    op.create_index(op.f("ix_paper_record_pubmed_id"), "paper_record", ["pubmed_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_paper_record_pubmed_id"), table_name="paper_record")
    op.drop_table("paper_record")
