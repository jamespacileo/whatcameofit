"""A claim with no confirmed evidence stage starts with no trial found.

Revision ID: 0022
Revises: 0021
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("claim", "current_status", server_default="no_trial_found")


def downgrade() -> None:
    op.alter_column("claim", "current_status", server_default="preclinical_only")
