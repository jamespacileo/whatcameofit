"""record which step is done for which record, and hold registry trials and article leads

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_entry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("record_kind", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("step_version", sa.Integer(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum(
                "done",
                "nothing_found",
                "failed",
                name="outcome",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("requests_used", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("stale", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(outcome = 'failed') = (error IS NOT NULL)",
            name=op.f("ck_work_entry_failure_has_error"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_entry")),
        sa.UniqueConstraint(
            "record_kind",
            "record_id",
            "step",
            "step_version",
            name="uq_work_entry_record_step_version",
        ),
    )
    op.create_table(
        "source_allowance_use",
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requests_used", sa.Integer(), nullable=False),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refusals", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("source_name", name=op.f("pk_source_allowance_use")),
    )
    op.create_table(
        "registry_trial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registry_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("interventions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("phases", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("overall_status", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Text(), nullable=True),
        sa.Column("sponsor_class", sa.Text(), nullable=True),
        sa.Column("search_name", sa.Text(), nullable=True),
        sa.Column("search_indication", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registry_trial")),
        sa.UniqueConstraint(
            "registry_name", "external_id", name="uq_registry_trial_registry_external"
        ),
    )
    op.create_table(
        "registry_load",
        sa.Column("registry_name", sa.Text(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("loaded_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("registry_name", "condition", name=op.f("pk_registry_load")),
    )
    op.create_table(
        "article_lead",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registry_trial_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("outlet", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=True),
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
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("search_query", sa.Text(), nullable=False),
        sa.Column("raw_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registry_trial_id"],
            ["registry_trial.id"],
            name=op.f("fk_article_lead_registry_trial_id_registry_trial"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_article_lead")),
        sa.UniqueConstraint("registry_trial_id", "url", name="uq_article_lead_trial_url"),
    )
    op.create_index(
        op.f("ix_article_lead_registry_trial_id"),
        "article_lead",
        ["registry_trial_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_article_lead_registry_trial_id"), table_name="article_lead")
    op.drop_table("article_lead")
    op.drop_table("registry_load")
    op.drop_table("registry_trial")
    op.drop_table("source_allowance_use")
    op.drop_table("work_entry")
