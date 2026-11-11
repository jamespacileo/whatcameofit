"""Refusals and failures of language model calls. Messages are safe to show."""


class LlmError(Exception):
    """A language model call was refused or failed."""


class LlmNotConfigured(LlmError):
    pass


class BudgetExceeded(LlmError):
    pass


class LlmCallFailed(LlmError):
    pass


class LlmOutputInvalid(LlmError):
    """The model never produced output that fits the schema."""

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields
        named = f" Failing fields: {', '.join(fields)}." if fields else ""
        super().__init__(f"The model's output failed validation on every attempt.{named}")
