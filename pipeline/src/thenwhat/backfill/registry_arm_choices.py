"""Use explicit protocol arm wording to distinguish regimens from alternatives."""

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass

from thenwhat.claims.entry import name_key

_PAREN_CHOICE = re.compile(r"(?:fluoropyrimidine )?\(([^()]+) or ([^()]+)\)")
_OPTIONAL = re.compile(r"\bwith or without\s+")
_SWITCH = re.compile(
    r"\b(?:may be used as an alternative|switch(?:es|ed)? to|"
    r"investigator-selected chemotherapy)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DescribedChoice:
    description: str
    variants: tuple[tuple[str, ...], ...] = ()


def _unambiguous_names(names: Mapping[str, Collection[str]]) -> dict[str, str]:
    owners: dict[str, set[str]] = {}
    for component, aliases in names.items():
        for alias in (component, *(part for name in aliases for part in name.split(","))):
            if label := name_key(alias):
                owners.setdefault(label, set()).add(component)
    return {label: next(iter(keys)) for label, keys in owners.items() if len(keys) == 1}


def _complete_variants(
    expression: str, names: Mapping[str, str], members: Collection[str]
) -> tuple[tuple[str, ...], ...]:
    fixed = []
    alternatives = None
    for term in expression.split(" + "):
        choice = _PAREN_CHOICE.fullmatch(term)
        if choice is None:
            if term not in names:
                return ()
            fixed.append(names[term])
            continue
        if alternatives is not None or any(part not in names for part in choice.groups()):
            return ()
        alternatives = tuple(names[part] for part in choice.groups())
    if alternatives is None:
        return ()
    named = [*fixed, *alternatives]
    if len(set(named)) != len(named) or set(named) != set(members):
        return ()
    return tuple(tuple(sorted((*fixed, alternative))) for alternative in alternatives)


def described_choice(
    description: str,
    names: Mapping[str, Collection[str]],
    *,
    may_separate: bool,
) -> DescribedChoice | None:
    """Separate a complete literal assignment or identify an unresolved alternative."""
    text = name_key(description).strip(" .")
    switches = _SWITCH.search(description)
    if len(names) < 2 or (" or " not in text and switches is None):
        return None
    labels = _unambiguous_names(names)
    if may_separate and (variants := _complete_variants(text, labels, names.keys())):
        return DescribedChoice(description, variants)
    if switches is not None:
        return DescribedChoice(description)
    for match in _OPTIONAL.finditer(text):
        if any(re.match(rf"{re.escape(label)}(?!\w)", text[match.end() :]) for label in labels):
            return DescribedChoice(description)
    for match in re.finditer(r"\bor\b", text):
        left = text[: match.start()].rstrip()
        right = text[match.end() :].lstrip()
        before = {
            owner
            for label, owner in labels.items()
            if re.search(rf"(?<!\w){re.escape(label)}$", left)
        }
        after = {
            owner
            for label, owner in labels.items()
            if re.match(rf"{re.escape(label)}(?!\w)", right)
        }
        if before and after and before.isdisjoint(after):
            return DescribedChoice(description)
    return None
