"""The rules that check a proposed record reading before it is stored.

Behavior: openspec record-readings ("A reading is checked by rule before it is stored").
Pure: no database, network or clock. No model is asked anything here.
"""

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from thenwhat.domain import FollowUpUnit, MeasureCode, ReadingField, ReadingKind

# The one field each kind of reading is read from.
FIELD_OF_KIND = {
    ReadingKind.FOLLOW_UP: ReadingField.TIME_FRAME,
    ReadingKind.MEASURE: ReadingField.MEASURE,
}
_KINDS = frozenset(kind.value for kind in ReadingKind)
_UNITS = frozenset(unit.value for unit in FollowUpUnit)
_CODES = frozenset(code.value for code in MeasureCode)


class Refusal(StrEnum):
    """Why a proposed reading is not stored."""

    NO_SUCH_OUTCOME = "no_such_outcome"
    UNKNOWN_KIND = "unknown_kind"
    WRONG_FIELD = "wrong_field"
    WORDS_NOT_IN_RECORD = "words_not_in_record"
    UNKNOWN_UNIT = "unknown_unit"
    UNKNOWN_CODE = "unknown_code"
    NUMBER_NOT_IN_WORDS = "number_not_in_words"
    LATER_EVENT_OFFSET = "later_event_offset"
    # A second reading of one kind for one outcome in the same answer. Found by the
    # step that stores readings, not by `refusal`, which sees one reading at a time.
    REPEATED = "repeated"


@dataclass(frozen=True, slots=True)
class Outcome:
    """A planned primary outcome as a trial's facts carry it: its title and time frame."""

    measure: str
    time_frame: str | None


@dataclass(frozen=True, slots=True)
class Proposed:
    """A reading as a model gave it, before any check. Kind, field, unit and code are
    still plain text: whether they are in the lists is one of the checks."""

    # The place of the outcome among the trial's planned primary outcomes, from 0.
    outcome: int
    kind: str
    field: str
    words: str
    number: int | None = None
    unit: str | None = None
    code: str | None = None


def refusal(reading: Proposed, outcomes: Sequence[Outcome]) -> Refusal | None:
    """Why the reading is refused, or None when it may be stored.

    Stored only when: the outcome is one of the trial's; the kind is in the list and
    reads its own field; the words are in that field, character for character; a
    follow-up's unit is in the list and its number is in the words as digits; a
    measure's code is in the list.
    """
    if not 0 <= reading.outcome < len(outcomes):
        return Refusal.NO_SUCH_OUTCOME
    if reading.kind not in _KINDS:
        return Refusal.UNKNOWN_KIND
    kind = ReadingKind(reading.kind)
    if reading.field != FIELD_OF_KIND[kind].value:
        return Refusal.WRONG_FIELD
    outcome = outcomes[reading.outcome]
    text = outcome.time_frame if kind is ReadingKind.FOLLOW_UP else outcome.measure
    if not reading.words.strip() or text is None or reading.words not in text:
        return Refusal.WORDS_NOT_IN_RECORD
    if kind is ReadingKind.MEASURE:
        return None if reading.code in _CODES else Refusal.UNKNOWN_CODE
    if reading.unit not in _UNITS:
        return Refusal.UNKNOWN_UNIT
    if reading.number is None or not number_in(reading.number, reading.words):
        return Refusal.NUMBER_NOT_IN_WORDS
    if later_event_offset(reading.number, reading.unit, text):
        return Refusal.LATER_EVENT_OFFSET
    return None


def later_event_offset(number: int, unit: str, time_frame: str) -> bool:
    """Recognize explicit offsets from a later treatment event, not study start.

    Check the whole field: a proposed quote can omit the anchor after its duration.
    This is a refusal boundary, not a general parser or a calculated follow-up.
    Surgery and the first dose may be the start; a completed cycle or later dose is not.
    """
    ordinal = r"(?:\d+(?:st|nd|rd|th)?|first|second|third|fourth|fifth|sixth|last|final)"
    later_ordinal = (
        r"(?:(?:[2-9]|\d{2,})(?:st|nd|rd|th)?|second|third|fourth|fifth|sixth|last|final)"
    )
    # Allow short modifiers such as "monthly diet" or "treatment", without
    # crossing another event noun or connecting phrase: "first dose of cycle 1"
    # is anchored to the first dose, not the completion of cycle 1.
    modifiers = (
        r"(?:(?!(?:dose|infusion|session|cycle|course|administration|of|and|or|after|before|"
        r"following|from|to|at|in|start|starting|beginning)\b)[a-z0-9][a-z0-9-]*\s+){0,3}"
    )
    event = (
        rf"(?:{ordinal}\s+{modifiers}(?:cycle|course)\b"
        rf"|(?:cycle|course)\s+{ordinal}\b"
        rf"|{later_ordinal}\s+{modifiers}(?:dose|infusion|session)\b"
        rf"|(?:dose|infusion|session)\s+{later_ordinal}\b"
        r"|(?:completion|end|discontinuation)\s+of\s+(?:the\s+)?(?:treatment|therapy|intervention)\b"
        r"|(?:treatment|therapy|intervention)\s+(?:completion|end|discontinuation)\b)"
    )
    return (
        re.search(
            rf"(?<![\d.,]){number}\s+{re.escape(unit.removesuffix('s'))}s?\b"
            rf"\s+(?:after|following)\s+(?:the\s+)?{event}",
            time_frame,
            flags=re.IGNORECASE,
        )
        is not None
    )


def number_in(number: int, words: str) -> bool:
    """Whether the words give the number in digits, as a whole number of its own: 4 is
    in "week 4", and is not in "week 14", "week 4.5" or "four weeks"."""
    if number < 0:
        return False
    return re.search(rf"(?<![\d.,]){number}(?![\d]|[.,]\d)", words) is not None


def input_hash(outcomes: Sequence[Outcome]) -> str:
    """The hash of what a model is shown of a trial: the titles and time frames of its
    planned primary outcomes, in order. Readings belong to the record with this hash."""
    shown = [[outcome.measure, outcome.time_frame] for outcome in outcomes]
    return hashlib.sha256(json.dumps(shown, ensure_ascii=False).encode()).hexdigest()
