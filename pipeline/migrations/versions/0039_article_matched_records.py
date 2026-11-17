"""Keep the trials and papers an upstream verifier matched exactly to each article.

Revision ID: 0039
Revises: 0038

Adds to `source_article` the registry numbers, canonical paper DOIs and PubMed numbers
matched exactly to the article, each kind in its own column and apart from what its page
names (`named_registry_numbers`, `named_dois`). They are identifiers only, never the
article's text. All start empty, so an article from before has none and is handled as
before. Behavior: openspec lead-reading.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("matched_registry_numbers", "matched_dois", "matched_pubmed_ids")


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column(
            "source_article",
            sa.Column(column, postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        )


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column("source_article", column)
