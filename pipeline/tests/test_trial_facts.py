"""Reading a trial's facts out of one registry record, tested through the pure `read_trial`.

Starts from a recorded study and changes only the fields a test is about. Scenario names
are from openspec trial-facts.
"""

import copy
import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import pytest

from thenwhat.domain import TrialState
from thenwhat.events.trial_facts import (
    Comparison,
    Participants,
    PlannedOutcome,
    ResultGroup,
    Sponsor,
    TrialFacts,
    is_registry_record,
    read_trial,
    reported_state,
)

Load = Callable[[str], dict[str, Any]]


@pytest.fixture
def load(fixture_json) -> Load:
    return lambda name: copy.deepcopy(fixture_json(f"clinicaltrials/{name}.json"))


def facts(study: dict[str, Any]) -> TrialFacts:
    return read_trial(study).facts


def protocol(study: dict[str, Any]) -> dict[str, Any]:
    return study["protocolSection"]


def primary_result(study: dict[str, Any]) -> dict[str, Any]:
    measures = study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
    return next(measure for measure in measures if measure["type"] == "PRIMARY")


# --- 2.1 participants and design ------------------------------------------------------


def test_completed_trial_states_its_actual_size_and_its_design(load: Load):
    """Scenario: Completed trial"""
    read = facts(load("study_NCT02586935"))

    assert read.participants == Participants(83, "actual")
    assert read.study_kind == "interventional"
    assert (read.allocation, read.masking) == ("randomised", "quadruple")
    # The record classes the treatment arm itself as an "active comparator". With no
    # experimental arm beside it, it is the treatment, not something compared with it.
    assert read.comparators == ("placebo",)


def test_active_arm_is_a_comparator_only_beside_an_experimental_arm(load: Load):
    study = load("study_NCT02586935")
    arms = protocol(study)["armsInterventionsModule"]["armGroups"]
    assert {arm["type"] for arm in arms} == {"ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR"}

    arms.append({"label": "New treatment", "type": "EXPERIMENTAL"})

    assert facts(study).comparators == ("placebo", "active")


def test_trial_not_yet_started_states_its_planned_size(load: Load):
    """Scenario: Trial not yet started"""
    study = load("study_NCT02586935")
    protocol(study)["designModule"]["enrollmentInfo"] = {"count": 400, "type": "ESTIMATED"}

    assert facts(study).participants == Participants(400, "planned")


def test_randomised_double_masked_placebo_controlled_trial(load: Load):
    """Scenario: Randomised, double-masked, placebo-controlled trial"""
    read = facts(load("study_NCT01596231_results"))

    assert (read.allocation, read.masking) == ("randomised", "double")
    assert read.comparators == ("placebo",)


def test_single_arm_trial_has_no_allocation_and_no_comparator(load: Load):
    """Scenario: Single-arm trial"""
    read = facts(load("study_NCT04951479_comparison"))

    assert read.allocation is None and read.comparators == ()
    assert read.masking == "none"


def test_record_that_gives_no_masking_carries_none(load: Load):
    """Scenario: Record that gives no masking"""
    study = load("study_NCT02586935")
    del protocol(study)["designModule"]["designInfo"]["maskingInfo"]

    assert facts(study).masking is None


def test_comparators_are_listed_once_each_in_a_fixed_order(load: Load):
    study = load("study_NCT02586935")
    protocol(study)["armsInterventionsModule"]["armGroups"] = [
        {"label": label, "type": kind}
        for label, kind in [
            ("A", "NO_INTERVENTION"),
            ("B", "EXPERIMENTAL"),
            ("C", "SHAM_COMPARATOR"),
            ("D", "ACTIVE_COMPARATOR"),
            ("E", "PLACEBO_COMPARATOR"),
            ("F", "SHAM_COMPARATOR"),
        ]
    ]

    assert facts(study).comparators == ("placebo", "sham", "active", "no_treatment")


# --- 2.2 who was studied and who ran it -----------------------------------------------


def test_trial_in_healthy_adults(load: Load):
    """Scenario: Phase 1 trial in healthy adults"""
    read = facts(load("study_NCT01596231_results"))

    assert read.healthy_volunteers is True and read.age_groups == ("adult",)


