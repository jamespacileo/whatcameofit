"""Keep what the registry states of a stored trial's activity and results.

Revision ID: 0031
Revises: 0030

Only adds: every new column is empty until the trials are loaded again with the wider
record, and nothing already stored is rewritten, so its place in the order does not
matter to the data.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import Boolean, Column, Date, Text, text

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEXT_COLUMNS = (
    "start_date_type",
    "primary_completion_date",
    "primary_completion_date_type",
    "completion_date",
    "completion_date_type",
    "acronym",
    "lead_sponsor_name",
)
DATE_COLUMNS = ("last_update_posted", "study_first_posted", "results_first_posted")


def upgrade() -> None:
    for name in TEXT_COLUMNS:
        op.add_column("registry_trial", Column(name, Text(), nullable=True))
    for name in DATE_COLUMNS:
        op.add_column("registry_trial", Column(name, Date(), nullable=True))
    op.add_column("registry_trial", Column("has_results", Boolean(), nullable=True))
    op.create_index(
        "ix_registry_trial_last_update_posted", "registry_trial", ["last_update_posted"]
    )
    op.create_index("ix_registry_trial_overall_status", "registry_trial", ["overall_status"])
    op.create_index(
        "ix_registry_trial_completion_with_results",
        "registry_trial",
        ["completion_date"],
        postgresql_where=text("has_results AND completion_date_type = 'ACTUAL'"),
    )


def downgrade() -> None:
    op.drop_index("ix_registry_trial_completion_with_results", table_name="registry_trial")
    op.drop_index("ix_registry_trial_overall_status", table_name="registry_trial")
    op.drop_index("ix_registry_trial_last_update_posted", table_name="registry_trial")
    for name in ("has_results", *DATE_COLUMNS, *TEXT_COLUMNS):
        op.drop_column("registry_trial", name)
