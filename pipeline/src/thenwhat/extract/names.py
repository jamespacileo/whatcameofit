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

    A word for a class marks the name only when nothing that is a name is left once the
    class words and codes are taken out: "PD-1 inhibitor pembrolizumab" names
    pembrolizumab, "PD-1 inhibitor" names none.
    """
    words = [word.strip(PUNCTUATION) for word in FOR.split(text, maxsplit=1)[0].split()]
    words = [word for word in words if word]
    if not words:
        return False
    if words[-1].lower() in PLURAL_KINDS or any(PLURAL_CODE.fullmatch(word) for word in words):
        return True
    if not any(word.lower() in CLASS_WORDS for word in words):
        return False
    left = [
        word
        for word in words
        if word.lower() not in CLASS_WORDS and not any(ch.isdigit() for ch in word)
    ]
    return not left or not is_a_name(" ".join(left))


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
