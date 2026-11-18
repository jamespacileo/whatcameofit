"""Indication wording supported by the labels and titles of a registry record."""

import re
from collections.abc import Iterable

from thenwhat.claims.entry import condition_words, tidy

# Only complete qualifiers that occur directly before the registered condition.
_QUALIFIER = (
    r"relapsing(?: remitting)?|progressive|recurrent|relapsed(?:(?: or)? refractory)?|"
    r"refractory|locally advanced|advanced|early stage|metastatic|"
    r"moderate to severe|high risk"
)
_ACRONYM = re.compile(r"\s*\(([A-Z][A-Z0-9-]{1,11})\)$")
_WORD = re.compile(r"[^\W_]+")
_TARGET = re.compile(
    r"\b(?:to (?:treat|prevent)|(?:treatment|prevention|management|reduction) of) $"
)
_TARGET_LIST = re.compile(r"^(?: and | or | as well as )")
_MIXED_ENROLMENT = re.compile(
    r"\b(?:untreated|treatment naive|previously treated|newly diagnosed) (?:and|or) $"
)
_PATIENT_CONTEXT = re.compile(
    r"^\s+(?:associated with|due to|among|in (?:patients|participants|people|subjects|adults) with)"
    r"\b[^,:;()]+",
    re.IGNORECASE,
)


def _within(short: tuple[str, ...], long: tuple[str, ...]) -> bool:
    return any(long[start : start + len(short)] == short for start in range(len(long)))


def resolve_indication(
    labels: tuple[str, ...], titles: Iterable[str]
) -> tuple[tuple[str, ...], str | None]:
    """Keep the exact label unless a title can establish a more specific indication.

    Multiple listed labels can be narrowed when a single title phrase covers them all.
    Distinct or conflicting labels remain visible for review.
    """
    if not labels:
        return labels, None
    words = {label: tuple(condition_words(_ACRONYM.sub("", label))) for label in labels}
    title_phrases: dict[tuple[str, ...], str] = {}
    named_targets: dict[tuple[str, ...], str] = {}
    target_list = False
    for title in titles:
        tokens = list(_WORD.finditer(title))
        normalized = " ".join(token.group().casefold() for token in tokens)
        for key in words.values():
            if not key:
                continue
            expression = r"\b(?:(?:" + _QUALIFIER + r") )?" + " ".join(map(re.escape, key)) + r"\b"
            for match in re.finditer(expression, normalized):
                first = normalized.count(" ", 0, match.start())
                if first > 0 and tokens[first - 1].group().casefold() in {
                    "non",
                    "no",
                    "not",
                    "without",
                }:
                    continue
                last = normalized.count(" ", 0, match.end())
                span = match.group().split()
                whole = tuple(span)
                preceding = normalized[: match.start()]
                if whole != key and _MIXED_ENROLMENT.search(preceding):
                    continue
                label = tidy(title[tokens[first].start() : tokens[last].end()])
                title_phrases.setdefault(whole, label)
                if not _TARGET.search(preceding):
                    continue
                after = title[tokens[last].end() :]
                if _TARGET_LIST.match(normalized[match.end() :]) or after.lstrip().startswith(
                    (",", "/", ";")
                ):
                    target_list = True
                    continue
                context = _PATIENT_CONTEXT.match(after)
                if context is not None:
                    context_words = tuple(condition_words(context.group()))
                    if len(context_words) <= 16 and any(
                        listed and listed != key and _within(listed, context_words)
                        for listed in words.values()
                    ):
                        label = tidy(
                            title[tokens[first].start() : tokens[last].end() + context.end()]
                        )
                        whole = tuple(condition_words(label))
                named_targets.setdefault(whole, label)

    targets = [
        (key, phrase)
        for key, phrase in named_targets.items()
        if not any(key != other and _within(key, other) for other in named_targets)
    ]
    if len(labels) > 1 and len(targets) == 1 and not target_list:
        target, phrase = targets[0]
        # Keep a more specific phrase if a second title distinguishes it.
        if not any(target != other and _within(target, other) for other in title_phrases):
            return (phrase,), phrase

    # If an explicit narrow and broad label both occur, keep the narrow one. If two
    # incompatible descendants occur, assigning one arbitrarily would change the scope.
    strongest = [
        (key, label)
        for key, label in title_phrases.items()
        if all(_within(listed, key) for listed in words.values())
        and not any(key != other and _within(key, other) for other in title_phrases)
    ]
    if len(strongest) != 1:
        if len(labels) == 1:
            distinct = [
                label
                for key, label in title_phrases.items()
                if key not in words.values()
                and not any(key != other and _within(key, other) for other in title_phrases)
            ]
            if len(distinct) > 1:
                return tuple(distinct), None
        return labels, None
    key, label = strongest[0]
    if len(labels) == 1 and key == next(iter(words.values())):
        return labels, None
    return (label,), label


def has_named_cohorts(conditions: tuple[str, ...], arm_labels: Iterable[str]) -> bool:
    """Each distinct condition is named in its own tested arm label."""
    cohorts = [(label, tuple(condition_words(label))) for label in arm_labels]
    assigned: set[int] = set()
    for condition in conditions:
        acronym = _ACRONYM.search(condition)
        phrase = tuple(condition_words(_ACRONYM.sub("", condition)))
        shorthand = (
            re.compile(rf"(?<!\w){re.escape(acronym.group(1))}(?!\w)")
            if acronym is not None
            else None
        )
        matching = {
            index
            for index, (label, words) in enumerate(cohorts)
            if (phrase and _within(phrase, words))
            or (shorthand is not None and shorthand.search(label))
        }
        if not matching or assigned & matching:
            return False
        assigned.update(matching)
    return True
