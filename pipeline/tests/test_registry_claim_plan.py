"""Registry plans preserve treatment arms and condition scope before any drafting."""

from typing import Any

from thenwhat.backfill.registry_claim_plan import group_registry_trials


def study(
    conditions: list[str], arms: list[dict[str, Any]], purpose: str = "TREATMENT"
) -> dict[str, Any]:
    return {
        "protocolSection": {
            "conditionsModule": {"conditions": conditions},
            "designModule": {"designInfo": {"primaryPurpose": purpose}},
            "armsInterventionsModule": {"armGroups": arms},
        }
    }


def test_groups_by_complete_regimen_and_matches_only_a_complete_claim_name():
    condition = ["Relapsing Multiple Sclerosis"]

    def with_partner(partner: str) -> dict[str, Any]:
        return study(
            condition,
            [
                {
                    "type": "EXPERIMENTAL",
                    "interventionNames": ["Drug: Alpha XR", f"Drug: {partner}", "Drug: Placebo"],
                },
                {"type": "ACTIVE_COMPARATOR", "interventionNames": ["Drug: Trial Control"]},
            ],
        )

    plan = group_registry_trials(
        [
            ("one", with_partner("Beta")),
            ("two", with_partner("Gamma")),
            ("three", with_partner("Beta")),
        ],
        [
            ("combination", condition[0], "Beta + Alpha XR", []),
            ("single-drug", condition[0], "Alpha XR", []),
            ("other-indication", "Progressive Multiple Sclerosis", "Alpha XR + Beta", []),
            ("other-formulation", condition[0], "Alpha + Beta", []),
        ],
        current_links={"one": "single-drug", "outside": "other-indication"},
    )

    assert plan.trial_count == 3
    assert plan.current_claim_links == {"one": "single-drug"}
    assert not plan.needs_review
    first, second = plan.groups
    assert (first.regimen, first.indication, first.trials) == (
        "Alpha XR + Beta",
        condition[0],
        ["one", "three"],
    )
    assert first.exact_claim_candidates == {"combination"}
    assert (second.regimen, second.trials) == ("Alpha XR + Gamma", ["two"])
    assert not second.exact_claim_candidates


def test_plans_purposes_separately_and_reports_aliases_and_unassigned_conditions():
    arms: list[dict[str, Any]] = [{"label": "Intervention", "type": "EXPERIMENTAL"}]
    prevention = study(["Condition One"], arms, "PREVENTION")
    prevention["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {"name": "ABC-123", "armGroupLabels": ["Intervention"], "otherNames": ["Example XR"]}
    ]
    treatment = study(["Condition One"], [{**arms[0], "interventionNames": ["Drug: ABC-123"]}])
    ambiguous = study(["Condition One", "Condition Two"], arms)
    ambiguous["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {"name": "ABC-123", "armGroupLabels": ["Intervention"]}
    ]

    plan = group_registry_trials(
        [
            ("prevention", prevention),
            ("treatment", treatment),
            ("ambiguous", ambiguous),
            ("old", {}),
        ],
        [("existing", "Condition One", "Example XR", [])],
    )

    assert [(g.purpose, g.trials) for g in plan.groups] == [
        ("PREVENTION", ["prevention"]),
        ("TREATMENT", ["treatment"]),
    ]
    assert plan.groups[0].alias_claim_candidates == {"existing"}
    assert not plan.groups[1].alias_claim_candidates
    assert plan.needs_review["ambiguous"].conditions == ("Condition One", "Condition Two")
    assert plan.needs_review["ambiguous"].issues == ("condition_assignment_needs_review",)
    assert "missing_tested_arm" in plan.needs_review["old"].issues


def test_crossover_membership_does_not_establish_a_combination():
    crossover = study(
        ["Asthma"],
        [
            {
                "type": "EXPERIMENTAL",
                "interventionNames": [
                    "Drug: Intervention: Alpha",
                    "Drug: Intervention: Beta",
                    "Drug: Intervention: Placebo matching Alpha",
                ],
            }
        ],
    )
    crossover["protocolSection"]["designModule"]["designInfo"]["interventionModel"] = "CROSSOVER"

    plan = group_registry_trials([("crossover", crossover)])

    assert not plan.groups
    scope = plan.needs_review["crossover"]
    assert scope.issues == ("arm_time_order_needs_review",)
    assert scope.regimens[0].components == ("Intervention: Alpha", "Intervention: Beta")
