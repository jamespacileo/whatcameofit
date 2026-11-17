"""What a backfill command refuses, in words for the operator."""

from datetime import datetime


class BackfillError(Exception):
    """A backfill command could not do what was asked."""


class DuplicateStep(BackfillError):
    """Two steps were declared with one name."""


class UnknownStep(BackfillError):
    """No step has the name given."""


class NoAllowance(BackfillError):
    """A step's source has no configured allowance."""


class KeysOutOfDate(BackfillError):
    """Stored link leads were keyed under an earlier form of the address key."""


class WorkInProgress(BackfillError):
    """A step over the same records was at work a moment ago."""


class SourceStop(Exception):
    """A source may not be asked right now. The run ends; the record stays due and no
    attempt is counted."""


class StopAfterProgress(SourceStop):
    """Stop after committing earlier, completed parts of the record. The interrupted
    part has already been rolled back and the record itself stays due."""

    def __init__(self, cause: SourceStop) -> None:
        super().__init__(str(cause))
        self.cause = cause


class CannotAsk(SourceStop):
    """A source or a model cannot be asked: it is paused, its allowance or quota is used
    up, its key was refused, the spend ceiling is reached, or it kept failing for causes
    that pass. That says nothing about the record it was asked for. `until` is when it
    may be asked again, where that is known (openspec source-clients, decision-steps)."""

    def __init__(self, message: str, *, until: datetime | None = None) -> None:
        super().__init__(message)
        self.until = until


class AllowanceUsedUp(CannotAsk):
    """The source's allowance for the period is spent."""


class SpendCeilingReached(CannotAsk):
    """The month's recorded model cost has reached the ceiling. No call was made."""


class ModelUnreachable(CannotAsk):
    """A call to the model did not get through. That says nothing about the record it
    was for, so the run ends with the record still due and no attempt counted."""


class SourcePaused(CannotAsk):
    """The source said it cannot be asked before a time, and is sent nothing until then."""


class ReaderUnavailable(SourceStop):
    """The page reader could not be asked: it did not answer, it failed, it said it was
    overloaded, or it answered in a form the pipeline does not know. That says nothing
    about the site asked for, so nothing is recorded against it (openspec page-reading)."""
