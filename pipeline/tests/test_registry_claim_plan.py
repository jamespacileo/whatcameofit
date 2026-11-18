"""Registry plans preserve treatment arms and condition scope before any drafting."""

import json
from pathlib import Path
from typing import Any

import pytest

from thenwhat.backfill.registry_claim_plan import group_registry_trials, trial_scope
from thenwhat.backfill.registry_scope_review import load_scope_reviews
from thenwhat.clinical.mesh_xml import mesh_xml_vocabulary
from thenwhat.store.form import payload_of
from thenwhat.work.errors import BackfillError


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


def test_registry_assessment_is_not_a_regimen_component_in_a_treatment_trial():
    arms = [
        {
            "type": "EXPERIMENTAL",
            "interventionNames": [
                "Procedure: Computed Tomography",
                "Behavioral: Mobility Coaching",
                "Drug: Example XR",
                "Other: Quality-of-Life Assessment",
            ],
        }
    ]
    record = study(["Condition One"], arms)
    record["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {"type": "PROCEDURE", "name": "Computed Tomography"},
        {"type": "BEHAVIORAL", "name": "Mobility Coaching"},
        {"type": "DRUG", "name": "Example XR"},
        {"type": "OTHER", "name": "Quality-of-Life Assessment"},
    ]

    scope = trial_scope(record)

    assert not scope.issues
    assert scope.regimens[0].components == ("Example XR", "Mobility Coaching")
    assert scope.regimens[0].assessments == ("Computed Tomography", "Quality-of-Life Assessment")


def test_a_diagnostic_intervention_stays_in_a_diagnostic_trial():
    record = study(
        ["Condition One"],
        [{"type": "EXPERIMENTAL", "interventionNames": ["Procedure: Computed Tomography"]}],
        "DIAGNOSTIC",
    )
    record["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {"name": "Computed Tomography", "type": "PROCEDURE"}
    ]

    plan = group_registry_trials([("diagnostic", record)])

    assert not plan.needs_review
    assert plan.groups[0].regimen == "Computed Tomography"


def test_title_refines_nested_indication_but_does_not_choose_an_unrelated_condition():
    arms: list[dict[str, Any]] = [
        {"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}
    ]
    general = "Multiple Sclerosis"
    subtype = "Relapsing-Remitting Multiple Sclerosis"
    anchor = {"officialTitle": f"A Study of Example XR in Participants With {subtype}"}
    single = study([general], arms)
    nested = study([general, subtype], arms)
    unrelated = study([general, "Chronic Lung Disease"], arms)
    for record in (single, nested, unrelated):
        record["protocolSection"]["identificationModule"] = anchor

    plan = group_registry_trials([("single", single), ("nested", nested), ("mixed", unrelated)])

    assert [(group.indication, group.trials) for group in plan.groups] == [
        (subtype, ["single", "nested"])
    ]
    assert plan.needs_review["mixed"].registered_conditions == (general, "Chronic Lung Disease")
    assert trial_scope(single).indication_title_phrase == subtype


def test_title_with_disagreeing_subtypes_is_held_and_a_negation_does_not_narrow():
    arms: list[dict[str, Any]] = [
        {"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}
    ]
    conflicting = study(["Multiple Sclerosis"], arms)
    conflicting["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "Example XR in Relapsing Multiple Sclerosis and Progressive Multiple Sclerosis"
        )
    }
    negated = study(["Multiple Sclerosis"], arms)
    negated["protocolSection"]["identificationModule"] = {
        "officialTitle": "Example XR in Non-Relapsing Multiple Sclerosis"
    }

    plan = group_registry_trials([("conflicting", conflicting), ("negated", negated)])

    assert set(plan.needs_review["conflicting"].conditions) == {
        "Relapsing Multiple Sclerosis",
        "Progressive Multiple Sclerosis",
    }
    assert plan.groups[0].indication == "Multiple Sclerosis"


def test_a_named_treatment_target_can_distinguish_a_comorbidity_from_the_indication():
    arms: list[dict[str, Any]] = [
        {"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}
    ]
    labels = ["Acute Kidney Injury", "Cirrhosis"]
    for_population = study(labels, arms)
    for_population["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "A Trial of Example XR to Treat Acute Kidney Injury in People With Cirrhosis"
        )
    }
    target_list = study(labels, arms)
    target_list["protocolSection"]["identificationModule"] = {
        "briefTitle": "A Trial of Example XR to Treat Acute Kidney Injury",
        "officialTitle": "A Trial of Example XR to Treat Acute Kidney Injury and Cirrhosis",
    }

    plan = group_registry_trials([("population", for_population), ("list", target_list)])

    assert [(group.indication, group.trials) for group in plan.groups] == [
        ("Acute Kidney Injury in People With Cirrhosis", ["population"])
    ]
    assert plan.needs_review["list"].registered_conditions == tuple(labels)


def test_mixed_enrolment_does_not_turn_a_broad_indication_into_one_subgroup():
    broad = "Chronic Lymphocytic Leukemia"
    record = study([broad], [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}])
    record["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "Example XR in Untreated and Relapsed or Refractory Chronic Lymphocytic Leukemia"
        ),
        "briefTitle": "Example XR in Chronic Lymphocytic Leukemia",
    }

    assert trial_scope(record).conditions == (broad,)


