"""What a backfill command refuses, in words for the operator."""


class BackfillError(Exception):
    """A backfill command could not do what was asked."""


class DuplicateStep(BackfillError):
    """Two steps were declared with one name."""


class UnknownStep(BackfillError):
    """No step has the name given."""


class NoAllowance(BackfillError):
    """A step's source has no configured allowance."""


class SourceStop(Exception):
    """A source may not be asked right now. The run ends; the record stays due and no
    attempt is counted."""


class AllowanceUsedUp(SourceStop):
    """The source's allowance for the period is spent."""


class SpendCeilingReached(SourceStop):
    """The month's recorded model cost has reached the ceiling. No call was made."""


class ModelUnreachable(SourceStop):
    """A call to the model did not get through. That says nothing about the record it
    was for, so the run ends with the record still due and no attempt counted."""


class SourcePaused(SourceStop):
    """The source said "too many requests" and is not asked until the pause has passed."""


class ReaderUnavailable(SourceStop):
    """The page reader could not be asked: it did not answer, it failed, it said it was
    overloaded, or it answered in a form the pipeline does not know. That says nothing
    about the site asked for, so nothing is recorded against it (openspec page-reading)."""
