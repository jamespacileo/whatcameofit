"""Telling a name from a description.

A news article calls a treatment "the drug" or "a one-time gene-editing treatment" as
often as it names it. Recorded as another name, a description is sent to the registries
as a search term and brings back thousands of unrelated trials.
"""

import re

# Words that open a description, never a name.
OPENERS = frozenset(
    [
        "the",
        "a",
        "an",
        "this",
        "that",
        "these",
        "those",
        "new",
        "novel",
        "experimental",
        "investigational",
        "one-time",
        "daily",
        "weekly",
        "once-daily",
        "once-weekly",
        "non-surgical",
        "under-the-skin",
    ]
)
# What a description ends in: the kind of thing, not which one.
KINDS = frozenset(
    [
        "pill",
        "pills",
        "drug",
        "drugs",
        "treatment",
        "treatments",
        "therapy",
        "therapies",
        "procedure",
        "medicine",
        "medication",
        "jab",
        "jabs",
        "shot",
        "shots",
        "injection",
        "injections",
        "infusion",
        "vaccine",
        "vaccines",
        "implant",
        "implants",
        "device",
        "devices",
        "tablet",
        "tablets",
        "capsule",
        "spray",
        "gel",
        "cream",
        "surgery",
        "operation",
        "technique",
        "method",
        "approach",
        "compound",
        "molecule",
        "peptide",
        "antibody",
    ]
)

# Words for a class of treatments: every member of the class, not one of them. A code
# in the phrase does not make it one treatment: "GLP-1 receptor agonists", "PD-1
# inhibitor". "Receptor" goes with them, since it names a target, not a treatment.
CLASS_WORDS = frozenset(
    [
        "agonist",
        "agonists",
        "antagonist",
        "antagonists",
        "inhibitor",
        "inhibitors",
        "blocker",
        "blockers",
        "analog",
        "analogs",
        "analogue",
        "analogues",
        "modulator",
        "modulators",
        "mimetic",
        "mimetics",
        "receptor",
        "receptors",
    ]
)
# Kinds of thing in the plural: several treatments, whatever comes before.
PLURAL_KINDS = frozenset(
    [
        "drugs",
        "medications",
        "medicines",
        "treatments",
        "therapies",
        "vaccines",
        "antibodies",
        "prescriptions",
        # Classes of drug named by their plural (batch 2 and 3 audits, 2026-11-16).
        "statins",
        "antidepressants",
        "insulins",
        "opioids",
        "antibiotics",
        "antivirals",
        "immunotherapies",
        "vaccinations",
        "boosters",
        "regimens",
        "biologics",
        "psychedelics",
    ]
)
# The plural of a code: "GLP-1s", "SGLT2s". A code names a target or a family when it
# takes a plural; one product does not.
PLURAL_CODE = re.compile(r"[A-Za-z]{2,}-?\d+[A-Za-z]?s")
# What a name is said to be for, set aside before it is judged: "GLP-1 drugs for obesity".
FOR = re.compile(r"\bfor\b", re.IGNORECASE)
PUNCTUATION = ".,;:()[]"


def is_a_class(text: str) -> bool:
    """Whether the text names a class of treatments, not one treatment, with or without
    a code. "Semaglutide" is one; "GLP-1 drugs", "GLP-1s" and "GLP-1 receptor agonist
    prescriptions" are many. What the name is said to be for is set aside first.

    What comes before a word for a class is its target ("glucagon receptor agonist"), so
    a class word marks the name unless a name follows it: "PD-1 inhibitor pembrolizumab"
    names pembrolizumab, "PD-1 inhibitor" names none. A kind of thing after it ("agonist
    pill") is no name.
    """
    words = [word.strip(PUNCTUATION) for word in FOR.split(text, maxsplit=1)[0].split()]
    words = [word for word in words if word]
    if not words:
        return False
    if words[-1].lower() in PLURAL_KINDS or any(PLURAL_CODE.fullmatch(word) for word in words):
        return True
    marked = [at for at, word in enumerate(words) if word.lower() in CLASS_WORDS]
    if not marked:
        return False
    after = [word for word in words[marked[-1] + 1 :] if word.lower() not in KINDS]
    return not after or not is_a_name(" ".join(after))