def test_one_regimen_is_planned_for_each_separately_named_trial_cohort():
    labels = ["Ocular Redness (OR)", "Eye Irritation (EI)"]

    def arm(label: str, name: str = "Example XR") -> dict[str, Any]:
        return {"type": "EXPERIMENTAL", "label": label, "interventionNames": [f"Drug: {name}"]}

    separate = study(labels, [arm("OR cohort"), arm("EI cohort")])
    ambiguous = study(labels, [arm("OR and EI population")])
    different_regimens = study(labels, [arm("OR cohort"), arm("EI cohort", "Other Drug")])

    plan = group_registry_trials(
        [("separate", separate), ("ambiguous", ambiguous), ("different", different_regimens)]
    )

    assert {(group.indication, tuple(group.trials)) for group in plan.groups} == {
        ("Ocular Redness (OR)", ("separate",)),
        ("Eye Irritation (EI)", ("separate",)),
    }
    assert set(plan.needs_review) == {"ambiguous", "different"}


def test_reviewed_pairs_stay_linked_to_their_source_record_and_never_cross_join(tmp_path: Path):
    first = "Drug: Example XR"
    second = "Device: Example Device"
    given = study(
        ["Ocular Redness", "Asthma"],
        [
            {"type": "EXPERIMENTAL", "interventionNames": [first]},
            {"type": "EXPERIMENTAL", "interventionNames": [second]},
        ],
    )
    identifier = "NCT00000001"
    receipt = {
        "trial_id": identifier,
        "registry_sha256": payload_of(given).sha256,
        "reviewed_by": "assistant:sample-review",
        "pairs": [
            {
                "regimen": ["Example XR"],
                "indication": "Ocular Redness",
                "intervention_quotes": [first],
                "indication_quotes": ["Ocular Redness"],
            },
            {
                "regimen": ["Example Device"],
                "indication": "Asthma",
                "intervention_quotes": [second],
                "indication_quotes": ["Asthma"],
            },
        ],
    }
    file = tmp_path / "reviews.json"
    file.write_text(json.dumps({"schema_version": 1, "reviews": [receipt]}))
    reviews = load_scope_reviews(file)

    plan = group_registry_trials([(identifier, given)], scope_reviews=reviews)

    assert {(group.regimen, group.indication) for group in plan.groups} == {
        ("Example XR", "Ocular Redness"),
        ("Example Device", "Asthma"),
    }
    assert plan.applied_reviews == {identifier: "assistant:sample-review"}
    assert not plan.needs_review
    assert group_registry_trials([], scope_reviews=reviews).reviews_outside_plan == (identifier,)
    given["protocolSection"]["identificationModule"] = {"officialTitle": "Updated record"}
    with pytest.raises(BackfillError, match=identifier):
        group_registry_trials([(identifier, given)], scope_reviews=reviews)


def test_reference_arms_preserve_the_complete_active_regimen():
    given = study(
        ["Ocular Redness"],
        [
            {
                "type": "EXPERIMENTAL",
                "label": "Investigational Arm",
                "interventionNames": ["Drug: Example XR", "Drug: Background Therapy"],
            },
            {
                "type": "EXPERIMENTAL",
                "label": "Placebo + Background Therapy",
                "interventionNames": ["Drug: Placebo", "Drug: Background Therapy"],
            },
        ],
    )
    given["protocolSection"]["designModule"]["designInfo"]["interventionModel"] = "PARALLEL"

    scope = trial_scope(given)

    assert scope.reference_arms == ("Placebo + Background Therapy",)
    assert [regimen.components for regimen in scope.regimens] == [
        ("Background Therapy", "Example XR")
    ]


@pytest.mark.parametrize("placebo, is_reference", [("Example XR", True), ("Unrelated", False)])
def test_a_placebo_for_the_added_product_identifies_its_reference_arm(
    placebo: str, is_reference: bool
):
    given = study(
        ["Ocular Redness"],
        [
            {
                "type": "EXPERIMENTAL",
                "label": "Example XR + Background Therapy",
                "interventionNames": ["Drug: Example XR", "Drug: Background Therapy"],
            },
            {
                "type": "EXPERIMENTAL",
                "label": f"Background Therapy + {placebo} Placebo",
                "interventionNames": ["Drug: Background Therapy", f"Drug: {placebo} Placebo"],
            },
        ],
    )
    given["protocolSection"]["designModule"]["designInfo"]["interventionModel"] = "PARALLEL"

    scope = trial_scope(given)

    assert scope.reference_arms == (
        (f"Background Therapy + {placebo} Placebo",) if is_reference else ()
    )
    assert [regimen.components for regimen in scope.regimens] == (
        [("Background Therapy", "Example XR")]
        if is_reference
        else [("Background Therapy", "Example XR"), ("Background Therapy",)]
    )


