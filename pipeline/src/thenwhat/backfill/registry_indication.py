"""Indication wording supported by the labels and titles of a registry record."""

import re
from collections.abc import Iterable

from thenwhat.claims.entry import condition_words, tidy

# Complete clinical qualifiers, in compared (casefolded, hyphen-free) form. Each is one
# unit; units may stack directly before the registered condition ("moderate severe
# chronic plaque psoriasis"). Only verbatim title wording is ever kept.
_STATUS = (
    r"newly diagnosed|previously (?:un)?treated|untreated|treatment naive|"
    r"relapsing(?: remitting)?|(?:primary |secondary )?progressive|recurrent|"
    r"relapsed(?:(?: or)? refractory)?|refractory"
)
_EXTENT = (
    r"(?:locally |regionally )?advanced|metastatic|(?:un)?resectable|(?:in)?operable|"
    r"(?:early|late|extensive|limited) stage|localized"
)
_STAGE_NUMBER = r"(?:[0-4]|i{1,3}|iv)[a-c]?"
_STAGE = rf"stage {_STAGE_NUMBER}(?: (?:(?:and|or|to) )?(?:stage )?{_STAGE_NUMBER})?"
_UNIT = re.compile(
    rf"(?:{_STATUS})"
    rf"|(?:{_EXTENT})(?: (?:or|and) (?:{_EXTENT}|recurrent))?"
    rf"|recurrent (?:or|and) (?:{_EXTENT})"
    rf"|{_STAGE}"
    r"|(?:mild|moderate|moderately)(?: (?:to |or )?(?:moderate|severe|severely))?|severe|severely"
    r"|active|chronic|acute|(?:high|intermediate|low) risk"
    r"|(?:non )?small cell|(?:non )?squamous(?: cell)?"
    r"|plaque|pustular|guttate|erythrodermic|palmoplantar"
    r"|(?P<genotype>[a-z0-9]+(?: [a-z0-9]+)?)"
    r"(?: (?:mutation )?(?:positive|negative)| (?:mutant|mutated))"
)
_LONGEST_UNIT = 6
# A gene or marker as written in the title, e.g. SCN1A, HER2, PD-L1.
_MARKER = re.compile(r"[A-Z0-9]*[A-Z][A-Z0-9]*")
_MARKER_TAIL = re.compile(
    r"^\s+(?i:harbou?ring|carrying|with)\s+(?:(?i:the|a|an)\s+)?"
    r"[A-Z][A-Z0-9-]{1,11}(?:\s+[A-Z]\d+[A-Z])?\s+(?i:mutations?|variants?)\b"
)
_MARKER_CONTINUATION = re.compile(r"^\s*(?:[,;]\s*)?(?:and\b|or\b|[/&+])", re.IGNORECASE)
# Enrollment wording kept with the condition: "previously treated patients with ...".
_ENROLMENT = re.compile(
    r"(?:previously (?:un)?treated|untreated|treatment naive|newly diagnosed) "
    r"(?:(?:adult|pediatric|paediatric) )?"
    r"(?:patients|participants|subjects|adults|children|people|individuals) with"
)
_JOIN = re.compile(r"[\s\-‐‑–/]*")
_NEGATION = {"non", "no", "not", "without"}
_COORDINATION = {"and", "or", "versus", "vs"}
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


def _narrows(short: tuple[str, ...], long: tuple[str, ...]) -> bool:
    """`long` is `short` with more wording; a negated occurrence does not count
    ("non small cell" does not narrow "small cell")."""
    return any(
        long[start : start + len(short)] == short
        and not (start > 0 and long[start - 1] in _NEGATION)
        for start in range(len(long) - len(short) + 1)
    )


def _qualifier_start(title: str, tokens: list[re.Match], words: list[str], start: int) -> int:
    """Index of the first word of the qualifiers written directly before `start`."""

    def joined(first: int, last: int) -> bool:
        return all(
            _JOIN.fullmatch(title[tokens[index - 1].end() : tokens[index].start()])
            for index in range(first + 1, last + 1)
        )

    while start > 0:
        for size in range(min(_LONGEST_UNIT, start), 0, -1):
            first = start - size
            unit = _UNIT.fullmatch(" ".join(words[first:start]))
            if unit is None or not joined(first, start):
                continue
            if unit.group("genotype") is not None:
                markers = tokens[first : first + len(unit.group("genotype").split())]
                if not all(
                    len(marker.group()) > 1 and _MARKER.fullmatch(marker.group())
                    for marker in markers
                ):
                    continue
            start = first
            break
        else:
            break
    for size in range(min(_LONGEST_UNIT, start), 2, -1):
        first = start - size
        if _ENROLMENT.fullmatch(" ".join(words[first:start])) and joined(first, start):
            return first
    return start


