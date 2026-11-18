"""Record what each claim was drafted from, and let a registry-drafted claim go without text.

Revision ID: 0040
Revises: 0039

Adds to `claim` what it was drafted from (`drafted_from`: article, registry or operator)
and the registry trial IDs a claim drafted from registry records was drafted from
(`drafting_trial_ids`). A claim from before has no recorded origin, which is left empty
rather than guessed, and no drafting trials. The headline and summary may now be empty,
but only on a claim drafted from registry records, which must name at least one trial;
every other claim, including one with no recorded origin, keeps both and names no
drafting trial. A registry-drafted claim that later gains an article keeps its origin.
Behavior: openspec claims.

The downgrade refuses, before changing anything, while any claim is drafted from
registry records: such a claim may have no headline or summary, and its origin would be
lost.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DRAFTED_FROM_VALUES = ("article", "registry", "operator")


def upgrade() -> None:
    op.add_column("claim", sa.Column("drafted_from", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        op.f("ck_claim_drafted_from"),
        "claim",
        "drafted_from IN ({})".format(", ".join(f"'{value}'" for value in DRAFTED_FROM_VALUES)),
    )
    op.add_column(
        "claim",
        sa.Column(
            "drafting_trial_ids",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.alter_column("claim", "headline", existing_type=sa.Text(), nullable=True)
    op.alter_column("claim", "summary", existing_type=sa.Text(), nullable=True)
    op.create_check_constraint(
        op.f("ck_claim_registry_draft_has_trials"),
        "claim",
        "drafted_from IS DISTINCT FROM 'registry' OR cardinality(drafting_trial_ids) > 0",
    )
    op.create_check_constraint(
        op.f("ck_claim_non_registry_draft_has_text"),
        "claim",
        "drafted_from IS NOT DISTINCT FROM 'registry' OR (cardinality(drafting_trial_ids) = 0"
        " AND headline IS NOT NULL AND summary IS NOT NULL)",
    )


def downgrade() -> None:
    registry_drafted = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM claim WHERE drafted_from = 'registry'"))
        .scalar_one()
    )
    if registry_drafted:
        raise RuntimeError(
            f"Cannot downgrade 0040: {registry_drafted} claim(s) were drafted from registry"
            " records. Their origin would be lost and they may have no headline or summary."
        )
    op.drop_constraint(op.f("ck_claim_non_registry_draft_has_text"), "claim", type_="check")
    op.drop_constraint(op.f("ck_claim_registry_draft_has_trials"), "claim", type_="check")
    op.alter_column("claim", "summary", existing_type=sa.Text(), nullable=False)
    op.alter_column("claim", "headline", existing_type=sa.Text(), nullable=False)
    op.drop_column("claim", "drafting_trial_ids")
    op.drop_constraint(op.f("ck_claim_drafted_from"), "claim", type_="check")
    op.drop_column("claim", "drafted_from")
