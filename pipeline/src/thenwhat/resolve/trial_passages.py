"""Select publisher evidence about a result from a particular registered trial."""

import re
from dataclasses import dataclass

from thenwhat.backfill.trial_terms import words_of

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])|\n+")
_PARAGRAPH = re.compile(r"\n[ \t]*\n")
_CLAUSE = re.compile(r";\s*|,\s*(?:and|but|while)\s+|\s+(?:but|while)\s+", re.IGNORECASE)
_RESULT = re.compile(
    r"\b(?:achieved|demonstrated|observed|showed|found|"
    r"met (?:the|its|all) [\w -]{1,48}(?:endpoints?|goal)|"
    r"interim analysis|post hoc analysis|biomarker results|"
    r"(?:reported|presented)(?: [\w-]+){0,5} (?:results|findings)|"
    r"results (?:showed|were reported|were presented)|"
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) "
    r"(?:(?:complete|partial|sustained) )?remissions?)\b",
    re.IGNORECASE,
)
_FUTURE = re.compile(
    r"\b(?:will (?:be )?(?:reported|presented|published|released|report|present|publish|release)|"
    r"results (?:are )?(?:expected|pending))\b",
    re.IGNORECASE,
)
_TRIAL = re.compile(r"\b(?:trial|study|protocol|extension)\b", re.IGNORECASE)
_STUDY_WORDS = ("trial", "study", "protocol", "extension", "cohort")
_DESIGN = re.compile(
    r"\b(?:open[- ]label|OLE\b|mid[- ]stage|placebo[- ]controlled|randomi[sz]ed|phase\s+[1234ivx])",
    re.IGNORECASE,
)
_SHORT_CODE = re.compile(r"\b([A-Z]{2,8})\s*['‘’]\s*([0-9]{3,6})\b")
_FULL_CODE = re.compile(r"([A-Z]{2,8})[- ]?([0-9]{4,8})", re.IGNORECASE)
_OTHER_ID = re.compile(r"\bNCT[0-9]{8}\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TrialPassage:
    text: str
    possible_code: str | None = None
    names_protocol: bool = False


def _key(text: str) -> str:
    return " ".join(words_of(text))


def _contains(normalized: str, term: str) -> bool:
    return bool(term) and f" {term} " in f" {normalized} "


def _observed(sentence: str) -> bool:
    return any(
        _RESULT.search(clause) and not _FUTURE.search(clause) for clause in _CLAUSE.split(sentence)
    )


def _named_protocols(text: str, names: set[str]) -> set[str]:
    matched = {name for name in names if _contains(text, name)}
    explicit = {
        name
        for name in matched
        if any(
            _contains(text, f"{name} {word}") or _contains(text, f"{word} {name}")
            for word in _STUDY_WORDS
        )
    }
    matched = explicit or matched
    return {
        name for name in matched if not any(_contains(other, name) for other in matched - {name})
    }


def _excerpt_window(text: str, anchors: re.Pattern[str]) -> str:
    if len(text) <= 640:
        return text
    positions = [match.start() for match in anchors.finditer(text)]
    results = [match.start() for match in _RESULT.finditer(text)]
    if not positions:
        return text[:640]
    # Some publishers return headings, menus and the opening paragraph as one long line.
    # Keep the study mention closest to a finding, with room for the words on either side.
    chosen = (
        min(positions, key=lambda position: min(abs(r - position) for r in results))
        if results
        else positions[0]
    )
    start = max(0, chosen - 260)
    return text[start : start + 640]


def _shortened_code(text: str, products: tuple[str, ...]) -> str | None:
    registry_codes = [match for name in products if (match := _FULL_CODE.fullmatch(name))]
    for label in _SHORT_CODE.finditer(text):
        prefix, digits = label.groups()
        for match in registry_codes:
            registered_prefix, registered_digits = match.groups()
            if (
                prefix == registered_prefix.upper()
                and len(digits) < len(registered_digits)
                and registered_digits.endswith(digits)
            ):
                return f"{label[0]} is consistent with a shortened {match[0]}"
    return None


def reported_context(article: str) -> str:
    """Keep findings and trial setup together for comparisons across cohorts."""
    parts = []
    for sentence in _SENTENCE.split(article):
        if _observed(sentence) or (_TRIAL.search(sentence) and _DESIGN.search(sentence)):
            parts.append(" ".join(sentence.split())[:640])
    return "\n".join(dict.fromkeys(parts))[:3600]


def reported_passage(
    article: str,
    identifier: str,
    *,
    labels: tuple[str, ...],
    products: tuple[str, ...],
    other_labels: tuple[str, ...] = (),
) -> TrialPassage | None:
    """Prefer reported findings tied to this registry ID, study name or regimen."""
    names = {key for name in labels if len(key := _key(name)) >= 5}
    others = {key for name in other_labels if len(key := _key(name)) >= 5} - names
    product_names = tuple(key for name in products if len(key := _key(name)) >= 5)
    phrases = [
        r"[^a-z0-9]+".join(key.split())
        for key in sorted({*names, _key(identifier), *product_names})
    ]
    anchors = re.compile(r"(?<![a-z0-9])(?:" + "|".join(phrases) + r")(?![a-z0-9])", re.IGNORECASE)
    options: list[tuple[tuple[int, int], TrialPassage]] = []
    for paragraph in _PARAGRAPH.split(article):
        sentences = [
            _excerpt_window(sentence, anchors)
            for part in _SENTENCE.split(paragraph)
            if (sentence := part.strip())
        ]
        for index, sentence in enumerate(sentences):
            key = _key(sentence)
            cited = {match.upper() for match in _OTHER_ID.findall(sentence)}
            named = _named_protocols(key, names | others)
            if cited - {identifier} or named & others:
                continue
            possible_code = _shortened_code(sentence, products)
            if identifier in cited:
                strength = 4
            elif named:
                strength = 3
            elif possible_code is not None:
                strength = 2
            elif any(_contains(key, name) for name in product_names):
                strength = 1
            else:
                continue

            observed = _observed(sentence)
            text = sentence[:640]
            if not observed:
                if index + 1 == len(sentences) or _FUTURE.search(sentence):
                    continue
                follow_up = sentences[index + 1]
                follow_ids = {match.upper() for match in _OTHER_ID.findall(follow_up)}
                follow_names = _named_protocols(_key(follow_up), names | others)
                if follow_ids - {identifier} or follow_names & others:
                    continue
                text = f"{sentence} {follow_up}"[:640]
            if _observed(text):
                options.append(
                    (
                        (int(observed), strength),
                        TrialPassage(
                            text=text, possible_code=possible_code, names_protocol=strength >= 3
                        ),
                    )
                )
    return max(options, key=lambda item: item[0])[1] if options else None
