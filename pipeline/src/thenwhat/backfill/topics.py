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

from thenwhat.db.models import LinkLead
from thenwhat.extract.names import is_a_name
from thenwhat.work.errors import BackfillError

# Each topic's words, grouped by drug: every word of one group is the same treatment under
# another name. A group of one word, or a word that is no drug's name, stands alone.
TOPIC_DRUGS: dict[str, tuple[tuple[str, ...], ...]] = {
    # GLP-1 receptor agonists and the drugs reported beside them, by generic and brand
    # name. Named by the operator on 2026-11-15 as the first topic to cover in full.
    "glp-1": (
        ("GLP-1",),
        ("GLP1",),
        ("glucagon-like peptide",),
        ("semaglutide", "Ozempic", "Wegovy", "Rybelsus"),
        ("tirzepatide", "Mounjaro", "Zepbound"),
        ("liraglutide", "Saxenda", "Victoza"),
        ("dulaglutide", "Trulicity"),
        ("exenatide", "Byetta", "Bydureon"),
        ("lixisenatide", "Adlyxin", "Lyxumia"),
        ("albiglutide", "Tanzeum"),
        ("Soliqua",),
        ("Xultophy",),
        ("retatrutide",),
        ("orforglipron",),
        ("cagrilintide",),
        ("CagriSema",),
        ("survodutide",),
        ("mazdutide",),
    ),
}
# The words of a topic that name its class of treatments, not any one of them. A
# treatment named by one of these and by no drug of the topic is the class.
TOPIC_CLASS_WORDS: dict[str, tuple[str, ...]] = {
    "glp-1": ("GLP-1", "GLP1", "glucagon-like peptide"),
}
TOPICS: dict[str, tuple[str, ...]] = {
    topic: tuple(word for drug in drugs for word in drug) for topic, drugs in TOPIC_DRUGS.items()
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


def other_names_of(names: Sequence[str]) -> tuple[str, ...]:
    """The other names a topic lists for the drugs these names name: Ozempic, Wegovy and
    Rybelsus for semaglutide. An article that calls a drug by its brand reports the claim
    entered under its generic name, and the two share no word, so the list is what ties
    them. Empty when the names name no listed drug."""
    found: list[str] = []
    for drugs in TOPIC_DRUGS.values():
        for drug in drugs:
            if len(drug) > 1 and any(names_one(name, drug) for name in names):
                found += [word for word in drug if word not in found]
    return tuple(found)


def names_only_a_class(names: Sequence[str]) -> bool:
    """Whether a name is a topic's class of treatments and nothing more: it holds one of
    the topic's class words, none of its drugs, and what is left of it is no name.
    "GLP-1 metabolic therapy" and "GLP-1" are the class. "Semaglutide" is not, nor is a
    treatment that is described by what it does to GLP-1. The checked-in lists and the
    name rule decide it."""
    for topic, class_words in TOPIC_CLASS_WORDS.items():
        drugs = [word for word in TOPICS[topic] if word not in class_words]
        if any(names_one(name, drugs) for name in names):
            continue
        for name in names:
            if not names_one(name, class_words):
                continue
            rest = re.sub(
                rf"(?<!\w)(?:{_alternatives(class_words)})(?!\w)", " ", name, flags=re.IGNORECASE
            )
            if not is_a_name(" ".join(rest.split())):
                return True
    return False
