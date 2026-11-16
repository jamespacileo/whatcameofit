"""Have the database keep rules that only the code kept.

Revision ID: 0030
Revises: 0029

A claim has one intervention entity. A promise, a reported statement and a link lead
name their article's own claim, and a failure flag its event's own. Counts and costs are
never negative.

Not checked: that a published claim is approved. `published_at` is when a claim was first
published, and it stays when the claim is later rejected.

On 2026-11-16 the working database held no row that breaks any of these.

Also indexes the foreign keys that had none, and writes the check on a reading's code
in the order the models give its values, so that the two can be compared as text.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Table, name and condition of each check.
CHECKS = [
    (
        "llm_usage",
        "amounts_not_negative",
        "input_tokens >= 0 AND output_tokens >= 0 AND cost_usd >= 0",
    ),
    ("work_entry", "counts_not_negative", "attempts >= 0 AND requests_used >= 0"),
    ("source_allowance_use", "counts_not_negative", "requests_used >= 0 AND refusals >= 0"),
]

# Table and name of each foreign key that holds a row to its article's own claim.
ARTICLE_OF_CLAIM = [
    ("promise", "fk_promise_article_of_claim"),
    ("reported_statement", "fk_reported_statement_article_of_claim"),
    ("link_lead", "fk_link_lead_article_of_claim"),
]

# Table and column of each foreign key that had no index.
FOREIGN_KEYS = [
    ("promise", "source_article_id"),
    ("entity_article", "source_article_id"),
    ("evidence_event", "entity_match_id"),
    ("failure_flag", "evidence_event_id"),
]

MEASURE_CODES = [
    "symptom_score",
    "frequency",
    "body_measure",
    "scan_finding",
    "survival",
    "side_effects",
    "use_of_treatment",
    "physical_test",
    "quality_of_life",
    "other",
]


def upgrade() -> None:
    op.create_index(
        "uq_entity_intervention_per_claim",
        "entity",
        ["claim_id"],
        unique=True,
        postgresql_where=sa.text("type = 'intervention'"),
    )
    for table, name, condition in CHECKS:
        op.create_check_constraint(op.f(f"ck_{table}_{name}"), table, condition)

    op.create_unique_constraint("uq_source_article_id_claim", "source_article", ["id", "claim_id"])
    for table, name in ARTICLE_OF_CLAIM:
        # An article moved to another claim, as a duplicate's are, takes the row with it.
        op.create_foreign_key(
            name,
            table,
            "source_article",
            ["source_article_id", "claim_id"],
            ["id", "claim_id"],
            onupdate="CASCADE",
        )
    op.create_unique_constraint("uq_evidence_event_id_claim", "evidence_event", ["id", "claim_id"])
    op.create_foreign_key(
        "fk_failure_flag_event_of_claim",
        "failure_flag",
        "evidence_event",
        ["evidence_event_id", "claim_id"],
        ["id", "claim_id"],
    )

    for table, column in FOREIGN_KEYS:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column])
    op.create_index(
        "ix_link_lead_source_article_id",
        "link_lead",
        ["source_article_id"],
        postgresql_where=sa.text("source_article_id IS NOT NULL"),
    )

    # The same values as before, in the models' order.
    op.drop_constraint(op.f("ck_reading_code"), "reading", type_="check")
    listed = ", ".join(f"'{code}'" for code in MEASURE_CODES)
    op.create_check_constraint(op.f("ck_reading_code"), "reading", f"code IN ({listed})")


def downgrade() -> None:
    # The check on a reading's code stays as it is: it allows the same values.
    op.drop_index("ix_link_lead_source_article_id", table_name="link_lead")
    for table, column in reversed(FOREIGN_KEYS):
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)

    op.drop_constraint("fk_failure_flag_event_of_claim", "failure_flag", type_="foreignkey")
    op.drop_constraint("uq_evidence_event_id_claim", "evidence_event", type_="unique")
    for table, name in reversed(ARTICLE_OF_CLAIM):
        op.drop_constraint(name, table, type_="foreignkey")
    op.drop_constraint("uq_source_article_id_claim", "source_article", type_="unique")

    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
    op.drop_index("uq_entity_intervention_per_claim", table_name="entity")
