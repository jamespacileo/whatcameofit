"""Merged claims, former slugs, and a registry search that is due again.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP = sa.TIMESTAMP(timezone=True)


def upgrade() -> None:
    # Every claim already in the database stays as it is: none is merged, none is due.
    op.add_column("claim", sa.Column("merged_into_id", sa.Integer(), nullable=True))
    op.add_column("claim", sa.Column("registry_search_due_at", TIMESTAMP, nullable=True))
    op.create_foreign_key(
        op.f("fk_claim_merged_into_id_claim"), "claim", "claim", ["merged_into_id"], ["id"]
    )
    op.create_index(op.f("ix_claim_merged_into_id"), "claim", ["merged_into_id"])
    op.create_check_constraint(
        op.f("ck_claim_merged_is_archived"),
        "claim",
        "merged_into_id IS NULL OR (archived_at IS NOT NULL AND merged_into_id <> id)",
    )
    op.create_table(
        "claim_change",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("into_claim_id", sa.Integer(), nullable=True),
        sa.Column("old_name", sa.Text(), nullable=True),
        sa.Column("new_name", sa.Text(), nullable=True),
        sa.Column("former_slug", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "decided_by",
            sa.Enum(
                "human",
                "rule",
                "seed",
                "assistant",
                name="decided_by",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("decided_at", TIMESTAMP, nullable=False),
        sa.CheckConstraint("kind IN ('merge', 'rename')", name=op.f("ck_claim_change_kind_known")),
        sa.CheckConstraint(
            "decided_by IN ('human', 'assistant')",
            name=op.f("ck_claim_change_decided_by_a_reader"),
        ),
        sa.CheckConstraint(
            "(kind = 'merge') = (into_claim_id IS NOT NULL)",
            name=op.f("ck_claim_change_merge_has_target"),
        ),
        sa.CheckConstraint(
            "(kind = 'rename') = (old_name IS NOT NULL) AND (kind = 'rename') ="
            " (new_name IS NOT NULL)",
            name=op.f("ck_claim_change_rename_has_names"),
        ),
        sa.CheckConstraint(
            "kind = 'rename' OR former_slug IS NULL",
            name=op.f("ck_claim_change_former_slug_of_a_rename"),
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.id"], name=op.f("fk_claim_change_claim_id_claim")
        ),
        sa.ForeignKeyConstraint(
            ["into_claim_id"], ["claim.id"], name=op.f("fk_claim_change_into_claim_id_claim")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim_change")),
        sa.UniqueConstraint("former_slug", name=op.f("uq_claim_change_former_slug")),
    )
    op.create_index(op.f("ix_claim_change_claim_id"), "claim_change", ["claim_id"])


def downgrade() -> None:
    op.drop_table("claim_change")
    op.drop_constraint(op.f("ck_claim_merged_is_archived"), "claim", type_="check")
    op.drop_index(op.f("ix_claim_merged_into_id"), table_name="claim")
    op.drop_constraint(op.f("fk_claim_merged_into_id_claim"), "claim", type_="foreignkey")
    op.drop_column("claim", "registry_search_due_at")
    op.drop_column("claim", "merged_into_id")
