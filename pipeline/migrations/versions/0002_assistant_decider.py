"""allow review decisions made by the assistant

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = ("claim", "entity_match", "evidence_event")


def _allow(table: str, deciders: tuple[str, ...]) -> None:
    name = f"ck_{table}_reviewed_by"
    listed = ", ".join(f"'{decider}'" for decider in deciders)
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK (reviewed_by IN ({listed}))")


def upgrade() -> None:
    for table in TABLES:
        _allow(table, ("human", "rule", "seed", "assistant"))


def downgrade() -> None:
    # Decisions the assistant made cannot be kept under the old list; they return to pending.
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET review_state = 'pending', reviewed_at = NULL, reviewed_by = NULL"
            " WHERE reviewed_by = 'assistant'"
        )
        _allow(table, ("human", "rule", "seed"))
