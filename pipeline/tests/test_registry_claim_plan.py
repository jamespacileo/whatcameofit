"""Registry plans preserve treatment arms and condition scope before any drafting."""

import json
from pathlib import Path
from typing import Any

import pytest

from thenwhat.backfill.registry_claim_plan import group_registry_trials, trial_scope
from thenwhat.backfill.registry_scope_review import ScopePair, ScopeReview, load_scope_reviews
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


def test_generic_registry_treatment_labels_require_scope_evidence():
    def record(name: str):
        return study(
            ["Example Neoplasm"],
            [{"type": "EXPERIMENTAL", "interventionNames": [f"Drug: {name}"]}],
        )

    plan = group_registry_trials(
        [
            ("ordinary", record("Home")),
            ("schedule", record("Maintenance Therapy")),
            ("named", record("Aspirin")),
            ("full-label", record("Autologous Mesenchymal Stem Cells")),
        ]
    )

    assert {group.regimen for group in plan.groups} == {
        "Aspirin",
        "Autologous Mesenchymal Stem Cells",
    }
    assert {trial: scope.issues for trial, scope in plan.needs_review.items()} == {
        "ordinary": ("generic_intervention_needs_review",),
        "schedule": ("generic_intervention_needs_review",),
    }


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


def test_title_refines_a_disease_with_a_reordered_qualifier():
    arms = [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}]
    label = "Ovarian Cancer Recurrent"
    refined = study([label], arms)
    refined["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "Example XR for the Treatment of Platinum-resistant Recurrent Ovarian Cancer"
        )
    }
    unqualified = study([label], arms)
    unqualified["protocolSection"]["identificationModule"] = {
        "officialTitle": "Example XR in Ovarian Cancer"
    }
    negated = study([label], arms)
    negated["protocolSection"]["identificationModule"] = {
        "officialTitle": "Example XR in Non-Recurrent Ovarian Cancer"
    }
    two_conditions = study([label, "Ovarian Cancer"], arms)
    two_conditions["protocolSection"]["identificationModule"] = {
        "officialTitle": "Example XR in Advanced or Recurrent Ovarian Cancer"
    }

    assert trial_scope(refined).conditions == ("Platinum-resistant Recurrent Ovarian Cancer",)
    assert trial_scope(unqualified).conditions == (label,)
    assert trial_scope(negated).conditions == (label,)
    assert trial_scope(two_conditions).issues == ("condition_assignment_needs_review",)


def test_title_preserves_distinct_explicit_treatment_settings():
    arms = [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}]
    disease = "Example Carcinoma"
    setting_titles = {
        "first": "Example XR for the First-Line Treatment of Example Carcinoma: Phase 2",
        "short": "Example XR for 1L therapy in participants with Example Carcinoma",
        "second": "Example XR as second-line treatment of Example Carcinoma",
        "plain": "Example XR in Example Carcinoma after first-line treatment",
        "multiple": "Example XR for first-line treatment of Example Carcinoma or Example Sarcoma",
    }
    trials = [(identifier, study([disease], arms)) for identifier in setting_titles]
    for identifier, record in trials:
        record["protocolSection"]["identificationModule"] = {
            "officialTitle": setting_titles[identifier],
        }
    competing = study([disease], arms)
    competing["protocolSection"]["identificationModule"] = {
        "briefTitle": setting_titles["first"],
        "officialTitle": setting_titles["second"],
    }
    trials.append(("competing", competing))

    plan = group_registry_trials(trials)

    assert {group.indication: group.trials for group in plan.groups} == {
        disease: ["plain", "multiple"],
        f"{disease} (first-line treatment)": ["first", "short"],
        f"{disease} (second-line treatment)": ["second"],
    }
    assert plan.needs_review["competing"].issues == ("treatment_setting_needs_review",)
    assert trial_scope(trials[0][1]).indication_title_phrase == (
        "First-Line Treatment of Example Carcinoma"
    )


