"""Keep a record of each claim's registry search, and the identifiers an article's page names.

Revision ID: 0037
Revises: 0036

Adds the table `registry_search`: one row for each term of a claim's latest finished
search, with what came back or why the term was not sent. It starts empty, so every claim
is said never to have been searched until its search runs as a step of the work ledger.

Adds to `source_article` the registry numbers and paper DOIs its page names, so that the
step that looks them up can run apart from the read that joined the article. They are
identifiers only, never the article's text. Both start empty.
Behavior: openspec entity-resolution and lead-reading (change one-work-runner).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registry_search",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("ran_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported", sa.Integer(), nullable=True),
        sa.Column("kept", sa.Integer(), nullable=True),
        sa.Column("cut", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("not_sent_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(not_sent_reason IS NULL) = (reported IS NOT NULL)"
            " AND (reported IS NULL) = (kept IS NULL)",
            name=op.f("ck_registry_search_sent_or_why_not"),
        ),
        sa.CheckConstraint(
            "reported >= 0 AND kept >= 0", name=op.f("ck_registry_search_counts_not_negative")
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.id"], name=op.f("fk_registry_search_claim_id_claim")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registry_search")),
    )
    op.create_index(
        op.f("ix_registry_search_claim_id"), "registry_search", ["claim_id"], unique=False
    )
    for column in ("named_registry_numbers", "named_dois"):
        op.add_column(
            "source_article",
            sa.Column(column, postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        )


def downgrade() -> None:
    for column in ("named_dois", "named_registry_numbers"):
        op.drop_column("source_article", column)
    op.drop_index(op.f("ix_registry_search_claim_id"), table_name="registry_search")
    op.drop_table("registry_search")
