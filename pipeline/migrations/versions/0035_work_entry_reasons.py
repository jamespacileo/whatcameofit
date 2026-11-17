"""Let a ledger entry say a record is put off or needs a fix, and why.

Revision ID: 0035
Revises: 0034

Adds four empty columns to `work_entry`, two outcomes to the ones it allows, and two
checks: a record put off says until when, and one that waits says for what. No stored
entry is changed: every one holds an outcome that is still allowed.
Behavior: openspec work-ledger (change one-work-runner).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BEFORE = ("done", "nothing_found", "failed")
AFTER = ("done", "nothing_found", "later", "needs_fix", "failed")


def _allow(outcomes: Sequence[str]) -> None:
    op.drop_constraint(op.f("ck_work_entry_outcome"), "work_entry", type_="check")
    listed = ", ".join(f"'{outcome}'" for outcome in outcomes)
    op.create_check_constraint(
        op.f("ck_work_entry_outcome"), "work_entry", f"outcome IN ({listed})"
    )


def upgrade() -> None:
    op.add_column("work_entry", sa.Column("reason", sa.Text(), nullable=True))
    op.add_column("work_entry", sa.Column("reason_values", postgresql.JSONB(astext_type=sa.Text())))
    op.add_column("work_entry", sa.Column("not_before", sa.DateTime(timezone=True)))
    op.add_column("work_entry", sa.Column("first_put_off_at", sa.DateTime(timezone=True)))
    _allow(AFTER)
    op.create_check_constraint(
        op.f("ck_work_entry_later_has_time"),
        "work_entry",
        "(outcome = 'later') = (not_before IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_work_entry_waiting_has_reason"),
        "work_entry",
        "outcome NOT IN ('later', 'needs_fix') OR reason IS NOT NULL",
    )
    # What `thenwhat work requeue` and the plan look entries up by.
    op.create_index(
        "ix_work_entry_step_reason",
        "work_entry",
        ["step", "step_version", "reason"],
        postgresql_where=sa.text("reason IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_work_entry_step_reason", table_name="work_entry")
    op.drop_constraint(op.f("ck_work_entry_waiting_has_reason"), "work_entry", type_="check")
    op.drop_constraint(op.f("ck_work_entry_later_has_time"), "work_entry", type_="check")
    # An entry that says later or needs a fix has no place in the earlier ledger: its
    # record is simply due again there.
    op.execute("DELETE FROM work_entry WHERE outcome IN ('later', 'needs_fix')")
    _allow(BEFORE)
    for column in ("first_put_off_at", "not_before", "reason_values", "reason"):
        op.drop_column("work_entry", column)
