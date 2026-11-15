"""hold link leads: article addresses people shared, their shares, links and labels

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "link_lead",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_key", sa.Text(), nullable=False),
        sa.Column("outlet", sa.Text(), nullable=False),
        sa.Column(
            "outlet_kind",
            sa.Enum(
                "general_news",
                "trade_press",
                "press_release",
                "unknown",
                name="outlet_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("first_shared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "screen_outcome",
            sa.Enum(
                "in_scope",
                "unlisted_outlet",
                "already_tracked",
                name="screen_outcome",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("triage_score", sa.Double(), nullable=True),
        sa.Column("triage_version", sa.Integer(), nullable=True),
        sa.Column(
            "read_outcome",
            sa.Enum(
                "added_to_claim",
                "new_claim",
                "cannot_be_read",
                "needs_vertical",
                "enough_articles",
                name="read_outcome",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("read_detail", sa.Text(), nullable=True),
        sa.Column("claim_id", sa.Integer(), nullable=True),
        sa.Column("source_article_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.id"], name=op.f("fk_link_lead_claim_id_claim")
        ),
        sa.ForeignKeyConstraint(
            ["source_article_id"],
            ["source_article.id"],
            name=op.f("fk_link_lead_source_article_id_source_article"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_link_lead")),
        sa.UniqueConstraint("url_key", name=op.f("uq_link_lead_url_key")),
    )
    op.create_index(op.f("ix_link_lead_claim_id"), "link_lead", ["claim_id"], unique=False)
    op.create_index(op.f("ix_link_lead_outlet"), "link_lead", ["outlet"], unique=False)
    op.create_table(
        "link_lead_label",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_lead_id", sa.Integer(), nullable=False),
        sa.Column(
            "label",
            sa.Enum(
                "treatment_report",
                "health_other",
                "not_health",
                name="label",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "labelled_by",
            sa.Enum(
                "human",
                "rule",
                "seed",
                "assistant",
                name="labelled_by",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("labelled_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "labelled_by IN ('human', 'assistant')",
            name=op.f("ck_link_lead_label_labelled_by_a_reader"),
        ),
        sa.ForeignKeyConstraint(
            ["link_lead_id"],
            ["link_lead.id"],
            name=op.f("fk_link_lead_label_link_lead_id_link_lead"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_link_lead_label")),
        sa.UniqueConstraint("link_lead_id", "labelled_by", name="uq_link_lead_label_lead_by"),
    )
    op.create_index(
        op.f("ix_link_lead_label_link_lead_id"), "link_lead_label", ["link_lead_id"], unique=False
    )
    op.create_table(
        "link_lead_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_lead_id", sa.Integer(), nullable=False),
        sa.Column("record_kind", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["link_lead_id"],
            ["link_lead.id"],
            name=op.f("fk_link_lead_link_link_lead_id_link_lead"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_link_lead_link")),
        sa.UniqueConstraint(
            "link_lead_id",
            "record_kind",
            "record_id",
            "reason",
            name="uq_link_lead_link_lead_record_reason",
        ),
    )
    op.create_index(
        op.f("ix_link_lead_link_link_lead_id"), "link_lead_link", ["link_lead_id"], unique=False
    )
    op.create_table(
        "link_share",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_lead_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("community", sa.Text(), nullable=False),
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("item_number", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["link_lead_id"], ["link_lead.id"], name=op.f("fk_link_share_link_lead_id_link_lead")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_link_share")),
        sa.UniqueConstraint(
            "link_lead_id",
            "platform",
            "community",
            "shared_at",
            name="uq_link_share_lead_place_time",
        ),
    )
    op.create_index(
        op.f("ix_link_share_link_lead_id"), "link_share", ["link_lead_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_link_share_link_lead_id"), table_name="link_share")
    op.drop_table("link_share")
    op.drop_index(op.f("ix_link_lead_link_link_lead_id"), table_name="link_lead_link")
    op.drop_table("link_lead_link")
    op.drop_index(op.f("ix_link_lead_label_link_lead_id"), table_name="link_lead_label")
    op.drop_table("link_lead_label")
    op.drop_index(op.f("ix_link_lead_outlet"), table_name="link_lead")
    op.drop_index(op.f("ix_link_lead_claim_id"), table_name="link_lead")
    op.drop_table("link_lead")
