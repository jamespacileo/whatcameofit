"""What a step answers for a record, and whether the record comes back.
Behavior: openspec work-ledger, "An outcome says whether the record comes back".

An answer is one of three classes. Final: done or nothing found, and the record is
finished. Later: the cause is expected to pass, and the record comes back by itself once
a stated time has passed. Needs a fix: the cause will not pass until something outside
the record changes, and the record waits to be made due.

Every answer but done and a failure carries a reason: a code the step has declared, with
the values it carries. The words a person reads are made from the code here and nowhere
else, so a report and a stored detail cannot say two things.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ReasonClass(StrEnum):
    """Whether a record with this reason is finished, comes back by itself, or waits."""

    FINAL = "final"
    LATER = "later"
    NEEDS_FIX = "needs_fix"


class ReasonMisused(Exception):
    """An answer was given a reason of another class, or values its words do not take."""


class UndeclaredReason(Exception):
    """A step answered with a reason code it has not declared."""


@dataclass(frozen=True, slots=True)
class Reason:
    """Why a record was not done, as a code. `words` may name the values the reason
    carries in braces: "the site answered {status}"."""

    code: str
    kind: ReasonClass
    words: str

    def say(self, values: Mapping[str, Any] | None = None) -> str:
        """The reason in words, with its values put in."""
        try:
            return self.words.format(**(values or {}))
        except (KeyError, IndexError) as missing:
            raise ReasonMisused(
                f"The reason '{self.code}' is said with a value it was not given: {missing}."
            ) from None


def _check(reason: Reason, wanted: ReasonClass, values: Mapping[str, Any]) -> None:
    if reason.kind is not wanted:
        raise ReasonMisused(
            f"The reason '{reason.code}' is declared as {reason.kind.value} and cannot be "
            f"given with an answer that is {wanted.value}."
        )
    reason.say(values)


@dataclass(frozen=True, slots=True)
class NothingFound:
    """The record holds nothing for the step. Finished."""

    reason: Reason
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check(self.reason, ReasonClass.FINAL, self.values)


@dataclass(frozen=True, slots=True)
class Later:
    """The record cannot be worked on before a time, for a cause that passes. No attempt
    is counted, and the record is due again once the time has passed."""

    reason: Reason
    not_before: datetime
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check(self.reason, ReasonClass.LATER, self.values)


@dataclass(frozen=True, slots=True)
class NeedsFix:
    """The record cannot be worked on until something outside it changes. No attempt is
    counted, and the record waits until it is made due by its reason."""

    reason: Reason
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check(self.reason, ReasonClass.NEEDS_FIX, self.values)


Reasoned = NothingFound | Later | NeedsFix


def reasons_of(step: Any) -> Sequence[Reason]:
    """The reasons a step has declared: none for a step that gives no reasoned answer."""
    return tuple(getattr(step, "reasons", ()))


def declared(step: Any, code: str) -> Reason:
    """The step's reason with this code. Refuses a code the step has not declared."""
    for reason in reasons_of(step):
        if reason.code == code:
            return reason
    known = ", ".join(sorted(reason.code for reason in reasons_of(step))) or "none"
    raise UndeclaredReason(
        f"The step '{step.name}' has declared no reason '{code}'. Its reasons: {known}."
    )


def check_declared(step: Any, answer: Reasoned) -> None:
    """Refuse an answer whose reason the step has not declared as it stands."""
    if declared(step, answer.reason.code) != answer.reason:
        raise UndeclaredReason(
            f"The step '{step.name}' answered with a reason '{answer.reason.code}' that "
            "differs from the one it declared under that code."
        )
