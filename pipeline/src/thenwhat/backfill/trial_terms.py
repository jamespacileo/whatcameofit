"""The terms of a stored trial that a headline could hold, beyond its intervention's
name: its registry number, its acronym, the development codes among its interventions'
names and other names, and those other names. By rule from the stored record; no model
and no request. Behavior: openspec trial-report-links and trial-coverage.

A term names a treatment or a study, never one registry record: many trials carry one
code. So a link made on a term is a reason to read a lead, and says nothing of which
trial a report is about.
"""

import re
from collections.abc import Iterable
from typing import Any

from thenwhat.backfill.trial_names import MORE_GENERIC_CONDITION_WORDS, _name_alone
from thenwhat.sources.clinicaltrials import GENERIC_CONDITION_WORDS

WORD = re.compile(r"[a-z0-9]+")
REGISTRY_NUMBER = re.compile(r"nct\d{8}", re.IGNORECASE)

# A development code as sponsors write one: two to six letters, an optional hyphen, at
# least three digits, and at most a short tail ("TARA-002", "MEDI4736", "BNT162b2",
# "mRNA-1273"). Two digits are too few: "COVID-19", "IL-17" and "PD-1" are not codes.
CODE = re.compile(r"(?<![A-Za-z0-9-])([A-Za-z]{2,6})-?(\d{3,})([A-Za-z]\d{0,2})?(?![A-Za-z0-9])")
# Letters that open something shaped like a code and are not one: an antigen, a virus,
# a registry's number, a measure, a year.
NOT_A_CODE = frozenset(
    ["cd", "nct", "isrctn", "covid", "sars", "hiv", "hpv", "hsv", "pm", "omega", "day", "week"]
)
ACRONYM_MIN_LETTERS = 5
ACRONYM_MAX_WORDS = 3
OTHER_NAME_MIN_LETTERS = 5
# Words a registry record gives as an intervention's other name that name no product.
NOT_A_PRODUCT = frozenset(
    ["patients", "patient", "people", "children", "adults", "healthy", "early", "blood"]
)


def words_of(text: str) -> tuple[str, ...]:
    """A text as whole words in lower case, the form terms and titles are compared in."""
    return tuple(WORD.findall(text.lower()))


def codes_in(written: str) -> list[str]:
    """The development codes in one name as the registry gives it, as written."""
    return [
        match.group(0)
        for match in CODE.finditer(written)
        if match.group(1).lower() not in NOT_A_CODE
    ]


def codes_of(interventions: Iterable[dict[str, Any]]) -> list[str]:
    """The development codes among a trial's intervention names and other names, each
    once, whatever its letter case or hyphen."""
    found: dict[str, str] = {}
    for intervention in interventions:
        for written in (intervention.get("name"), *(intervention.get("otherNames") or [])):
            for code in codes_in(str(written or "")):
                found.setdefault(code_key(code), code)
    return list(found.values())


def code_key(code: str) -> str:
    """A code with no hyphen and in lower case: "TARA-002" and "tara002" are one."""
    return "".join(words_of(code))


def code_forms(code: str) -> set[tuple[str, ...]]:
    """The ways a headline writes a code, as words: with its hyphen, and without."""
    return {words_of(code), (code_key(code),)} - {()}


# Kinds of intervention whose other names are a product's: a brand, a second drug.
PRODUCT_KINDS = frozenset(["DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"])


def other_names_of(interventions: Iterable[dict[str, Any]], search_name: str | None) -> list[str]:
    """The names of a trial's drug and biological interventions that read as a name
    alone and are neither the name the trial is searched by nor a development code: a
    brand, a second drug. A behaviour, a device or a procedure has no such name."""
    known = {words_of(search_name or "")}
    names: dict[tuple[str, ...], str] = {}
    for intervention in interventions:
        if intervention.get("type") not in PRODUCT_KINDS:
            continue
        for written in (intervention.get("name"), *(intervention.get("otherNames") or [])):
            name = _name_alone(str(written or ""))
            if name is None or codes_in(name):
                continue
            key = words_of(name)
            if (
                key
                and key not in known
                and sum(map(len, key)) >= OTHER_NAME_MIN_LETTERS
                and not is_general(key)
            ):
                names.setdefault(key, name)
    return list(names.values())


def is_general(words: Iterable[str]) -> bool:
    """Whether a name holds a word that is general in health news ("cancer", "disease",
    "patients"): such a name tells one treatment from another nowhere."""
    return any(
        word in GENERIC_CONDITION_WORDS
        or word in MORE_GENERIC_CONDITION_WORDS
        or word in NOT_A_PRODUCT
        for word in words
    )


def condition_words(conditions: Iterable[str]) -> frozenset[str]:
    """The telling words of every condition a trial lists: no general word ("disease",
    "chronic") and none shorter than four letters."""
    return frozenset(
        word
        for condition in conditions
        for word in words_of(condition.replace("'s", ""))
        if len(word) >= 4
        and not word.isdigit()
        and word not in GENERIC_CONDITION_WORDS
        and word not in MORE_GENERIC_CONDITION_WORDS
    )


def acronym_words(acronym: str | None) -> tuple[str, ...] | None:
    """An acronym as the words a headline would hold, when its shape lets it tell a
    study from an ordinary word: it carries a digit beside a word of at least five
    letters ("KEYNOTE-789"). None otherwise: an acronym with no digit is a word a
    headline could use for anything ("HOPE", "RECOVERY", "VOLGA"), and never links.
    Shape alone does not make an acronym fit: one that holds a word of a condition
    ("COVID-19") or that several trials share is left out when the terms are gathered."""
    words = words_of(acronym or "")
    if not words or len(words) > ACRONYM_MAX_WORDS:
        return None
    has_digit = any(character.isdigit() for word in words for character in word)
    has_word = any(word.isalpha() and len(word) >= ACRONYM_MIN_LETTERS for word in words)
    return words if has_digit and has_word else None
