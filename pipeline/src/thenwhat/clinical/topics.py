"""Which MeSH categories each reader-friendly topic covers, and the topics a claim's
clinical categories fall under. Pure: no database, network, clock or model.

The mapping is many to many: a topic may cover several descriptors, and a descriptor may
sit under several topics. A topic covers a category when one of the topic's descriptors
is the category or is broader than it in the tree.

Derived topics file nothing. A claim keeps the one vertical it was filed under; what is
derived here is compared with it (`thenwhat clinical compare`) and offered as a
suggestion, until the operator decides otherwise on the measured numbers.

Add a descriptor by its identifier, with NLM's label beside it. The configuration check
refuses a slug that is no vertical, and a descriptor the stored vocabulary does not hold.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from thenwhat.claims.verticals import VERTICAL_GROUPS, VERTICALS
from thenwhat.clinical.vocabulary import Vocabulary

# Vertical slug to the descriptors it covers, each with NLM's label.
TOPIC_DESCRIPTORS: dict[str, tuple[tuple[str, str], ...]] = {
    "ageing": (("D000375", "Aging"),),
    "bones-joints-and-muscles": (
        ("D009140", "Musculoskeletal Diseases"),
        ("D014947", "Wounds and Injuries"),
    ),
    "brain-and-nerves": (("D009422", "Nervous System Diseases"),),
    "cancer": (("D009369", "Neoplasms"),),
    "diabetes-and-hormones": (
        ("D009750", "Nutritional and Metabolic Diseases"),
        ("D004700", "Endocrine System Diseases"),
    ),
    "eyes-and-ears": (("D005128", "Eye Diseases"), ("D004427", "Ear Diseases")),
    "gut-and-liver": (("D004066", "Digestive System Diseases"),),
    "heart-and-circulation": (
        ("D002318", "Cardiovascular Diseases"),
        ("D006425", "Hemic and Lymphatic Diseases"),
    ),
    "immune-system-and-allergies": (("D007154", "Immune System Diseases"),),
    "infections": (("D007239", "Infections"),),
    "kidneys-and-bladder": (("D007674", "Kidney Diseases"), ("D014570", "Urologic Diseases")),
    "lungs-and-breathing": (("D012140", "Respiratory Tract Diseases"),),
    "mental-health": (("D001523", "Mental Disorders"),),
    "mouth-and-teeth": (("D009057", "Stomatognathic Diseases"),),
    "pregnancy-and-fertility": (
        ("D011248", "Pregnancy Complications"),
        ("D007246", "Infertility"),
    ),
    "skin-and-hair": (("D017437", "Skin and Connective Tissue Diseases"),),
    # Specific verticals.
    "dementia": (("D003704", "Dementia"),),
    "gum-disease": (("D010510", "Periodontal Diseases"),),
}


@dataclass(frozen=True, slots=True)
class DerivedTopic:
    topic: str
    # The claim's category that the topic covers, and the topic's descriptor that covers
    # it: the same descriptor, or one broader.
    category: str
    covered_by: str

    @property
    def group(self) -> str:
        return VERTICAL_GROUPS[self.topic]


def mapped_descriptors(
    mapping: Mapping[str, tuple[tuple[str, str], ...]] = TOPIC_DESCRIPTORS,
) -> list[str]:
    """Every descriptor the mapping names, each once."""
    return sorted({identifier for covered in mapping.values() for identifier, _ in covered})


def derived_topics(
    categories: Iterable[str],
    vocabulary: Vocabulary,
    mapping: Mapping[str, tuple[tuple[str, str], ...]] = TOPIC_DESCRIPTORS,
) -> list[DerivedTopic]:
    """Each topic that covers one of the categories, once, with the first category and
    descriptor that put it there. In the order the topics are configured."""
    found: dict[str, DerivedTopic] = {}
    for category in categories:
        reach = vocabulary.at_or_above(category)
        for topic, covered in mapping.items():
            if topic in found:
                continue
            for identifier, _ in covered:
                if identifier in reach:
                    found[topic] = DerivedTopic(topic, category, identifier)
                    break
    return [found[topic] for topic in mapping if topic in found]


def uncovered(
    categories: Iterable[str],
    vocabulary: Vocabulary,
    mapping: Mapping[str, tuple[tuple[str, str], ...]] = TOPIC_DESCRIPTORS,
) -> list[str]:
    """The categories no topic covers."""
    mapped = set(mapped_descriptors(mapping))
    return [category for category in categories if not (vocabulary.at_or_above(category) & mapped)]


def configuration_problems(
    vocabulary: Vocabulary | None = None,
    mapping: Mapping[str, tuple[tuple[str, str], ...]] = TOPIC_DESCRIPTORS,
) -> list[str]:
    """What is wrong with the mapping: a slug that is no vertical, a topic that covers
    nothing and, when the stored vocabulary is given, a descriptor it does not hold."""
    problems: list[str] = []
    for topic, covered in mapping.items():
        if topic not in VERTICALS:
            problems.append(f"The topic mapping names '{topic}', which is no vertical.")
        if not covered:
            problems.append(f"The topic '{topic}' covers no MeSH descriptor.")
        for identifier, label in covered:
            if vocabulary is not None and identifier not in vocabulary:
                problems.append(
                    f"The topic '{topic}' covers {identifier} ({label}), which the stored"
                    " MeSH vocabulary does not hold."
                )
    return problems
