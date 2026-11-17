"""What a registry trial is searched by: the intervention under test as a name alone,
and the indication's telling words. By rule only; no model.

A registry lists interventions as their sponsor typed them: with doses, forms and
routes, alongside placebos and comparators, and sometimes as a description that is not
a name. A trial with no usable name is searched by nothing. Behavior: openspec
article-leads, "Intervention name used for the search".
"""

import re
from typing import Any

from thenwhat.sources.clinicaltrials import GENERIC_CONDITION_WORDS

# Kinds of intervention that have a name a news article would use.
NAMED_KINDS = frozenset(
    ["DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT", "DIETARY_SUPPLEMENT"]
)
# An entry that is the trial's control, not what it tests.
NOT_UNDER_TEST = re.compile(
    r"placebo|saline|standard|usual care|supportive care|\bcontrol\b|\bsham\b|vehicle|"
    r"no treatment|no intervention|observation|comparator|conventional|routine|\bdummy\b",
    re.IGNORECASE,
)
BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
# A dose, with or without a rate: "20 mg", "2,5%", "10 mg/kg", "80mg//40 mg".
DOSE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|ug|g|kg|ml|l|iu|u|units?|mmol|mm|meq|%)"
    r"(?:\s*/+\s*[\w.]+)*(?![\w-])",
    re.IGNORECASE,
)
# Forms, routes and other words that say how a product is given, not what it is.
HOW_GIVEN = re.compile(
    r"\b(?:iv|sc|im|po|bid|tid|qd|oral|orally|tablets?|capsules?|injections?|infusions?|"
    r"intravenous|subcutaneous|intramuscular|intranasal|nasal|topical|sublingual|inhaled|"
    r"solution|suspension|cream|gel|spray|patch|granules|decoction|powder|drops|"
    r"dose|doses|dosing|low|high|arm|group|cohort|drug|treatment|therapy|regimen|"
    r"once|twice|daily|weekly|monthly|extended|release|generic|branded|"
    r"single|double|active|experimental|investigational|study|open|label|"
    r"tab|tabs|cycles?|ophthalmic|inhalation)\b",
    re.IGNORECASE,
)
# What joins two products in one entry. The first is taken.
JOINS = re.compile(
    r"[,;/+&]|\b(?:and|plus|or|with|combined with|followed by|versus|vs)\b", re.IGNORECASE
)
# A word that is a kind of product, not a product.
KINDS_OF_PRODUCT = frozenset(
    [
        "vaccine",
        "vaccines",
        "chemotherapy",
        "antibiotic",
        "antibiotics",
        "steroid",
        "steroids",
        "corticosteroid",
        "corticosteroids",
        "anesthesia",
        "anaesthesia",
        "anesthetic",
        "analgesia",
        "analgesic",
        "formula",
        "arterial",
        "catheter",
        "phage",
        "mixture",
        "eutectic",
        "product",
        "medication",
        "medicine",
        "agent",
        "inhibitor",
        "antibody",
        "immunotherapy",
        "radiotherapy",
        "surgery",
    ]
)
# A word that shows the entry describes a procedure or a schedule.
DESCRIBES = frozenset(
    ["before", "after", "during", "in", "for", "of", "to", "then", "infiltration", "finding"]
)
MAX_NAME_WORDS = 3
MIN_NAME_LENGTH = 4
MORE_GENERIC_CONDITION_WORDS = frozenset(
    [
        "relapsed",
        "relapsing",
        "refractory",
        "metastatic",
        "recurrent",
        "primary",
        "secondary",
        "healthy",
        "volunteers",
        "volunteer",
        "multiple",
        "related",
        "induced",
        "associated",
        "non",
        "cell",
        "cells",
        "locally",
        "extensive",
        "generalized",
        "congenital",
        "major",
        "without",
        "positive",
        "negative",
        "mellitus",
        "carcinoma",
        "neoplasm",
        "neoplasms",
        "infection",
        "infections",
        "vaccine",
        "surgery",
    ]
)
MAX_INDICATION_WORDS = 3


def name_under_test(interventions: list[dict[str, Any]]) -> str | None:
    """The first intervention that reads as the name of what the trial tests, without
    dose, form or route. None when every entry is a control or a description."""
    for intervention in interventions:
        if intervention.get("type") not in NAMED_KINDS:
            continue
        written = intervention.get("name") or ""
        if NOT_UNDER_TEST.search(written):
            continue
        for candidate in (written, *(intervention.get("otherNames") or [])):
            name = _name_alone(candidate)
            if name is not None:
                return name
    return None


def name_alone(written: str) -> str | None:
    """One registry entry as a name alone, without dose, form or route, or None when it
    is a control or a description."""
    return _name_alone(written)


def _name_alone(written: str) -> str | None:
    if NOT_UNDER_TEST.search(written):
        return None
    text = BRACKETS.sub(" ", written)
    text = DOSE.sub(" ", text)
    text = JOINS.split(text, maxsplit=1)[0]
    text = HOW_GIVEN.sub(" ", text)
    text = re.sub(r"[^\w\- ]", " ", text)
    words = [word for word in text.split() if re.search(r"[A-Za-z]", word)]
    if not words or len(words) > MAX_NAME_WORDS:
        return None
    lowered = [word.lower() for word in words]
    if any(word in DESCRIBES for word in lowered):
        return None
    if all(word in KINDS_OF_PRODUCT or word.startswith("anti-") for word in lowered):
        return None
    name = " ".join(words)
    if len(name) < MIN_NAME_LENGTH or not re.search(r"[A-Za-z]{2}", name):
        return None
    return name


def indication_words(conditions: list[str]) -> str | None:
    """The telling words of the first condition that has any, in the registry's order.
    None when the conditions are only general words."""
    for condition in conditions:
        words = [
            word
            for word in re.findall(r"[a-z][a-z-]+", condition.lower().replace("'s", ""))
            if len(word) >= 4
            and word not in GENERIC_CONDITION_WORDS
            and word not in MORE_GENERIC_CONDITION_WORDS
        ]
        unique = list(dict.fromkeys(words))
        if unique:
            return " ".join(unique[:MAX_INDICATION_WORDS])
    return None
