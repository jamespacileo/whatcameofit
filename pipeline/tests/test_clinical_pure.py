"""Clinical categories, the tree and the topic mapping: the pure parts, on recorded and
synthetic records. Behavior: openspec clinical-classification."""

from typing import Any

from thenwhat.clinical.categories import (
    Category,
    Source,
    derive,
    paper_major_headings,
    trial_terms,
)
from thenwhat.clinical.topics import (
    TOPIC_DESCRIPTORS,
    configuration_problems,
    derived_topics,
    uncovered,
)
from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.sources.mesh import broader_descriptors, tree_numbers

YEAR = "http://id.nlm.nih.gov/mesh/2026"


def descriptor(
    identifier: str, label: str, trees: list[str], broader: list[str]
) -> tuple[str, dict[str, Any]]:
    """A stored descriptor record, as NLM's service gives it."""
    return identifier, {
        "term": {
            "@id": f"{YEAR}/{identifier}",
            "identifier": identifier,
            "label": {"@language": "en", "@value": label},
            "treeNumber": [f"{YEAR}/{tree}" for tree in trees],
            "broaderDescriptor": [f"{YEAR}/{one}" for one in broader]
            if len(broader) != 1
            else f"{YEAR}/{broader[0]}",
        },
        "concept": None,
    }


VOCABULARY = Vocabulary(
    [
        descriptor("D009750", "Nutritional and Metabolic Diseases", ["C18"], []),
        descriptor("D009748", "Nutrition Disorders", ["C18.654"], ["D009750"]),
        descriptor("D044342", "Overnutrition", ["C18.654.726"], ["D009748"]),
        descriptor("D050177", "Overweight", ["C18.654.726.750", "C23.888.144.699"], ["D044342"]),
        descriptor(
            "D009765",
            "Obesity",
            ["C18.654.726.750.500", "C23.888.144.699.500"],
            ["D050177"],
        ),
        descriptor("D005128", "Eye Diseases", ["C11"], []),
        descriptor("D012164", "Retinal Diseases", ["C11.768"], ["D005128"]),
        descriptor("D004700", "Endocrine System Diseases", ["C19"], []),
        descriptor("D003920", "Diabetes Mellitus", ["C18.452.394", "C19.246"], ["D004700"]),
        descriptor(
            "D003930",
            "Diabetic Retinopathy",
            ["C11.768.257", "C19.246.099.500.382"],
            ["D012164", "D003920"],
        ),
        descriptor("D006801", "Humans", ["B01.050.150.900.649.313.988.400.112.400.400"], []),
        descriptor("D000375", "Aging", ["G07.345.124"], []),
        descriptor("D012871", "Skin Diseases", ["C17.800"], []),
    ]
)


# --- the tree --------------------------------------------------------------------------


def test_a_stored_descriptor_gives_its_tree_numbers_and_what_is_broader(fixture_json):
    payload = {"term": fixture_json("mesh/descriptor_obesity.json"), "concept": None}

    assert tree_numbers(payload) == ("C18.654.726.750.500", "C23.888.144.699.500")
    assert broader_descriptors(payload) == ("D050177",)


def test_a_descriptor_in_two_places_is_below_both():
    """Scenario: Descriptor in two places"""
    above = VOCABULARY.above("D003930")

    assert {"D012164", "D005128", "D003920", "D004700"} == set(above)
    assert VOCABULARY.at_or_above("D003930") == above | {"D003930"}


def test_wolfram_does_not_inherit_the_unrelated_immune_placement_of_type_one_diabetes():
    vocab = Vocabulary(
        [
            descriptor("D000001", "Metabolic diseases", ["C18"], []),
            descriptor("D000002", "Immune diseases", ["C20"], []),
            descriptor("D000003", "Type 1 diabetes", ["C18.100", "C20.100"], ["D000001", "D000002"]),
            descriptor("D000004", "Wolfram syndrome", ["C18.100.100"], ["D000003"]),
        ]
    )
    assert vocab.above("D000004") == {"D000003", "D000001"}
    assert vocab.above("D000003") == {"D000001", "D000002"}


def test_missing_names_each_record_the_tree_still_needs():
    """Scenario: Record not yet read"""
    partial = Vocabulary([descriptor("D009765", "Obesity", ["C18.654.726.750.500"], ["D050177"])])

    assert partial.missing(["D009765", "D003930"]) == ["D003930", "D050177"]
    assert VOCABULARY.missing(["D009765", "D003930"]) == []


def test_the_vocabulary_states_its_year_and_finds_a_label_whatever_its_case():
    assert VOCABULARY.years() == ["2026"]
    found = VOCABULARY.labelled("diabetic  retinopathy")
    assert found is not None and found.identifier == "D003930"
    assert VOCABULARY.labelled("Retinopathy") is None


# --- categories ------------------------------------------------------------------------