def test_age_groups_are_listed_in_a_fixed_order(load: Load):
    study = load("study_NCT02586935")
    protocol(study)["eligibilityModule"]["stdAges"] = ["OLDER_ADULT", "CHILD", "ADULT"]

    assert facts(study).age_groups == ("child", "adult", "older_adult")


def test_industry_sponsor_is_named_with_its_kind(load: Load):
    """Scenario: Industry sponsor"""
    study = load("study_NCT02586935")
    protocol(study)["sponsorCollaboratorsModule"]["leadSponsor"] = {
        "name": "Example Pharma Ltd",
        "class": "INDUSTRY",
    }

    assert facts(study).sponsor == Sponsor("Example Pharma Ltd", "industry")


def test_hospital_sponsor_with_a_principal_investigator_keeps_its_name(load: Load):
    assert facts(load("study_NCT01596231_results")).sponsor == Sponsor("Mclean Hospital", "other")


def test_sponsor_who_is_a_person_is_not_named(load: Load):
    """Scenario: Sponsor who is a person"""
    study = load("study_NCT02586935")
    protocol(study)["sponsorCollaboratorsModule"]["leadSponsor"] = {
        "name": "Dr Example Person",
        "class": "INDIV",
    }

    read = facts(study)

    assert read.sponsor == Sponsor(None, "individual")
    assert "Example Person" not in json.dumps(asdict(read))


def test_sponsor_investigator_classed_as_other_is_not_named(load: Load):
    """Scenario: Sponsor-investigator classed as another kind"""
    study = load("study_NCT04951479_comparison")
    module = protocol(study)["sponsorCollaboratorsModule"]
    assert module["leadSponsor"]["class"] == "OTHER"
    assert module["responsibleParty"]["type"] == "SPONSOR_INVESTIGATOR"

    read = facts(study)

    assert read.sponsor == Sponsor(None, "individual")
    text = json.dumps(asdict(read))
    party = module["responsibleParty"]
    assert module["leadSponsor"]["name"] not in text
    assert party["investigatorFullName"] not in text
    assert party["investigatorAffiliation"] not in text


@pytest.mark.parametrize(
    ("registry_class", "kind"),
    [
        ("NIH", "government"),
        ("FED", "government"),
        ("OTHER_GOV", "government"),
        ("NETWORK", "network"),
        ("OTHER", "other"),
        ("AMBIG", None),
        ("UNKNOWN", None),
        (None, None),
    ],
)
def test_registry_sponsor_classes_become_kinds(load: Load, registry_class, kind):
    study = load("study_NCT02586935")
    lead = protocol(study)["sponsorCollaboratorsModule"]["leadSponsor"]
    lead["class"] = registry_class

    assert facts(study).sponsor == Sponsor(lead["name"], kind)


# --- 2.3 planned outcomes and reason for stopping -------------------------------------


def test_record_with_five_primary_outcomes_gives_the_first_three_and_the_total(load: Load):
    """Scenario: Record with five primary outcomes"""
    study = load("study_NCT02586935")
    protocol(study)["outcomesModule"]["primaryOutcomes"] = [
        {"measure": f"Outcome {n}", "description": "not read", "timeFrame": f"{n} weeks"}
        for n in range(1, 6)
    ]

    read = facts(study)

    assert read.primary_outcomes == tuple(
        PlannedOutcome(f"Outcome {n}", f"{n} weeks") for n in range(1, 4)
    )
    assert read.primary_outcomes_total == 5


def test_planned_outcome_is_in_the_registrys_words(load: Load):
    assert facts(load("study_NCT01596231_results")).primary_outcomes == (
        PlannedOutcome("Drinking Behaviors", "Study end"),
    )


def test_terminated_trial_with_a_stated_reason_carries_it(load: Load):
    """Scenario: Terminated trial with a stated reason"""
    study = load("study_NCT02586935")
    protocol(study)["statusModule"] |= {
        "overallStatus": "TERMINATED",
        "whyStopped": "Sponsor decision",
    }

    assert facts(study).why_stopped == "Sponsor decision"


def test_terminated_trial_with_no_stated_reason_carries_none(load: Load):
    """Scenario: Terminated trial with no stated reason"""
    study = load("study_NCT02586935")
    protocol(study)["statusModule"]["overallStatus"] = "TERMINATED"
    protocol(study)["statusModule"].pop("whyStopped", None)

    assert facts(study).why_stopped is None


# --- 2.4 posted results ---------------------------------------------------------------


