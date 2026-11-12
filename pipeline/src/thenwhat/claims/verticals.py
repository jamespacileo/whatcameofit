"""The health areas a claim is filed under: groups, verticals and approaches.

A group is a body system or disease area a reader recognises. Each group has a
general vertical with the group's own slug, and may have specific verticals that
split out of it once they would hold about five claims. Every vertical has
exactly one group.

Each group is anchored to one or more UKCRC Health Research Classification System
(HRCS) health categories, so the tree can be checked for completeness. The
anchors are internal: neither the export nor the site carries them. HRCS is
licensed CC BY-NC-ND 2.0 England & Wales by the UK Clinical Research
Collaboration (https://hrcsonline.net/); the category names below are quoted
unaltered. See docs/sources.md.

Add a group to GROUPS and GROUP_ANCHORS, and its general vertical to VERTICALS
and VERTICAL_GROUPS. Before launch a slug can simply change. After launch, record
a renamed or retired vertical in RETIRED_VERTICALS with its successor.
"""

from collections.abc import Mapping

# The HRCS health categories, as named at https://hrcsonline.net/health-categories/.
HRCS_CATEGORIES: tuple[str, ...] = (
    "Blood",
    "Cancer and neoplasms",
    "Cardiovascular",
    "Congenital disorders",
    "Ear",
    "Eye",
    "Infection",
    "Inflammatory and immune system",
    "Injuries and accidents",
    "Mental health",
    "Metabolic and endocrine",
    "Musculoskeletal",
    "Neurological",
    "Oral and gastrointestinal",
    "Renal and urogenital",
    "Reproductive health and childbirth",
    "Respiratory",
    "Skin",
    "Stroke",
    "Generic health relevance",
    "Disputed aetiology and other",
)

# Categories no group has to cover. A congenital condition is filed by the body
# system it affects.
HRCS_EXEMPT: frozenset[str] = frozenset(
    ["Generic health relevance", "Disputed aetiology and other", "Congenital disorders"]
)

# Group slug to display title.
GROUPS: dict[str, str] = {
    "ageing": "Ageing",
    "bones-joints-and-muscles": "Bones, joints and muscles",
    "brain-and-nerves": "Brain and nerves",
    "cancer": "Cancer",
    "diabetes-and-hormones": "Diabetes, weight and hormones",
    "eyes-and-ears": "Eyes and ears",
    "gut-and-liver": "Gut and liver",
    "heart-and-circulation": "Heart, blood and circulation",
    "immune-system-and-allergies": "Immune system and allergies",
    "infections": "Infections",
    "kidneys-and-bladder": "Kidneys and bladder",
    "lungs-and-breathing": "Lungs and breathing",
    "mental-health": "Mental health",
    "mouth-and-teeth": "Mouth and teeth",
    "pregnancy-and-fertility": "Pregnancy and fertility",
    "skin-and-hair": "Skin and hair",
}

# Group slug to the HRCS categories it covers.
GROUP_ANCHORS: dict[str, tuple[str, ...]] = {
    "ageing": ("Generic health relevance",),
    "bones-joints-and-muscles": ("Musculoskeletal", "Injuries and accidents"),
    "brain-and-nerves": ("Neurological", "Stroke"),
    "cancer": ("Cancer and neoplasms",),
    "diabetes-and-hormones": ("Metabolic and endocrine",),
    "eyes-and-ears": ("Eye", "Ear"),
    "gut-and-liver": ("Oral and gastrointestinal",),
    "heart-and-circulation": ("Cardiovascular", "Blood"),
    "immune-system-and-allergies": ("Inflammatory and immune system",),
    "infections": ("Infection",),
    "kidneys-and-bladder": ("Renal and urogenital",),
    "lungs-and-breathing": ("Respiratory",),
    "mental-health": ("Mental health",),
    "mouth-and-teeth": ("Oral and gastrointestinal",),
    "pregnancy-and-fertility": ("Reproductive health and childbirth",),
    "skin-and-hair": ("Skin",),
}

# Specific verticals: slug to (title, group slug).
_SPECIFIC: dict[str, tuple[str, str]] = {
    "dementia": ("Dementia", "brain-and-nerves"),
    "gum-disease": ("Gum disease", "mouth-and-teeth"),
}

# Vertical slug to display title: each group's general vertical, then the specific ones.
VERTICALS: dict[str, str] = {
    **GROUPS,
    **{slug: title for slug, (title, _) in _SPECIFIC.items()},
}

# Vertical slug to group slug.
VERTICAL_GROUPS: dict[str, str] = {
    **{slug: slug for slug in GROUPS},
    **{slug: group for slug, (_, group) in _SPECIFIC.items()},
}

# A vertical slug renamed or retired after launch, to the vertical that replaces it.
RETIRED_VERTICALS: dict[str, str] = {
    "allergies": "immune-system-and-allergies",
    "dental-regeneration": "mouth-and-teeth",
    "diabetes-and-metabolism": "diabetes-and-hormones",
    "hair-loss": "skin-and-hair",
    "pain": "bones-joints-and-muscles",
    "sight-and-hearing": "eyes-and-ears",
}

# Approach code to a description for operators. The site owns the public wording.
APPROACHES: dict[str, str] = {
    "drug": "A medicine, including biologics such as antibodies and phage therapy",
    "vaccine": "A vaccine, preventive or therapeutic",
    "gene-therapy": "Changing, adding or instructing genes, including gene editing and mRNA",
    "cell-therapy": "Living cells given as treatment, including stem cells",
    "tissue-regeneration": "Regrowing tissue with scaffolds, signals or materials",
    "transplant": "Transplanting an organ or tissue",
    "device": "A device or implant",
    "surgery-or-procedure": "An operation or other procedure",
    "diet-or-lifestyle": "Diet, exercise or another change in habits",
}


def configuration_problems(
    *,
    groups: Mapping[str, str] = GROUPS,
    anchors: Mapping[str, tuple[str, ...]] = GROUP_ANCHORS,
    verticals: Mapping[str, str] = VERTICALS,
    vertical_groups: Mapping[str, str] = VERTICAL_GROUPS,
    retired: Mapping[str, str] = RETIRED_VERTICALS,
) -> list[str]:
    """Every way the health area configuration breaks its rules. Empty when it is sound."""
    problems: list[str] = []
    known = set(HRCS_CATEGORIES)
    for group in groups:
        named = anchors.get(group, ())
        if not named:
            problems.append(f"Group '{group}' names no HRCS category.")
        for category in named:
            if category not in known:
                problems.append(f"Group '{group}' names an unknown HRCS category '{category}'.")
        if group not in verticals or vertical_groups.get(group) != group:
            problems.append(f"Group '{group}' has no general vertical of the same slug.")
        elif verticals[group] != groups[group]:
            problems.append(f"Group '{group}' and its general vertical have different titles.")
    covered = {category for group in groups for category in anchors.get(group, ())}
    for category in HRCS_CATEGORIES:
        if category not in HRCS_EXEMPT and category not in covered:
            problems.append(f"No group covers the HRCS category '{category}'.")
    for vertical in verticals:
        group = vertical_groups.get(vertical)
        if group is None:
            problems.append(f"Vertical '{vertical}' names no group.")
        elif group not in groups:
            problems.append(f"Vertical '{vertical}' names an unknown group '{group}'.")
    for old, new in retired.items():
        if old in verticals:
            problems.append(f"Retired vertical '{old}' is still configured.")
        if new not in verticals:
            problems.append(f"Retired vertical '{old}' points to an unknown vertical '{new}'.")
    return problems
