"""The health area configuration check: the configured tree, then one failure per rule."""

from thenwhat.claims.verticals import (
    GROUP_ANCHORS,
    GROUPS,
    VERTICAL_GROUPS,
    VERTICALS,
    configuration_problems,
)


def test_configured_tree_is_sound() -> None:
    assert configuration_problems() == []


def test_group_without_an_anchor() -> None:
    anchors = {**GROUP_ANCHORS, "lungs-and-breathing": ()}
    problems = configuration_problems(anchors=anchors)
    assert "Group 'lungs-and-breathing' names no HRCS category." in problems


def test_uncovered_category() -> None:
    anchors = {**GROUP_ANCHORS, "lungs-and-breathing": ("Generic health relevance",)}
    problems = configuration_problems(anchors=anchors)
    assert "No group covers the HRCS category 'Respiratory'." in problems


def test_vertical_without_a_group() -> None:
    verticals = {**VERTICALS, "epilepsy": "Epilepsy"}
    problems = configuration_problems(verticals=verticals)
    assert problems == ["Vertical 'epilepsy' names no group."]


def test_group_missing_its_general_vertical() -> None:
    verticals = {slug: title for slug, title in VERTICALS.items() if slug != "lungs-and-breathing"}
    vertical_groups = {
        slug: group for slug, group in VERTICAL_GROUPS.items() if slug != "lungs-and-breathing"
    }
    problems = configuration_problems(verticals=verticals, vertical_groups=vertical_groups)
    assert problems == ["Group 'lungs-and-breathing' has no general vertical of the same slug."]


def test_retired_vertical_pointing_nowhere() -> None:
    problems = configuration_problems(retired={"pain": "pain-relief"})
    assert problems == ["Retired vertical 'pain' points to an unknown vertical 'pain-relief'."]


def test_every_group_listed_once() -> None:
    assert set(GROUPS) == set(GROUP_ANCHORS)