def test_two_group_trial_with_one_primary_outcome(load: Load):
    """Scenario: Two-group trial with one primary outcome"""
    results = facts(load("study_NCT01596231_results")).results

    assert results is not None and results.outcomes_total == 1
    [outcome] = results.outcomes
    assert (outcome.title, outcome.time_frame, outcome.unit) == (
        "Drinking Behaviors",
        "Study end",
        "beers consumed",
    )
    assert (outcome.measure, outcome.spread_kind, outcome.rows) == (
        "mean",
        "Standard Deviation",
        1,
    )
    assert outcome.groups == (
        ResultGroup("Placebo", analysed="10", value="3.4", spread="1.1", lower=None, upper=None),
        ResultGroup("Kudzu", analysed="10", value="1.9", spread="1.3", lower=None, upper=None),
    )


def test_outcome_with_no_posted_comparison_carries_its_values_only(load: Load):
    """Scenario: Outcome with no posted comparison"""
    results = facts(load("study_NCT01596231_results")).results

    assert results is not None
    assert results.outcomes[0].comparisons == ()
    assert all(group.value for group in results.outcomes[0].groups)


def test_record_without_results_carries_no_results(load: Load):
    """Scenario: Record without results"""
    assert facts(load("study_NCT02586935")).results is None


def test_results_for_secondary_outcomes_are_not_carried(load: Load):
    study = load("study_NCT04951479_comparison")
    measures = study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
    assert sum(measure["type"] == "SECONDARY" for measure in measures) == 4

    results = facts(study).results

    assert results is not None and results.outcomes_total == 1
    assert [outcome.title for outcome in results.outcomes] == ["Change in KOOS Pain Score"]


def test_outcome_not_yet_posted_is_not_carried(load: Load):
    study = load("study_NCT01596231_results")
    primary_result(study)["reportingStatus"] = "NOT_POSTED"

    assert facts(study).results is None


def test_at_most_three_posted_primary_outcomes_are_carried_with_their_total(load: Load):
    study = load("study_NCT01596231_results")
    module = study["resultsSection"]["outcomeMeasuresModule"]
    module["outcomeMeasures"] = [
        primary_result(study) | {"title": f"Outcome {n}"} for n in range(1, 6)
    ]

    results = facts(study).results

    assert results is not None and results.outcomes_total == 5
    assert [outcome.title for outcome in results.outcomes] == [
        "Outcome 1",
        "Outcome 2",
        "Outcome 3",
    ]


@pytest.mark.parametrize(
    ("param_type", "measure"),
    [
        ("GEOMETRIC_LEAST_SQUARES_MEAN", "geometric_least_squares_mean"),
        ("COUNT_OF_UNITS", "count_of_units"),
        ("LOG_MEAN", "log_mean"),
        ("SOMETHING_NEW", None),
    ],
)
def test_kind_of_measure_is_the_registrys_lower_cased(load: Load, param_type, measure):
    study = load("study_NCT01596231_results")
    primary_result(study)["paramType"] = param_type

    results = facts(study).results

    assert results is not None and results.outcomes[0].measure == measure


# --- 2.5 posted comparisons and outcomes in several rows ------------------------------


def test_posted_comparison_carries_its_groups_p_value_method_and_test(load: Load):
    results = facts(load("study_NCT04951479_comparison")).results

    assert results is not None
    [outcome] = results.outcomes
    assert (outcome.measure, outcome.spread_kind) == ("median", "Inter-Quartile Range")
    assert outcome.groups == (
        ResultGroup(
            "Genicular Artery Embolization Arm",
            analysed="10",
            value="33",
            spread=None,
            lower="22",
            upper="47",
        ),
    )
    assert outcome.comparisons == (
        Comparison(
            groups=("Genicular Artery Embolization Arm",),
            p_value="0.00041",
            method="t-test, 2 sided",
            test="superiority",
        ),
    )


def test_comparison_posted_as_less_than_keeps_the_registrys_words(load: Load):
    """Scenario: Comparison posted as '<0.001'"""
    study = load("study_NCT04951479_comparison")
    primary_result(study)["analyses"][0] |= {"pValue": "<0.001", "statisticalMethod": "ANCOVA"}

    results = facts(study).results

    assert results is not None
    comparison = results.outcomes[0].comparisons[0]
    assert (comparison.p_value, comparison.method) == ("<0.001", "ANCOVA")