def test_the_name_of_one_combination_component_is_not_the_indication():
    record = study(
        ["Example Carcinoma", "Example Solid Tumors", "Example XR", "Example Y"],
        [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR; Example Y"]}],
    )
    record["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "Neoadjuvant Treatment of Example XR Plus Example Y in Stage II Example Carcinoma"
        )
    }
    scope = trial_scope(record)

    assert scope.issues == ("condition_assignment_needs_review",)
    assert scope.indication_title_phrase is None


def test_reordered_qualifiers_share_the_same_group_and_existing_claim_candidate():
    arms = [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}]
    trials = [
        ("one", study(["Ovarian Cancer Recurrent"], arms)),
        ("two", study(["Recurrent Ovarian Cancer"], arms)),
        ("three", study(["Ovarian Cancer"], arms)),
        ("four", study(["Ovarian Cancer Non-Recurrent"], arms)),
    ]
    plan = group_registry_trials(
        trials, [("existing", "Recurrent Ovarian Cancer", "Example XR", [])]
    )

    assert not plan.needs_review
    assert {tuple(group.trials): group.exact_claim_candidates for group in plan.groups} == {
        ("one", "two"): {"existing"},
        ("three",): set(),
        ("four",): set(),
    }


def test_title_keeps_a_genotype_for_the_enrolled_population():
    arms = [{"type": "EXPERIMENTAL", "interventionNames": ["Drug: Example XR"]}]
    narrow = study(["Multiple Myeloma"], arms)
    alternatives = study(["Multiple Myeloma"], arms)
    for given, title in (
        (
            narrow,
            "Example XR in Participants With Multiple Myeloma Harboring the ABC2 Q21R Mutation",
        ),
        (
            alternatives,
            "Example XR in Participants With Multiple Myeloma With ABC2 Q21R Mutations"
            " or Other Variants",
        ),
    ):
        given["protocolSection"]["identificationModule"] = {"officialTitle": title}
    plan = group_registry_trials([("narrow", narrow), ("alternatives", alternatives)])
    assert {(group.indication, tuple(group.trials)) for group in plan.groups} == {
        ("Multiple Myeloma Harboring the ABC2 Q21R Mutation", ("narrow",)),
        ("Multiple Myeloma", ("alternatives",)),
    }


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


def test_separate_control_entries_are_excluded_even_in_an_experimental_arm():
    arms = [
        {
            "type": "EXPERIMENTAL",
            "label": "Procedure",
            "interventionNames": ["Procedure: Example Procedure", "Other: Saline (Placebo)"],
        },
        {
            "type": "EXPERIMENTAL",
            "label": "Sham arm",
            "interventionNames": ["Procedure: Sham Procedure"],
        },
    ]

    scope = trial_scope(study(["Eye Irritation"], arms))

    assert scope.reference_arms == ("Sham arm",)
    assert [regimen.components for regimen in scope.regimens] == [("Example Procedure",)]
    assert not scope.issues


def test_placebo_shorthand_requires_the_registry_to_define_it():
    arms: list[dict[str, Any]] = [
        {
            "type": "EXPERIMENTAL",
            "label": "Combination",
            "interventionNames": ["Drug: Example XR", "Drug: PTM Example Immediate"],
        }
    ]
    record = study(["Eye Irritation"], arms)
    unresolved = group_registry_trials([("unknown", record)])
    assert not unresolved.groups
    assert unresolved.needs_review["unknown"].issues == ("control_component_needs_review",)

    arms[0]["description"] = "Example XR and placebo-to-match (PTM) Example Immediate."
    resolved = group_registry_trials([("defined", record)])
    assert resolved.groups[0].regimen == "Example XR"
    assert not resolved.needs_review


