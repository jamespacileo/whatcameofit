"""Index three lookups that read whole tables, and check a link lead's claim.

Revision ID: 0029
Revises: 0028

Measured on a copy of the working database on 2026-11-16: a decision looked up by its
step and reference fell from 450 ms to 5 ms, a count of leads by read outcome from
1 s to under 1 ms, and a step's finished ledger entries from 170 ms to 4 ms.

Each index is built with the table closed to writes for a second or two, so run this
between batches.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MADE_OUTCOME_HAS_CLAIM = (
    "read_outcome IS NULL OR read_outcome NOT IN ('added_to_claim', 'new_claim')"
    " OR claim_id IS NOT NULL"
)


def upgrade() -> None:
    # Replaces the index on the step alone: this one serves those lookups too.
    op.create_index("ix_decision_log_step_input_ref", "decision_log", ["step", "input_ref"])
    op.drop_index(op.f("ix_decision_log_step"), table_name="decision_log")
    op.create_index("ix_work_entry_step_step_version", "work_entry", ["step", "step_version"])
    op.create_index(
        "ix_link_lead_read_outcome",
        "link_lead",
        ["read_outcome"],
        postgresql_where=sa.text("read_outcome IS NOT NULL"),
    )
    op.create_check_constraint(
        op.f("ck_link_lead_article_has_claim"),
        "link_lead",
        "source_article_id IS NULL OR claim_id IS NOT NULL",
    )
    op.create_check_constraint(
        op.f("ck_link_lead_made_outcome_has_claim"), "link_lead", MADE_OUTCOME_HAS_CLAIM
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_link_lead_made_outcome_has_claim"), "link_lead", type_="check")
    op.drop_constraint(op.f("ck_link_lead_article_has_claim"), "link_lead", type_="check")
    op.drop_index("ix_link_lead_read_outcome", table_name="link_lead")
    op.drop_index("ix_work_entry_step_step_version", table_name="work_entry")
    op.create_index(op.f("ix_decision_log_step"), "decision_log", ["step"], unique=False)
    op.drop_index("ix_decision_log_step_input_ref", table_name="decision_log")
