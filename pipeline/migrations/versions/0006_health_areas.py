"""file claims under the revised health areas and give a claim an approach

Revision ID: 0006
Revises: 0005

The slugs are written out here rather than read from the configuration, so this
migration keeps meaning the same thing when the configuration changes later.
"""

from alembic import op
from sqlalchemy import Column, Text, text

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# The verticals that exist after this migration.
VERTICALS = (
    "ageing",
    "bones-joints-and-muscles",
    "brain-and-nerves",
    "cancer",
    "dementia",
    "diabetes-and-hormones",
    "eyes-and-ears",
    "gum-disease",
    "gut-and-liver",
    "heart-and-circulation",
    "immune-system-and-allergies",
    "infections",
    "kidneys-and-bladder",
    "lungs-and-breathing",
    "mental-health",
    "mouth-and-teeth",
    "pregnancy-and-fertility",
    "skin-and-hair",
)

RENAMED = {
    "allergies": "immune-system-and-allergies",
    "hair-loss": "skin-and-hair",
    "pain": "bones-joints-and-muscles",
    "sight-and-hearing": "eyes-and-ears",
}

# A vertical that splits: (old vertical, indication pattern, new vertical, approach or None).
# The first matching rule wins; the last rule for a vertical without a pattern catches the rest.
SPLITS = (
    ("dental-regeneration", "%periodont%", "gum-disease", None),
    ("dental-regeneration", None, "mouth-and-teeth", None),
    ("diabetes-and-metabolism", "%steatohepatitis%", "gut-and-liver", None),
    ("diabetes-and-metabolism", "%sleep apn%", "lungs-and-breathing", None),
    ("diabetes-and-metabolism", None, "diabetes-and-hormones", None),
    ("transplants", "%kidney%", "kidneys-and-bladder", "transplant"),
    ("transplants", "%infertil%", "pregnancy-and-fertility", "transplant"),
)


def upgrade() -> None:
    op.add_column("claim", Column("approach", Text, nullable=True))
    bind = op.get_bind()
    for old, new in RENAMED.items():
        bind.execute(
            text("UPDATE claim SET vertical = :new WHERE vertical = :old"), {"new": new, "old": old}
        )
    for old, pattern, new, approach in SPLITS:
        match = "" if pattern is None else " AND indication ILIKE :pattern"
        bind.execute(
            text(
                "UPDATE claim SET vertical = :new, approach = COALESCE(CAST(:approach AS TEXT), approach)"
                f" WHERE vertical = :old{match}"
            ),
            {"new": new, "old": old, "pattern": pattern, "approach": approach},
        )
    unplaced = bind.execute(
        text(
            "SELECT slug, vertical FROM claim WHERE NOT (vertical = ANY(:verticals)) ORDER BY slug"
        ),
        {"verticals": list(VERTICALS)},
    ).all()
    if unplaced:
        listed = ", ".join(f"{slug} ({vertical})" for slug, vertical in unplaced)
        raise RuntimeError(
            f"These claims fit no revised vertical: {listed}. Set each one's vertical to one of"
            " the revised verticals with 'claim edit --vertical' on the previous version, then"
            " upgrade again."
        )


def downgrade() -> None:
    bind = op.get_bind()
    back = {
        **{new: old for old, new in RENAMED.items()},
        "gum-disease": "dental-regeneration",
        "mouth-and-teeth": "dental-regeneration",
        "gut-and-liver": "diabetes-and-metabolism",
        "diabetes-and-hormones": "diabetes-and-metabolism",
    }
    bind.execute(
        text(
            "UPDATE claim SET vertical = 'transplants' WHERE approach = 'transplant'"
            " AND vertical IN ('kidneys-and-bladder', 'pregnancy-and-fertility')"
        )
    )
    bind.execute(
        text(
            "UPDATE claim SET vertical = 'diabetes-and-metabolism'"
            " WHERE vertical = 'lungs-and-breathing' AND indication ILIKE '%sleep apn%'"
        )
    )
    for new, old in back.items():
        bind.execute(
            text("UPDATE claim SET vertical = :old WHERE vertical = :new"), {"old": old, "new": new}
        )
    op.drop_column("claim", "approach")