def resolve_indication(
    labels: tuple[str, ...], titles: Iterable[str]
) -> tuple[tuple[str, ...], str | None]:
    """Keep the exact label unless a title can establish a more specific indication.

    Multiple listed labels can be narrowed when a single title phrase covers them all.
    Distinct or conflicting labels remain visible for review, as do qualifiers that are
    one of several coordinated alternatives and titles that name a condition both with
    and without a qualifier.
    """
    if not labels:
        return labels, None
    words = {label: tuple(condition_words(_ACRONYM.sub("", label))) for label in labels}
    title_phrases: dict[tuple[str, ...], str] = {}
    named_targets: dict[tuple[str, ...], str] = {}
    target_list = False
    unresolved = False
    for title in titles:
        tokens = list(_WORD.finditer(title))
        folded = [token.group().casefold() for token in tokens]
        normalized = " ".join(folded)
        offsets = []
        position = 0
        for word in folded:
            offsets.append(position)
            position += len(word) + 1
        spans: list[tuple[int, int, tuple[str, ...], bool]] = []
        for key in words.values():
            if not key:
                continue
            for end in range(len(key), len(folded) + 1):
                if tuple(folded[end - len(key) : end]) != key:
                    continue
                first = _qualifier_start(title, tokens, folded, end - len(key))
                last = end - 1
                if first > 0 and folded[first - 1] in _NEGATION:
                    continue
                whole = tuple(folded[first:end])
                preceding = normalized[: offsets[first]]
                if whole != key and first > 0:
                    coordinated = folded[first - 1] in _COORDINATION
                    complete_pair = coordinated and any(
                        earlier_end == first - 1 and earlier_key == key
                        for _, earlier_end, earlier_key, _ in spans
                    )
                    punctuation = title[tokens[first - 1].end() : tokens[first].start()].strip()
                    if _MIXED_ENROLMENT.search(preceding) or (
                        not complete_pair and (coordinated or punctuation in {"/", ",", "&", "+"})
                    ):
                        # A fragment such as "or small cell lung cancer" alone
                        # cannot narrow the label.
                        continue
                after = title[tokens[last].end() :]
                label = tidy(title[tokens[first].start() : tokens[last].end()])
                marker = _MARKER_TAIL.match(after)
                if marker is not None and not _MARKER_CONTINUATION.match(after[marker.end() :]):
                    label = tidy(label + marker.group())
                    whole = tuple(condition_words(label))
                spans.append((first, end, key, whole != key))
                title_phrases.setdefault(whole, label)
                if not _TARGET.search(preceding):
                    continue
                following = normalized[offsets[last] + len(folded[last]) :]
                if _TARGET_LIST.match(following) or after.lstrip().startswith((",", "/", ";")):
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
        # A title naming the same condition with and without a qualifier disagrees
        # with itself, e.g. "Prior study enrolled advanced melanoma. This study ...
        # melanoma".
        for first, end, key, qualified in spans:
            if qualified:
                continue
            if any(
                (other_first, other_end) != (first, end)
                and other_first <= first
                and end <= other_end
                for other_first, other_end, _, _ in spans
            ):
                continue
            if any(
                other_key == key and other_qualified for _, _, other_key, other_qualified in spans
            ):
                unresolved = True

    if unresolved:
        return labels, None

    targets = [
        (key, phrase)
        for key, phrase in named_targets.items()
        if not any(key != other and _narrows(key, other) for other in named_targets)
    ]
    if len(labels) > 1 and len(targets) == 1 and not target_list:
        target, phrase = targets[0]
        # Keep a more specific phrase if a second title distinguishes it.
        if not any(target != other and _narrows(target, other) for other in title_phrases):
            return (phrase,), phrase

    # If an explicit narrow and broad label both occur, keep the narrow one. If two
    # incompatible descendants occur, assigning one arbitrarily would change the scope.
    strongest = [
        (key, label)
        for key, label in title_phrases.items()
        if all(_narrows(listed, key) for listed in words.values())
        and not any(key != other and _narrows(key, other) for other in title_phrases)
    ]
    if len(strongest) != 1:
        if len(labels) == 1:
            distinct = [
                label
                for key, label in title_phrases.items()
                if key not in words.values()
                and not any(key != other and _narrows(key, other) for other in title_phrases)
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
