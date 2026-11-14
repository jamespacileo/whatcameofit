"""Whether a registry record agrees with what an article says about the trial it reports.

A treatment often has dozens of trials. The article is about one of them, and gives it
away by its name, its size or who ran it. These are compared with the record by rule:
no model is asked, and each agreement can be shown to a reader as a plain fact.
"""

import re
from dataclasses import dataclass
from typing import Any

# The codes for why a record is ranked where it is.
STATED = "stated"  # the text or the page gives this record's registry number
PAPER = "paper"  # a paper the page links to gives it
TRIAL_NAME = "trial_name"
PARTICIPANTS = "participants"
SPONSOR = "sponsor"

# How far a reported number of participants may be from the registered one: articles
# round, and report the people analysed rather than the people enrolled.
PARTICIPANTS_WITHIN = 0.1
# Words that say what kind of body a sponsor is, not which one.
SPONSOR_FILLER = frozenset(
    ["of", "the", "and", "at", "inc", "ltd", "plc", "llc", "co", "company", "corporation", "corp"]
)


@dataclass(frozen=True, slots=True)
class Details:
    """What the text says about the trial itself. Each is None when the text does not say."""

    trial_name: str | None = None
    participants: int | None = None
    sponsor: str | None = None


def agreeing(payload: dict[str, Any], details: Details) -> list[str]:
    """The details this registry record agrees with, as codes."""
    section = payload.get("protocolSection") or {}
    identification = section.get("identificationModule") or {}
    reasons: list[str] = []

    name = _words(details.trial_name)
    if len("".join(name)) >= 3:
        carried = [
            _words(identification.get(part)) for part in ("acronym", "briefTitle", "officialTitle")
        ]
        if any(_within(name, words) for words in carried):
            reasons.append(TRIAL_NAME)

    enrolled = ((section.get("designModule") or {}).get("enrollmentInfo") or {}).get("count")
    reported = details.participants
    if (
        isinstance(enrolled, int)
        and reported
        and enrolled > 0
        and abs(enrolled - reported) <= PARTICIPANTS_WITHIN * max(enrolled, reported)
    ):
        reasons.append(PARTICIPANTS)

    sponsors = section.get("sponsorCollaboratorsModule") or {}
    registered = [
        (sponsors.get("leadSponsor") or {}).get("name"),
        *(one.get("name") for one in sponsors.get("collaborators") or []),
    ]
    wanted = {word for word in _words(details.sponsor) if word not in SPONSOR_FILLER}
    if wanted and any(wanted <= set(_words(one)) for one in registered):
        reasons.append(SPONSOR)
    return reasons


def _words(text: object) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).lower()) if text else []


def _within(wanted: list[str], words: list[str]) -> bool:
    """Whether the wanted words appear in order, next to each other."""
    return any(
        words[start : start + len(wanted)] == wanted
        for start in range(len(words) - len(wanted) + 1)
    )