@pytest.mark.parametrize(
    ("label", "issues"),
    [
        ("Placebo + Study Product", ("control_component_needs_review",)),
        ("Placebo/Study Product", ("control_component_needs_review",)),
        ("Study Product vs Saline (Placebo)", ("control_component_needs_review",)),
        ("Product One or Product Two", ("alternative_regimen_needs_review",)),
        ("Study Product Doses 1 or 2 QD", ()),
        ("Study Product (25mg or 40mg)", ()),
        ("Product One 25 mg or Product Two 40 mg", ("alternative_regimen_needs_review",)),
    ],
)
def test_unresolved_component_labels_stay_out_of_the_grouping_plan(
    label: str, issues: tuple[str, ...]
):
    record = study(
        ["Eye Irritation"], [{"type": "EXPERIMENTAL", "interventionNames": [f"Drug: {label}"]}]
    )
    plan = group_registry_trials([("trial", record)])

    if issues:
        assert not plan.groups
        assert plan.needs_review["trial"].issues == issues
    else:
        assert plan.groups[0].regimen == label
        assert not plan.needs_review


def test_an_arm_with_optional_treatments_needs_review_of_its_complete_regimen():
    record = study(
        ["Ovarian Cancer"],
        [
            {
                "type": "EXPERIMENTAL",
                "label": "Example XR + Backbone ± Optional Drug",
                "interventionNames": ["Drug: Example XR", "Drug: Backbone", "Drug: Optional Drug"],
            },
        ],
    )

    plan = group_registry_trials([("trial", record)])

    assert not plan.groups
    assert plan.needs_review["trial"].issues == ("alternative_regimen_needs_review",)


@pytest.mark.parametrize(
    ("description", "needs_review"),
    [
        ("Example XR with or without Example Y in the first cycle", True),
        ("If Example XR is not tolerated, Example Y may be used as an alternative", True),
        ("After four cycles, participants may switch to Example Y", True),
        ("Both Example XR and Example Y are given on Day 1 or Day 2", False),
        ("Both Example XR and Example Y are given with or without food", False),
    ],
)
def test_described_choices_stay_visible_without_inventing_arm_assignments(
    description: str, needs_review: bool
):
    record = study(
        ["Example Neoplasm"],
        [
            {
                "type": "EXPERIMENTAL",
                "label": "Test treatment",
                "interventionNames": ["Drug: Example XR", "Drug: Example Y"],
                "description": description,
            }
        ],
    )
    scope = trial_scope(record)

    assert ("alternative_regimen_needs_review" in scope.issues) is needs_review
    if needs_review:
        [(arm, evidence)] = scope.arm_choices
        assert arm == "Test treatment" and evidence.description == description
        assert not evidence.variants
    else:
        assert len(scope.regimens) == 1 and not scope.arm_choices


def test_distinct_line_regimens_named_in_the_title_hold_one_flattened_arm():
    record = study(
        ["Colorectal Cancer Metastatic"],
        [
            {
                "type": "EXPERIMENTAL",
                "interventionNames": ["Drug: Example XR plus Backbone"],
            },
        ],
    )
    record["protocolSection"]["identificationModule"] = {
        "officialTitle": (
            "Example XR Plus Backbone as First-line / Example XR as Second-line "
            "in Participants With Metastatic Colorectal Cancer"
        ),
    }

    assert trial_scope(record).issues == ("alternative_regimen_needs_review",)


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