def test_comparison_posted_without_a_p_value_is_still_carried(load: Load):
    study = load("study_NCT04951479_comparison")
    analysis = primary_result(study)["analyses"][0]
    del analysis["pValue"]
    analysis |= {"paramType": "Mean Difference (Final Values)", "paramValue": "4.2"}

    results = facts(study).results

    assert results is not None
    [comparison] = results.outcomes[0].comparisons
    assert comparison.p_value is None and comparison.groups == (
        "Genicular Artery Embolization Arm",
    )
    assert "4.2" not in json.dumps(asdict(comparison))


@pytest.mark.parametrize(
    ("registry_test", "test"),
    [
        ("NON_INFERIORITY", "non_inferiority"),
        ("EQUIVALENCE", "equivalence"),
        ("NON_INFERIORITY_OR_EQUIVALENCE", None),
        ("SUPERIORITY_OR_OTHER", None),
        ("OTHER", None),
    ],
)
def test_only_three_kinds_of_test_are_named(load: Load, registry_test, test):
    study = load("study_NCT04951479_comparison")
    primary_result(study)["analyses"][0]["nonInferiorityType"] = registry_test

    results = facts(study).results

    assert results is not None and results.outcomes[0].comparisons[0].test == test


def test_outcome_reported_in_several_rows_carries_a_row_count_and_no_values(load: Load):
    """Scenario: Outcome reported at four time points (here, three categories)"""
    results = facts(load("study_NCT03491397_rows")).results

    assert results is not None
    [outcome] = results.outcomes
    assert outcome.title.startswith("Number of Participants Experiencing")
    assert outcome.time_frame == "Up to 12 Months after GAE"
    assert (outcome.rows, outcome.groups, outcome.comparisons) == (3, (), ())


def test_outcome_with_a_comparison_in_several_rows_carries_no_comparison(load: Load):
    study = load("study_NCT04951479_comparison")
    measure = primary_result(study)
    measure["classes"] = [
        {
            "title": f"Month {month}",
            "categories": copy.deepcopy(measure["classes"][0]["categories"]),
        }
        for month in (1, 3, 6, 12)
    ]

    results = facts(study).results

    assert results is not None
    assert (results.outcomes[0].rows, results.outcomes[0].comparisons) == (4, ())


# --- 2.6 state, and what is never read ------------------------------------------------


@pytest.mark.parametrize(
    ("overall_status", "state"),
    [
        ("RECRUITING", "under_way"),
        ("ENROLLING_BY_INVITATION", "under_way"),
        ("ACTIVE_NOT_RECRUITING", "under_way"),
        ("NOT_YET_RECRUITING", "not_started"),
        ("COMPLETED", "completed"),
        ("SUSPENDED", "suspended"),
        ("TERMINATED", "terminated"),
        ("WITHDRAWN", "withdrawn"),
        ("UNKNOWN", "unknown"),
        ("AVAILABLE", "unknown"),
        (None, "unknown"),
    ],
)
def test_registry_status_is_reduced_to_seven_states(load: Load, overall_status, state):
    """Scenario: Recruiting trial"""
    study = load("study_NCT02586935")
    protocol(study)["statusModule"]["overallStatus"] = overall_status

    assert read_trial(study).state == state


@pytest.mark.parametrize(
    ("reported", "state"),
    [
        (None, "not_started"),
        (TrialState.STARTED, "under_way"),
        (TrialState.COMPLETED, "completed"),
        (TrialState.SUSPENDED, "suspended"),
        (TrialState.TERMINATED, "terminated"),
        (TrialState.WITHDRAWN, "withdrawn"),
    ],
)
def test_trial_with_no_record_takes_its_state_from_its_newest_status_change(reported, state):
    assert reported_state(reported) == state


def test_sponsors_description_of_a_results_group_is_not_carried(load: Load):
    """Scenario: Group described as having improved significantly"""
    study = load("study_NCT01596231_results")
    assert "significantly reduced" in json.dumps(study)

    read = facts(study)

    assert read.results is not None and read.results.outcomes[0].groups[1].title == "Kudzu"
    assert "significantly reduced" not in json.dumps(asdict(read))


