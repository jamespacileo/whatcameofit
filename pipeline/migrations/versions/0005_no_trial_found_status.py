"""allow the status of a claim studied in people with no trial found

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

BEFORE = (
    "preclinical_only",
    "trial_registered",
    "phase_1",
    "phase_2",
    "phase_3",
    "approved",
    "failed",
    "terminated",
    "retracted",
)
NAME = "ck_claim_current_status"


def _allow(statuses: tuple[str, ...]) -> None:
    listed = ", ".join(f"'{status}'" for status in statuses)
    op.execute(f"ALTER TABLE claim DROP CONSTRAINT {NAME}")
    op.execute(f"ALTER TABLE claim ADD CONSTRAINT {NAME} CHECK (current_status IN ({listed}))")


def upgrade() -> None:
    _allow((BEFORE[0], "no_trial_found", *BEFORE[1:]))
    # A claim with no trial found and a confirmed stage in people was stored as
    # preclinical only. A status with a trial behind it is left alone.
    op.execute(
        "UPDATE claim SET current_status = 'no_trial_found'"
        " WHERE current_status = 'preclinical_only'"
        " AND evidence_stage IN ('early_human', 'late_human')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE claim SET current_status = 'preclinical_only'"
        " WHERE current_status = 'no_trial_found'"
    )
    _allow(BEFORE)
