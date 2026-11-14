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


class SourcePaused(SourceStop):
    """The source said "too many requests" and is not asked until the pause has passed."""