def test_descriptions_eligibility_locations_and_contacts_are_never_read(load: Load):
    """Scenario: Recruiting trial: the facts carry no location or contact"""
    study = load("study_NCT04951479_comparison")
    marker = "UNREAD-TEXT"
    section = protocol(study)
    section["statusModule"]["overallStatus"] = "RECRUITING"
    section["descriptionModule"] = {"briefSummary": marker, "detailedDescription": marker}
    section["eligibilityModule"]["eligibilityCriteria"] = marker
    section["contactsLocationsModule"] = {
        "centralContacts": [{"name": marker, "email": "contact@example.org", "phone": "555"}],
        "locations": [{"facility": marker, "city": marker, "status": "RECRUITING"}],
        "overallOfficials": [{"name": marker, "affiliation": marker}],
    }
    section["sponsorCollaboratorsModule"]["responsibleParty"] |= {
        "investigatorFullName": marker,
        "investigatorAffiliation": marker,
    }
    for outcome in section["outcomesModule"]["primaryOutcomes"]:
        outcome["description"] = marker
    measure = primary_result(study)
    measure |= {"description": marker, "populationDescription": marker}
    for group in measure["groups"]:
        group["description"] = marker
    measure["analyses"][0] |= {
        "groupDescription": marker,
        "statisticalComment": marker,
        "pValueComment": marker,
        "estimateComment": marker,
    }

    trial = read_trial(study)

    assert trial.state == "under_way"
    text = json.dumps(asdict(trial))
    assert marker not in text and "example.org" not in text and "RECRUITING" not in text


# --- 2.7 tolerant reads ---------------------------------------------------------------


def test_record_holding_only_an_identification_module_gives_empty_facts(load: Load):
    study = load("study_NCT02586935")
    identification = protocol(study)["identificationModule"]

    trial = read_trial({"protocolSection": {"identificationModule": identification}})

    assert trial.title == identification["briefTitle"]
    assert trial.state == "unknown"
    assert trial.facts == TrialFacts(
        study_kind=None,
        participants=None,
        allocation=None,
        masking=None,
        comparators=(),
        healthy_volunteers=None,
        age_groups=(),
        sponsor=None,
        primary_outcomes=(),
        primary_outcomes_total=0,
        why_stopped=None,
        results=None,
    )


@pytest.mark.parametrize(
    "spoil",
    [
        lambda study: study["protocolSection"].update(designModule=["not", "an", "object"]),
        lambda study: study["protocolSection"]["designModule"].update(enrollmentInfo="83"),
        lambda study: study["protocolSection"]["designModule"]["enrollmentInfo"].pop("type"),
        lambda study: study["protocolSection"]["armsInterventionsModule"].update(armGroups={}),
        lambda study: study["protocolSection"]["eligibilityModule"].update(stdAges="ADULT"),
        lambda study: study["protocolSection"]["sponsorCollaboratorsModule"].update(
            leadSponsor="Mclean Hospital"
        ),
        lambda study: study["protocolSection"]["outcomesModule"].update(primaryOutcomes=[{}, 3]),
        lambda study: study.update(resultsSection=None),
        lambda study: study["resultsSection"]["outcomeMeasuresModule"].update(
            outcomeMeasures=[{"type": "PRIMARY", "reportingStatus": "POSTED"}]
        ),
        lambda study: primary_result(study).update(
            groups=[{"id": "OG000"}, "x"], denoms=[], classes=[{"categories": [{}]}]
        ),
        lambda study: primary_result(study)["classes"][0]["categories"][0].update(
            measurements=[{"groupId": ["OG000"], "value": 3.4}]
        ),
    ],
)
def test_missing_or_oddly_shaped_fields_give_absent_facts_and_no_error(load: Load, spoil):
    study = load("study_NCT01596231_results")
    spoil(study)

    trial = read_trial(study)

    assert trial.title == "Kudzu Treatment for Alcohol Abuse"


def test_size_without_a_stated_basis_is_not_given(load: Load):
    """A fact the record does not state is absent, not inferred."""
    study = load("study_NCT02586935")
    del protocol(study)["designModule"]["enrollmentInfo"]["type"]

    assert facts(study).participants is None


def test_registry_record_is_told_apart_from_details_entered_by_hand(load: Load):
    assert is_registry_record(load("study_NCT02586935"))
    assert not is_registry_record({"entered_by": "operator", "external_id": "jRCT2051240154"})
    assert not is_registry_record({"protocolSection": "not an object"})
