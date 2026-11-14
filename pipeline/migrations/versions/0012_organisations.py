"""where an entity was named, the articles that named an organisation, and each
organisation's own registry record

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Every existing entity was read from a source article.
    op.add_column(
        "entity",
        sa.Column("named_by", ARRAY(sa.Text()), server_default="{article}", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_entity_named_by_known"),
        "entity",
        "cardinality(named_by) > 0 AND named_by <@ ARRAY['article', 'registry']::text[]",
    )
    op.create_table(
        "entity_article",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("source_article_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_entity_article_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["source_article_id"],
            ["source_article.id"],
            name=op.f("fk_entity_article_source_article_id_source_article"),
        ),
        sa.PrimaryKeyConstraint("entity_id", "source_article_id", name=op.f("pk_entity_article")),
    )
    # Which article named an organisation was not recorded before. On a claim with one
    # article it can only be that one; on a claim with several it stays unknown.
    op.execute(
        "INSERT INTO entity_article (entity_id, source_article_id)"
        " SELECT entity.id, source_article.id FROM entity"
        " JOIN source_article ON source_article.claim_id = entity.claim_id"
        " WHERE entity.type IN ('institution', 'company') AND entity.claim_id IN"
        " (SELECT claim_id FROM source_article GROUP BY claim_id HAVING count(*) = 1)"
    )
    op.create_table(
        "organisation_record",
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_name", "external_id", name=op.f("pk_organisation_record")),
    )


def downgrade() -> None:
    op.drop_table("organisation_record")
    op.drop_table("entity_article")
    op.drop_constraint(op.f("ck_entity_named_by_known"), "entity", type_="check")
    op.drop_column("entity", "named_by")
