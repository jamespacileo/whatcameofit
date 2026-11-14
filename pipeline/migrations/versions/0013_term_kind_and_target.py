"""a subject term link can be a kind link, and can be for a named gene

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

ROLE = ("role", ("condition", "intervention"), ("target",))
FIT = ("fit", ("exact", "broader"), ("kind",))


def _allow(column: str, values: tuple[str, ...]) -> None:
    name = f"ck_claim_term_{column}"
    listed = ", ".join(f"'{value}'" for value in values)
    op.execute(f"ALTER TABLE claim_term DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE claim_term ADD CONSTRAINT {name} CHECK ({column} IN ({listed}))")


def upgrade() -> None:
    for column, before, added in (ROLE, FIT):
        _allow(column, before + added)


def downgrade() -> None:
    # A kind link or a named-gene link has no place under the old lists, and deleting
    # it would lose a decision. The operator removes them first, on purpose.
    connection = op.get_bind()
    for column, _, added in (ROLE, FIT):
        held = connection.execute(
            sa.text(f"SELECT count(*) FROM claim_term WHERE {column} = ANY(:added)"),
            {"added": list(added)},
        ).scalar_one()
        if held:
            raise RuntimeError(
                f"{held} row(s) of claim_term hold {column} {', '.join(added)}, which the"
                " earlier schema does not allow. Delete those links first, then downgrade."
            )
    for column, before, _ in (ROLE, FIT):
        _allow(column, before)