def test_product_prefixed_placebo_is_excluded_from_a_double_dummy_regimen():
    record = study(
        ["Eye Irritation"],
        [
            {
                "type": "EXPERIMENTAL",
                "interventionNames": [
                    "Drug: Study Product tablets",
                    "Drug: Study Product placebo tablets",
                ],
            }
        ],
    )

    (regimen,) = trial_scope(record).regimens
    assert regimen.components == ("Study Product tablets",)


def test_control_label_and_explicit_dose_escalation_are_used_as_reference_evidence():
    arms: list[dict[str, Any]] = [
        {
            "type": "ACTIVE_COMPARATOR",
            "label": "Control group",
            "interventionNames": ["Drug: Drug A"],
        },
        {"type": "ACTIVE_COMPARATOR", "label": "Dose group", "interventionNames": ["Drug: Drug B"]},
    ]
    control = study(["Eye Irritation"], arms)
    assert [regimen.components for regimen in trial_scope(control).regimens] == [("Drug B",)]

    for arm in arms:
        arm["type"] = "EXPERIMENTAL"
    arms[0]["label"] = "Drug A"
    doses = study(["Eye Irritation"], arms)
    doses["protocolSection"]["designModule"]["designInfo"]["interventionModel"] = "PARALLEL"
    doses["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "Evaluation of Different Dose Escalation Regimens for Drug B in Eye Irritation"
        )
    }

    assert trial_scope(doses).reference_arms == ("Drug A",)
    assert [regimen.components for regimen in trial_scope(doses).regimens] == [("Drug B",)]


def test_explicit_noninvestigational_product_is_kept_as_background_evidence():
    arms: list[dict[str, Any]] = [
        {
            "type": "EXPERIMENTAL",
            "interventionNames": ["Drug: Study Drug", "Drug: Premedication"],
        },
        {"type": "ACTIVE_COMPARATOR", "interventionNames": ["Drug: Control Drug"]},
    ]
    given = study(["Eye Irritation"], arms)
    given["protocolSection"]["identificationModule"] = {
        "officialTitle": "An Evaluation of Study Drug Versus Control Drug for Eye Irritation"
    }
    given["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {
            "name": "Premedication",
            "type": "DRUG",
            "otherNames": ["Non-Investigational Medicinal Product"],
        }
    ]

    (regimen,) = trial_scope(given).regimens
    assert regimen.components == ("Study Drug",)
    assert regimen.background == ("Premedication",)

    given["protocolSection"]["identificationModule"]["officialTitle"] = (
        "An Evaluation of Study Drug + Premedication Versus Control Drug for Eye Irritation"
    )
    (regimen,) = trial_scope(given).regimens
    assert regimen.components == ("Premedication", "Study Drug")


def test_only_a_unique_evidenced_general_vertical_is_assigned(tmp_path: Path):
    file = tmp_path / "desc2026.xml"
    mesh = [
        ("D009369", "Neoplasms", ["C04"]),
        ("D012140", "Respiratory Tract Diseases", ["C08"]),
        ("D000001", "Example Neoplasm", ["C04.200"]),
        ("D000002", "Example Overlap", ["C04.300", "C08.300"]),
    ]
    elements = []
    for identifier, label, trees in mesh:
        placements = "".join(f"<TreeNumber>{code}</TreeNumber>" for code in trees)
        elements.append(
            f"<DescriptorRecord><DescriptorUI>{identifier}</DescriptorUI>"
            f"<DescriptorName><String>{label}</String></DescriptorName>"
            f"<TreeNumberList>{placements}</TreeNumberList></DescriptorRecord>"
        )
    file.write_text("<DescriptorRecordSet>" + "".join(elements) + "</DescriptorRecordSet>")
    vocabulary = mesh_xml_vocabulary(file)
    arms = [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}]
    records = []
    for identifier, label, _ in mesh[2:]:
        given = study([label], arms)
        given["derivedSection"] = {
            "conditionBrowseModule": {"meshes": [{"id": identifier, "term": label}]}
        }
        records.append((identifier, given))

    plan = group_registry_trials(records, vocabulary=vocabulary)

    unique, overlap = plan.groups
    assert unique.vertical == "cancer"
    assert unique.vertical_evidence == {"cancer": {"D000001"}}
    assert overlap.vertical is None
    assert set(overlap.vertical_evidence) == {"cancer", "lungs-and-breathing"}
