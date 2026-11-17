"""The terms of a stored trial a headline could hold. Scenario names are from openspec
trial-report-links (change trial-first-route). Every name here is synthetic."""

from thenwhat.backfill.trial_terms import (
    acronym_words,
    code_forms,
    codes_of,
    condition_words,
    other_names_of,
)


def test_a_development_code_is_found_among_names_and_other_names_once():
    """Scenario: A development code"""
    interventions = [
        {"type": "DRUG", "name": "TARA-002 solution", "otherNames": ["tara002", "MEDI4736"]},
        {"type": "DRUG", "name": "Placebo"},
    ]

    assert codes_of(interventions) == ["TARA-002", "MEDI4736"]
    assert code_forms("TARA-002") == {("tara", "002"), ("tara002",)}


def test_a_virus_an_antigen_and_two_digits_are_not_codes():
    interventions = [
        {"type": "BIOLOGICAL", "name": "COVID-19 vaccine", "otherNames": ["IL-17 blocker"]},
        {"type": "DRUG", "name": "CD123 antibody", "otherNames": ["NCT01234567"]},
    ]

    assert codes_of(interventions) == []


def test_only_an_acronym_that_carries_a_number_can_tell_a_study():
    """Scenarios: An acronym with a number, A study's acronym"""
    assert acronym_words("KEYNOTE-789") == ("keynote", "789")
    assert acronym_words("HOPE") is None
    assert acronym_words("RECOVERY") is None
    assert acronym_words("AB-12") is None
    assert acronym_words(None) is None


def test_other_names_are_a_drugs_and_never_general_words():
    """Scenarios: A brand name, A class of treatments"""
    interventions = [
        {"type": "DRUG", "name": "Exavir", "otherNames": ["Brandvir", "TARA-002", "Cancer drug"]},
        {"type": "BEHAVIORAL", "name": "Walking", "otherNames": ["Stepping"]},
    ]

    assert other_names_of(interventions, "Exavir") == ["Brandvir"]


def test_condition_words_leave_out_general_and_short_words():
    assert condition_words(["Bladder Cancer", "Crohn's disease of the gut"]) == frozenset(
        {"bladder", "crohn"}
    )