def test_topic_evidence_places_unique_groups_and_the_approved_cancer_overlap(tmp_path: Path):
    file = tmp_path / "desc2026.xml"
    mesh = [
        ("D009369", "Neoplasms", ["C04"]),
        ("D012140", "Respiratory Tract Diseases", ["C08"]),
        ("D007239", "Infections", ["C01"]),
        ("D000001", "Example Neoplasm", ["C04.200"]),
        ("D000002", "Example Overlap", ["C04.200.300", "C08.300"]),
        ("D000003", "Independent Lung Disease", ["C08.400"]),
        ("D000004", "Example Infection Overlap", ["C04.400", "C01.400"]),
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
    for identifier, label, _ in mesh[3:5]:
        given = study([label], arms)
        if identifier == "D000001":
            given["protocolSection"]["identificationModule"] = {
                "officialTitle": f"Example XR for the first-line treatment of {label}",
            }
        given["derivedSection"] = {
            "conditionBrowseModule": {"meshes": [{"id": identifier, "term": label}]}
        }
        records.append((identifier, given))

    plan = group_registry_trials(records, vocabulary=vocabulary)

    unique, overlap = plan.groups
    assert unique.indication == "Example Neoplasm (first-line treatment)"
    assert unique.vertical == "cancer"
    assert unique.vertical_evidence == {"cancer": {"D000001"}}
    assert overlap.vertical == "cancer"
    assert overlap.primary_cancer_descriptor == "D000002"
    assert set(overlap.vertical_evidence) == {"cancer", "lungs-and-breathing"}

    def reviewed(
        nct: str, indication: str, registered: list[str], descriptor: tuple[str, str] | None
    ) -> tuple[tuple[str, dict[str, Any]], ScopeReview]:
        record = study(registered, arms)
        record["protocolSection"]["identificationModule"] = {"officialTitle": indication}
        if descriptor is not None:
            identifier, term = descriptor
            record["derivedSection"] = {
                "conditionBrowseModule": {"meshes": [{"id": identifier, "term": term}]}
            }
        receipt = ScopeReview(
            nct,
            payload_of(record).sha256,
            "assistant:fixture",
            (ScopePair(("Example XR",), indication, ("Example XR",), (indication,)),),
        )
        return (nct, record), receipt

    cases = [
        reviewed(
            "NCT00000001",
            "Example Neoplasm in adults after prior therapy",
            ["Example Neoplasm", "Other Disease"],
            ("D000001", "Example Neoplasm"),
        ),
        reviewed(
            "NCT00000002",
            "Example Neoplasm among newborns",
            ["Example Neoplasm"],
            None,
        ),
        reviewed(
            "NCT00000003",
            "Other Disease in adults with Example Neoplasm",
            ["Other Disease", "Example Neoplasm"],
            ("D000001", "Example Neoplasm"),
        ),
        reviewed(
            "NCT00000004",
            "Example Overlap in patients",
            ["Other Disease", "Example Overlap"],
            ("D000002", "Example Overlap"),
        ),
        reviewed(
            "NCT00000005",
            "Example Infection Overlap",
            ["Example Infection Overlap"],
            ("D000004", "Example Infection Overlap"),
        ),
    ]
    placed = group_registry_trials(
        [record for record, _ in cases],
        scope_reviews={review.trial_id: review for _, review in cases},
        vocabulary=vocabulary,
    )
    groups = {group.trials[0]: group for group in placed.groups}
    assert groups["NCT00000001"].vertical == "cancer"
    assert groups["NCT00000002"].vertical == "cancer"
    assert groups["NCT00000002"].condition_terms == {("D000001", "Example Neoplasm")}
    assert not groups["NCT00000003"].vertical_evidence
    assert groups["NCT00000004"].vertical == "cancer"
    assert set(groups["NCT00000004"].vertical_evidence) == {"cancer", "lungs-and-breathing"}
    assert groups["NCT00000005"].vertical is None
    assert set(groups["NCT00000005"].vertical_evidence) == {"cancer", "infections"}

    different_evidence = study(["Example Overlap"], arms)
    different_evidence["derivedSection"] = {
        "conditionBrowseModule": {"meshes": [{"id": "D000003", "term": "Independent Lung Disease"}]}
    }
    concurrent = group_registry_trials(
        [records[1], ("independent", different_evidence)], vocabulary=vocabulary
    )
    assert concurrent.groups[0].vertical is None
    assert concurrent.groups[0].vertical_evidence["lungs-and-breathing"] == {"D000002", "D000003"}

    broad_context = study(["Example Overlap"], arms)
    broad_context["derivedSection"] = {
        "conditionBrowseModule": {
            "meshes": [
                {"id": "D000001", "term": "Example Neoplasm"},
                {"id": "D000002", "term": "Example Overlap"},
            ]
        }
    }
    # Both registry terms apply when neither label exactly matches the condition.
    no_exact = broad_context["derivedSection"]["conditionBrowseModule"]["meshes"][1]
    no_exact["term"] = "Example Condition Naming Variant"
    (supported,) = group_registry_trials(
        [("with-broad-term", broad_context)], vocabulary=vocabulary
    ).groups
    assert supported.primary_cancer_descriptor == "D000002"
    assert supported.vertical_evidence["cancer"] == {"D000001", "D000002"}