def trial(*meshes: tuple[str, str], ancestors: tuple[tuple[str, str], ...] = ()) -> dict[str, Any]:
    def listed(terms: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
        return [{"id": identifier, "term": label} for identifier, label in terms]

    return {
        "derivedSection": {
            "conditionBrowseModule": {"meshes": listed(meshes), "ancestors": listed(ancestors)}
        }
    }


def paper(*headings: tuple[str, str], qualifier_major: str | None = None) -> dict[str, Any]:
    listed: list[dict[str, Any]] = [
        {"majorTopic_YN": major, "descriptorName": label} for label, major in headings
    ]
    if qualifier_major:
        listed.append(
            {
                "majorTopic_YN": "N",
                "descriptorName": qualifier_major,
                "meshQualifierList": {
                    "meshQualifier": [{"majorTopic_YN": "Y", "qualifierName": "drug therapy"}]
                },
            }
        )
    return {"meshHeadingList": {"meshHeading": listed}}


def test_a_trials_direct_terms_are_read_and_its_ancestors_are_not(fixture_json):
    """Scenarios: Trial with a condition term; Ancestor is not a category"""
    recorded = fixture_json("clinicaltrials/study_NCT06497504_conditions.json")
    module = recorded["derivedSection"]["conditionBrowseModule"]

    read = trial_terms(recorded)

    assert read == [(entry["id"], entry["term"]) for entry in module["meshes"]]
    assert not {entry["id"] for entry in module["ancestors"]} & {one for one, _ in read}


def test_a_recorded_papers_major_headings_are_read(fixture_json):
    recorded = fixture_json("europepmc/pmid_35658024_trial_report.json")
    record = recorded["resultList"]["result"][0] if "resultList" in recorded else recorded

    assert "Obesity" in paper_major_headings(record)
    assert "Humans" not in paper_major_headings(record)


def test_two_records_that_give_one_category_are_both_named():
    """Scenario: Two sources"""
    derived = derive(
        [("NCT1", trial(("D009765", "Obesity"))), ("NCT1", trial(("D009765", "Obesity")))],
        [("pmid:1", paper(("Obesity", "Y")))],
        VOCABULARY,
    )

    assert derived.categories == (
        Category("D009765", "Obesity", (Source("paper", "pmid:1"), Source("trial", "NCT1"))),
    )


def test_only_a_papers_major_condition_headings_are_categories():
    """Scenarios: Claim with no trial; Heading that is not a condition; Heading that is
    not a major topic"""
    derived = derive(
        [],
        [
            (
                "pmid:2",
                paper(
                    ("Humans", "Y"),
                    ("Aging", "Y"),
                    ("Diabetes Mellitus", "N"),
                    qualifier_major="Obesity",
                ),
            )
        ],
        VOCABULARY,
    )

    assert [category.identifier for category in derived.categories] == ["D009765"]
    assert derived.unread_headings == ()


def test_a_major_heading_whose_descriptor_is_not_stored_is_reported_not_guessed():
    derived = derive([], [("pmid:3", paper(("Periodontitis", "Y")))], VOCABULARY)

    assert derived.categories == ()
    assert derived.unread_headings == ("Periodontitis",)


def test_a_trials_term_outside_the_disease_trees_is_still_its_category():
    derived = derive([("NCT2", trial(("D000375", "Aging")))], [], VOCABULARY)

    assert [category.label for category in derived.categories] == ["Aging"]


def test_no_records_give_no_category():
    """Scenario: Claim with no approved trial or paper"""
    assert derive([], [], VOCABULARY).categories == ()


# --- the topic mapping -----------------------------------------------------------------

WEIGHT = {"weight-loss": (("D009765", "Obesity"), ("D050177", "Overweight"))}


def test_a_topic_covers_a_category_below_one_of_its_descriptors():
    """Scenario: One topic, several categories"""
    topics = derived_topics(["D009765"], VOCABULARY)

    assert [(one.topic, one.category, one.covered_by) for one in topics] == [
        ("diabetes-and-hormones", "D009765", "D009750")
    ]


def test_a_claim_falls_under_every_topic_that_covers_one_of_its_categories():
    """Scenario: One claim, several topics"""
    topics = derived_topics(["D003930"], VOCABULARY)

    assert [one.topic for one in topics] == ["diabetes-and-hormones", "eyes-and-ears"]
    assert {one.group for one in topics} == {"diabetes-and-hormones", "eyes-and-ears"}


def test_a_category_no_topic_covers_is_listed_as_uncovered():
    """Scenario: Category no topic covers"""
    assert derived_topics(["D012871"], VOCABULARY) == []
    assert uncovered(["D012871", "D009765"], VOCABULARY) == ["D012871"]


def test_the_configured_mapping_names_only_verticals():
    assert configuration_problems() == []
    assert all(covered for covered in TOPIC_DESCRIPTORS.values())


def test_an_unknown_descriptor_or_slug_in_the_mapping_is_refused():
    """Scenario: Unknown descriptor in the mapping"""
    mapping = {"cancer": (("D999999", "Not a term"),), "weight-loss": WEIGHT["weight-loss"]}

    assert configuration_problems(VOCABULARY, mapping) == [
        "The topic 'cancer' covers D999999 (Not a term), which the stored MeSH vocabulary"
        " does not hold.",
        "The topic mapping names 'weight-loss', which is no vertical.",
    ]
