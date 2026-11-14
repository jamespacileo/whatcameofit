"""a subject term link can be a drug source's record of the intervention

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

BEFORE = ("condition", "intervention", "target")
ADDED = "drug"


def _allow(values: tuple[str, ...]) -> None:
    listed = ", ".join(f"'{value}'" for value in values)
    op.execute("ALTER TABLE claim_term DROP CONSTRAINT ck_claim_term_role")
    op.execute(f"ALTER TABLE claim_term ADD CONSTRAINT ck_claim_term_role CHECK (role IN ({listed}))")


def upgrade() -> None:
    _allow((*BEFORE, ADDED))


def downgrade() -> None:
    # A drug link has no place under the old list, and deleting it would lose a
    # decision. The operator removes them first, on purpose.
    held = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM claim_term WHERE role = :added"), {"added": ADDED})
        .scalar_one()
    )
    if held:
        raise RuntimeError(
            f"{held} row(s) of claim_term hold role {ADDED}, which the earlier schema does"
            " not allow. Delete those links first, then downgrade."
        )
    _allow(BEFORE)
