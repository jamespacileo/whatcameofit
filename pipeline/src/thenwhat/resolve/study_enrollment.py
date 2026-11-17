"""Read an explicit study-wide participant count from article evidence."""

import re
from collections.abc import Iterable

_NUMBER = r"(?:[1-9][0-9]{0,2}(?:,[0-9]{3})+|[1-9][0-9]{0,5})"
_TOTAL = re.compile(
    r"\b(?:each of the|all of the|a total of|trial (?:enrolled|randomized|included))\s+"
    rf"(?:(?:about|around|approximately)\s+)?({_NUMBER})\s+"
    r"(?:human )?(?:participants|patients|volunteers|people|adults)\b",
    re.IGNORECASE,
)
_SUBSET = re.compile(
    r"\b(?:in (?:this|one|each|the) arm|for this subgroup|in this cohort|per arm|"
    r"subgroup of the trial|subset of the trial)\b",
    re.IGNORECASE,
)


def reported_total(excerpts: Iterable[str]) -> int | None:
    """Use a single, explicit article-wide size cue, leaving conflicting totals pending."""
    totals: set[int] = set()
    for excerpt in excerpts:
        text = " ".join(excerpt.split())
        for match in _TOTAL.finditer(text):
            near = text[max(0, match.start() - 48) : match.end() + 44]
            if not _SUBSET.search(near):
                totals.add(int(match[1].replace(",", "")))
    return next(iter(totals)) if len(totals) == 1 else None


def agrees_with_total(reported: int, registered: int) -> bool:
    """Allow ordinary rounding, while distinguishing a small prior study from a larger one."""
    return registered > 0 and abs(reported - registered) * 10 <= reported