def is_a_name(text: str) -> bool:
    """Whether the text names an intervention: a brand, a code or a generic name.

    A phrase that opens like a description is not a name. Nor is a phrase of several
    words that ends in a kind of thing, unless it carries a code such as "BPL-003".
    """
    words = text.split()
    if not words:
        return False
    if words[0].lower() in OPENERS:
        return False
    has_code = any(any(character.isdigit() for character in word) for word in words)
    ends_in_a_kind = len(words) > 1 and words[-1].lower() in KINDS
    return has_code or not ends_in_a_kind


def is_a_search_phrase(text: str) -> bool:
    """Whether the text says which treatment: words a registry would file it under.

    "The device" or "new treatment" says only what kind of thing it is. Once the words
    that open a description are set aside, something other than a kind must remain.
    """
    words = [word.lower() for word in text.split()]
    while words and words[0] in OPENERS:
        words = words[1:]
    return any(word not in KINDS for word in words)


# Words of a vaccine or a schedule that hold no product: "COVID-19 vaccine", "third
# dose of COVID-19 vaccine", "2024-2025 dose", "three-dose vaccination".
SCHEDULE_WORDS = frozenset(
    [
        "vaccine", "vaccines", "vaccination", "vaccinations", "booster", "boosters",
        "dose", "doses", "dosing", "regimen", "regimens", "shot", "shots", "jab", "jabs",
        "immunisation", "immunization", "of", "the", "a", "an", "for", "against", "and",
        "first", "second", "third", "fourth", "fifth", "single", "updated", "seasonal",
        "annual", "bivalent", "monovalent", "coronavirus", "covid", "covid-19",
        "sars-cov-2", "flu", "influenza",
    ]
)  # fmt: skip
_SCHEDULE_PATTERN = re.compile(r"\d+(?:st|nd|rd|th)|\d{4}(?:[-\u2013/]\d{2,4})?|\w+-dose|\d+")
SCHEDULE_MARKERS = frozenset(
    ["vaccine", "vaccines", "vaccination", "vaccinations", "booster", "boosters", "dose",
     "doses", "dosing", "regimen", "regimens", "immunisation", "immunization"]
)  # fmt: skip


def names_no_product(intervention: str, indication: str) -> bool:
    """Whether a vaccine or schedule name holds no product once the condition's own
    words are left out: "COVID-19 vaccination" for prevention of COVID-19 does;
    "Pfizer-BioNTech COVID-19 vaccine" does not."""
    words = [word.strip(PUNCTUATION).lower() for word in intervention.split()]
    words = [word for word in words if word]
    if (
        not words
        or not SCHEDULE_MARKERS & set(words)
        and not any(word.endswith("-dose") for word in words)
    ):
        return False
    condition = {word.strip(PUNCTUATION).lower() for word in indication.split()}
    left = [
        word
        for word in words
        if word not in SCHEDULE_WORDS
        and word not in condition
        and not _SCHEDULE_PATTERN.fullmatch(word)
    ]
    return not left


# A condition that names no one condition: "Cancer". Words of an animal's condition: a
# claim is about people.
NO_ONE_CONDITION = frozenset(
    ["cancer", "cancers", "tumour", "tumours", "tumor", "tumors", "solid tumours",
     "solid tumors", "disease", "diseases"]
)  # fmt: skip
ANIMAL_WORDS = frozenset(
    ["feline", "canine", "equine", "bovine", "veterinary", "cats", "dogs", "horses",
     "cattle", "pets"]
)  # fmt: skip


def condition_refusal(indication: str) -> str | None:
    """Why a read's condition cannot make a claim, or None: it names no one condition,
    or it is an animal's."""
    words = [word.strip(PUNCTUATION).lower() for word in indication.split()]
    if " ".join(words) in NO_ONE_CONDITION:
        return "no one condition"
    if ANIMAL_WORDS & set(words):
        return "an animal's condition"
    return None
