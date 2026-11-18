"""Why a claim step did not finish, and what a failure of a source or a model means for
the claim: put off, stopped, or failed. Behavior: openspec work-ledger, "An outcome says
whether the record comes back"."""

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from thenwhat.decide.core import DecisionFailed
from thenwhat.llm.errors import BudgetExceeded, LlmError
from thenwhat.sources.base import (
    AllowanceUsedUp,
    MissingContact,
    MissingKey,
    SourceError,
    SourceThrottled,
    TermsNotRecorded,
)
from thenwhat.work.errors import (
    CannotAsk,
    ModelUnreachable,
    SourceStop,
    SpendCeilingReached,
    StopAfterProgress,
)
from thenwhat.work.outcome import Later, Reason, ReasonClass
from thenwhat.work.steps import Failed

# How long a claim is put off when a source failed and stated no wait.
SOURCE_RETRY = timedelta(hours=1)

# --- put off: the claim comes back by itself ---------------------------------------------
SOURCE_FAILED = Reason("source_failed", ReasonClass.LATER, "a source did not answer: {error}")
MESH_UNRESOLVED = Reason(
    "mesh_unresolved", ReasonClass.LATER, "MeSH could not resolve entry terms for {names}"
)
OUTLET_HELD = Reason(
    "outlet_held", ReasonClass.LATER, "the page reader cannot ask {outlet} for an article yet"
)

# --- needs a fix: waits to be made due ---------------------------------------------------
ARTICLE_UNREADABLE = Reason(
    "article_unreadable",
    ReasonClass.NEEDS_FIX,
    "the page reader could not read an article: {said}. Paste its text with"
    " `thenwhat extract article --paste`",
)
PAPERS_OFF = Reason(
    "papers_off",
    ReasonClass.NEEDS_FIX,
    "paper search is off because it was disabled or OPENALEX_API_KEY is unset",
)
KIND_TERM_MISSING = Reason("kind_term_missing", ReasonClass.NEEDS_FIX, "{said}")

# --- final: the claim holds nothing for the step -----------------------------------------
NO_INTERVENTION = Reason("no_intervention", ReasonClass.FINAL, "the claim has no intervention")
NO_TRIAL_TO_READ = Reason(
    "no_trial_to_read",
    ReasonClass.FINAL,
    "no approved trial of the claim has a stored registry record with a planned primary outcome",
)
NOTHING_TO_DECIDE = Reason(
    "nothing_to_decide", ReasonClass.FINAL, "the claim is no read's draft awaiting review"
)
NO_DRAFT_TRIAL_APPROVED = Reason(
    "no_draft_trial_approved", ReasonClass.FINAL, "none of the drafting trials is approved"
)


class SourceNotSetUp(SourceStop):
    """A source cannot be asked for any claim: its contact, key or terms are not set, its
    allowance is used up, or the page reader is not configured. The run ends with every
    claim still due."""


# Failures of a source that say nothing of the claim asked about and hold for every claim.
CANNOT_ASK = (MissingContact, MissingKey, TermsNotRecorded, AllowanceUsedUp)


def put_off(failed: SourceError, now: datetime) -> Later:
    """A source failed for this claim, on every attempt: the claim is put off, never
    recorded as searched with nothing found. It comes back after the wait the source
    stated, or after `SOURCE_RETRY`. A source that cannot be asked at all stops the run."""
    if isinstance(failed, CannotAsk):
        raise failed
    if isinstance(failed, CANNOT_ASK):
        raise SourceNotSetUp(str(failed)) from failed
    stated = failed.retry_after if isinstance(failed, SourceThrottled) else None
    wait = max(SOURCE_RETRY, timedelta(seconds=stated or 0))
    return Later(SOURCE_FAILED, now + wait, {"error": str(failed)})


def model_failed(failed: DecisionFailed | LlmError) -> Failed:
    """A model gave no usable answer for this claim: a failure, with what was logged and
    paid for kept. A model that could not be reached, or a spent ceiling, stops the run."""
    if isinstance(failed, CannotAsk) and not isinstance(failed, BudgetExceeded):
        raise failed
    if isinstance(failed, BudgetExceeded):
        raise SpendCeilingReached(str(failed)) from failed
    if isinstance(failed, DecisionFailed) and failed.unreachable:
        raise ModelUnreachable(str(failed)) from failed
    return Failed(str(failed))


def attempt[T](
    session: Session, work: Callable[[], T]
) -> T | SourceError | DecisionFailed | LlmError:
    """Do one part of a step in a savepoint. A source that fails undoes what the part
    wrote and is returned. A model that gives no usable answer is returned with what the
    part kept, its logged decision among it: a paid answer is not thrown away. Anything
    else is raised, and the runner undoes the step."""
    try:
        with session.begin_nested():
            try:
                return work()
            except BudgetExceeded as budget:
                raise SpendCeilingReached(str(budget), until=budget.until) from budget
            except CannotAsk:
                # A source or a model that cannot be asked says nothing of this claim:
                # it stops the run, and is never turned into an answer for the claim.
                raise
            except (DecisionFailed, LlmError) as failed:
                return failed
    except CannotAsk:
        raise
    except SourceError as failed:
        return failed


def run_parts(
    session: Session, parts: Iterable[Callable[[], None]], now: datetime
) -> Later | Failed | None:
    """Run each independent part in a savepoint. A later part's failure leaves earlier
    completed parts available on retry, including decisions already paid for."""
    for part in parts:
        try:
            answer = attempt(session, part)
            if isinstance(answer, SourceError):
                return put_off(answer, now)
            if isinstance(answer, DecisionFailed | LlmError):
                return model_failed(answer)
        except SourceStop as stop:
            raise StopAfterProgress(stop) from stop
    return None
