"""Telling a name from a description.

A news article calls a treatment "the drug" or "a one-time gene-editing treatment" as
often as it names it. Recorded as another name, a description is sent to the registries
as a search term and brings back thousands of unrelated trials.
"""

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
