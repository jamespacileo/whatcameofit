"""Topics the operator wants covered first: a name, and the words that mark a link lead's
title or a claim's intervention as belonging to it. A checked-in list, applied by rule; no
model decides it. Behavior: openspec lead-reading, "Topic leads".

A topic changes two things and nothing else: a lead whose title names one of its words is
read before the others, and is read when triage held it, not only when triage passed it.
It is never a status and never reaches the export. Add a topic here when the operator
names one; `thenwhat backfill topics` shows how far each is covered.
"""

import re
from collections.abc import Sequence

from sqlalchemy import ColumnElement

from thenwhat.backfill.errors import BackfillError
from thenwhat.db.models import LinkLead

TOPICS: dict[str, tuple[str, ...]] = {
    # GLP-1 receptor agonists and the drugs reported beside them, by generic and brand
    # name. Named by the operator on 2026-11-15 as the first topic to cover in full.
    "glp-1": (
        "GLP-1",
        "GLP1",
        "semaglutide",
        "Ozempic",
        "Wegovy",
        "Rybelsus",
        "tirzepatide",
        "Mounjaro",
        "Zepbound",
        "liraglutide",
        "Saxenda",
        "Victoza",
        "dulaglutide",
        "Trulicity",
        "exenatide",
        "Byetta",
        "Bydureon",
        "retatrutide",
        "orforglipron",
        "cagrilintide",
        "CagriSema",
        "survodutide",
        "mazdutide",
    ),
}


class UnknownTopic(BackfillError):
    """No topic has the name given."""


def terms_of(topic: str | None = None) -> tuple[str, ...]:
    """The words of one topic, or of every topic when none is named."""
    if topic is None:
        return tuple(term for terms in TOPICS.values() for term in terms)
    if topic not in TOPICS:
        raise UnknownTopic(f"No topic is named '{topic}'. The topics are: {', '.join(TOPICS)}.")
    return TOPICS[topic]


def _alternatives(terms: Sequence[str]) -> str:
    return "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True))


def title_names(terms: Sequence[str]) -> ColumnElement[bool] | None:
    """The query condition for a lead whose title names one of the words, as a whole
    word and whatever its letter case. None when there are no words."""
    if not terms:
        return None
    return LinkLead.title.op("~*")(rf"\m(?:{_alternatives(terms)})\M")


def names_one(text: str, terms: Sequence[str]) -> bool:
    """Whether the text names one of the words, by the same rule as `title_names`."""
    if not terms:
        return False
    return re.search(rf"(?<!\w)(?:{_alternatives(terms)})(?!\w)", text, re.IGNORECASE) is not None
