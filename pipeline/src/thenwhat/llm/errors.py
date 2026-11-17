"""Refusals and failures of language model calls. Messages are safe to show."""

from thenwhat.work.errors import CannotAsk


class LlmError(Exception):
    """A language model call was refused or failed."""


class LlmNotConfigured(LlmError):
    pass


class BudgetExceeded(LlmError, CannotAsk):
    """The month's recorded cost has reached the ceiling, so no call was made. The model
    cannot be asked until the month ends: a run that meets this stops."""


class LlmCallFailed(LlmError):
    pass


class ModelCannotBeAsked(LlmCallFailed, CannotAsk):
    """The model cannot be asked now: its key was refused, its quota is used up, it is
    paused, or it failed for causes that pass on every attempt (openspec decision-steps,
    "A backend that cannot be asked is not a failed decision"). That says nothing about
    what it was asked: a run that meets this stops, with its records still due."""


class LlmOutputInvalid(LlmError):
    """The model never produced output that fits the schema."""

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields
        named = f" Failing fields: {', '.join(fields)}." if fields else ""
        super().__init__(f"The model's output failed validation on every attempt.{named}")
