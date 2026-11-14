"""What an index record says of its paper, and which papers a registry record names
for its trial. Pure functions on recorded fixtures. Scenario names are from openspec
paper-facts."""

import copy
import json
from typing import Any

import pytest

from thenwhat.events.paper_facts import NOT_STORED, read_paper, reduced
from thenwhat.events.trial_facts import ResultsPaper, read_trial

PLACEHOLDER = "Abstract replaced in this fixture. The recorded text is not kept."
TRIAL_REPORT = "europepmc/pmid_35658024_trial_report.json"
PREPRINT = "europepmc/paper_preprint_299164.json"
HUMANS_AND_ANIMALS = "europepmc/pmid_41363554_humans_animals.json"
RETRACTED = "europepmc/pmid_9500320_retracted.json"


def record(fixture_json, name: str) -> dict[str, Any]:
    return copy.deepcopy(fixture_json(name)["resultList"]["result"][0])


@pytest.mark.parametrize("name", [TRIAL_REPORT, PREPRINT, HUMANS_AND_ANIMALS, RETRACTED])
def test_recorded_fixture_loads_and_holds_no_abstract_text(fixture_json, name: str):
    paper = record(fixture_json, name)

    assert paper["title"]
    assert paper.get("abstractText", PLACEHOLDER) == PLACEHOLDER


def test_paper_in_a_journal(fixture_json):
    """Scenario: Paper in a journal"""
    facts = read_paper(record(fixture_json, HUMANS_AND_ANIMALS))

    assert facts.title == "Melatonin and the Dental Pulp: A Scoping Review."
    assert (facts.journal, facts.year) == ("International endodontic journal", 2026)
    assert facts.open_access is True


def test_report_of_a_phase_3_randomised_trial(fixture_json):
    """Scenario: Report of a Phase 3 randomised trial"""
    facts = read_paper(record(fixture_json, TRIAL_REPORT))

    assert facts.kinds == ("randomised_trial", "clinical_trial", "article")
    assert (facts.journal, facts.year) == ("The New England journal of medicine", 2022)
    assert (facts.open_access, facts.retracted) == (False, False)
    assert facts.studied_in == ("people",)


def test_preprint(fixture_json):
    """Scenario: Preprint"""
    facts = read_paper(record(fixture_json, PREPRINT))

    assert facts.kinds == ("preprint",)
    # A preprint is in no journal, and a recent record carries no subject headings.
    assert (facts.journal, facts.year, facts.studied_in) == (None, 2020, ())


def test_publication_type_with_no_mapping_adds_no_kind():
    facts = read_paper({"pubTypeList": {"pubType": ["Video-Audio Media", "Journal Article"]}})

    assert facts.kinds == ("article",)


def test_kinds_are_listed_from_most_to_least_specific():
    types = ["Journal Article", "Review", "Meta-Analysis", "Systematic Review", "Editorial"]

    facts = read_paper({"pubTypeList": {"pubType": types}})

    assert facts.kinds == ("meta_analysis", "systematic_review", "review", "comment", "article")


def headings(*names: str) -> dict[str, Any]:
    return {"meshHeadingList": {"meshHeading": [{"descriptorName": name} for name in names]}}


@pytest.mark.parametrize(
    ("record_headings", "studied_in"),
    [
        (headings("Animals", "Mice"), ("animals",)),  # Scenario: Study in mice
        (headings("Humans", "Animals"), ("people", "animals")),  # ... in people and animals
        (headings("Humans", "Adult"), ("people",)),
        (headings("Cells, Cultured"), ()),  # Scenario: Laboratory study with neither heading
        (headings("Mice"), ()),  # nothing is guessed from a species
        ({}, ()),  # Scenario: Record with no index terms yet
    ],
)
def test_people_or_animals_is_read_from_two_headings_only(record_headings, studied_in):
    assert read_paper(record_headings).studied_in == studied_in


def test_study_in_people_and_animals_on_a_recorded_paper(fixture_json):
    """Scenario: Study in people and animals"""
    assert read_paper(record(fixture_json, HUMANS_AND_ANIMALS)).studied_in == ("people", "animals")


def test_retracted_paper_is_marked(fixture_json):
    """Scenario: Retracted results paper (the mark itself)"""
    facts = read_paper(record(fixture_json, RETRACTED))

    assert facts.retracted is True
    assert facts.kinds == ("article",)


def test_oddly_shaped_record_reads_as_absent_facts():
    facts = read_paper({"pubTypeList": "Journal Article", "journalInfo": [], "pubYear": 2021})

    assert (facts.title, facts.journal, facts.year, facts.kinds) == (None, None, None, ())
    assert (facts.open_access, facts.retracted, facts.studied_in) == (None, False, ())


def test_record_with_an_abstract_and_authors_is_reduced(fixture_json):
    """Scenario: Record with an abstract and eleven authors"""
    paper = record(fixture_json, TRIAL_REPORT)
    names = [author["lastName"] for author in paper["authorList"]["author"]]
    assert names and paper["abstractText"] and paper["authorString"]

    kept = reduced(paper)

    assert not set(NOT_STORED) & set(kept)
    stored = json.dumps(kept)
    assert PLACEHOLDER not in stored
    assert not [name for name in names if name in stored]
    # What the facts are read from is still there.
    assert read_paper(kept) == read_paper(paper)


# --- results papers of a trial ---------------------------------------------------------


def references(*entries: tuple[str | None, str]) -> dict[str, Any]:
    listed = [
        {"type": kind, "citation": "Example A, Sample B. A made-up citation. J Ex. 2020."}
        | ({"pmid": pubmed_id} if pubmed_id else {})
        for pubmed_id, kind in entries
    ]
    return {"protocolSection": {"referencesModule": {"references": listed}}}


def test_paper_linked_by_the_registry(fixture_json):
    """Scenario: Paper linked by the registry"""
    study = fixture_json("clinicaltrials/study_NCT01596231_results.json")

    assert read_trial(study).results_papers == (ResultsPaper("26048637", "linked_by_registry"),)


def test_trial_whose_sponsor_listed_a_results_paper():
    """Scenario: Trial whose sponsor listed a results paper"""
    study = references(
        ("111", "BACKGROUND"),
        ("222", "RESULT"),
        ("333", "BACKGROUND"),
        ("444", "BACKGROUND"),
        ("555", "BACKGROUND"),
    )

    assert read_trial(study).results_papers == (ResultsPaper("222", "listed_by_sponsor"),)


def test_record_with_background_references_only_names_no_results_paper():
    assert read_trial(references(("111", "BACKGROUND"), ("333", "BACKGROUND"))).results_papers == ()


def test_reference_with_no_pubmed_number_attaches_no_paper():
    """Scenario: Reference with no PubMed number"""
    assert read_trial(references((None, "RESULT"), ("PMC12", "DERIVED"))).results_papers == ()


def test_paper_both_listed_and_linked_is_the_sponsors_and_no_citation_is_returned():
    study = references(("222", "DERIVED"), ("222", "RESULT"), ("333", "DERIVED"))

    papers = read_trial(study).results_papers

    assert papers == (
        ResultsPaper("222", "listed_by_sponsor"),
        ResultsPaper("333", "linked_by_registry"),
    )
    assert "citation" not in repr(papers) and "Example A" not in repr(papers)
