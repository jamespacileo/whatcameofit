"""The triage step: from a link lead's title alone, how likely its article reports a
specific treatment for a specific condition. Behavior: openspec lead-triage.

It fetches no article. It stores a score and nothing else: whether a lead is passed,
held or rejected is worked out from the score and the operator's two thresholds each
time it is asked, so changing a threshold scores nothing again.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, and_, case, false, func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import ModelUnreachable
from thenwhat.backfill.steps import MODEL, Failed, ModelSpend
from thenwhat.backfill.topics import title_names
from thenwhat.db.models import DecisionLog, LinkLead
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import (
    LEAD_TRIAGE,
    TREATMENT_REPORT,
    headline_text,
    lead_ref,
    triage_headlines,
)
from thenwhat.domain import ScreenOutcome, WorkOutcome
from thenwhat.sources.base import SystemTime, Time


class Standing(StrEnum):
    """Where a link lead stands after triage, by its score and the two thresholds."""

    PASSED = "passed"
    HELD = "held"
    REJECTED = "rejected"
    # Scored, but the operator has not set both thresholds yet.
    UNDECIDED = "undecided"
    NOT_SCORED = "not_scored"


def standing_of(
    score: float | None, pass_above: float | None, reject_below: float | None
) -> Standing:
    """Passed at or above the pass threshold, rejected below the reject threshold, held
    between them. While either threshold is unset nothing is passed or rejected."""
    if score is None:
        return Standing.NOT_SCORED
    if pass_above is None or reject_below is None:
        return Standing.UNDECIDED
    if score >= pass_above:
        return Standing.PASSED
    if score < reject_below:
        return Standing.REJECTED
    return Standing.HELD


def is_passed(pass_above: float | None, reject_below: float | None) -> ColumnElement[bool]:
    """The query condition for a lead that is passed. False for every lead while either
    threshold is unset."""
    if pass_above is None or reject_below is None:
        return false()
    return and_(LinkLead.triage_score.is_not(None), LinkLead.triage_score >= pass_above)


def standings(
    session: Session, pass_above: float | None, reject_below: float | None
) -> Counter[Standing]:
    """How many leads that screening left in scope stand where."""
    if pass_above is None or reject_below is None:
        scored = Standing.UNDECIDED.value
        standing: ColumnElement[str] = case(
            (LinkLead.triage_score.is_(None), Standing.NOT_SCORED.value), else_=scored
        )
    else:
        standing = case(
            (LinkLead.triage_score.is_(None), Standing.NOT_SCORED.value),
            (LinkLead.triage_score >= pass_above, Standing.PASSED.value),
            (LinkLead.triage_score < reject_below, Standing.REJECTED.value),
            else_=Standing.HELD.value,
        )
    rows = session.execute(
        select(standing, func.count())
        .where(LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE)
        .group_by(standing)
    )
    return Counter({Standing(name): number for name, number in rows})


def _stop_if_unreachable(failure: DecisionFailed) -> None:
    """End the run when the model could not be reached. Found on the first real run: a
    minute without a connection, met by four workers, used up three attempts each for
    449 leads that nothing was wrong with."""
    if failure.unreachable:
        raise ModelUnreachable(
            f"The model could not be reached: {failure}. Nothing was scored by this call; "
            "the leads are still due. Run the step again."
        )


class DecisionClient:
    """What a step that asks the decision backend is given. The backend is made for the
    session at hand, because it logs each decision and its cost there."""

    def __init__(self, make_backend: Callable[[Session], Backend]) -> None:
        self.requests_made = 0
        self._make_backend = make_backend

    def backend(self, session: Session) -> Backend:
        return self._make_backend(session)


class LinkTriage:
    name = "link_triage"
    version = 1
    record_kind = "link_lead"
    model = LinkLead
    source = MODEL
    requests_per_record = 0
    batch_size = 20
    # For the plan. Measured on the first live run (2026-11-14, Decisions API): 60,362
    # input tokens for 200 headlines. The question and the options' descriptions are
    # sent with every headline, so a headline costs far more than its own words.
    model_spend = ModelSpend(input_tokens=300)

    def __init__(
        self,
        time: Time | None = None,
        *,
        topic_terms: Sequence[str] = (),
        since: date | None = None,
    ) -> None:
        self._time = time or SystemTime()
        # Only leads first shared on or after this day are scored; None scores any.
        self.since = since
        # The words of the operator's topics. Leads whose title names one are scored
        # first, so a topic need not wait for every older lead.
        self._names_a_topic = title_names(topic_terms)

    def first(self) -> ColumnElement[bool] | None:
        """The leads whose title names one of the operator's topics come first. The order
        changes which lead is scored when, never what it scores."""
        return self._names_a_topic

    def scope(self) -> ColumnElement[bool]:
        """Leads that screening left in scope: on a listed outlet and not yet tracked."""
        in_scope = LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE
        if self.since is None:
            return in_scope
        since = datetime.combine(self.since, datetime.min.time(), tzinfo=UTC)
        return and_(in_scope, LinkLead.first_shared_at >= since)

    def inputs(self, record: LinkLead) -> dict[str, Any]:
        return {
            "title": record.title,
            "outlet": record.outlet,
            "year": record.first_shared_at.year,
        }

    def _text(self, record: LinkLead) -> str:
        return headline_text(record.title, record.outlet, record.first_shared_at.year)

    def _keep(self, record: LinkLead, score: float) -> WorkOutcome:
        record.triage_score = score
        record.triage_version = self.version
        return WorkOutcome.DONE

    def run(
        self, session: Session, record: LinkLead, client: DecisionClient
    ) -> WorkOutcome | Failed:
        """Score one lead. With no usable answer the lead keeps no score, and the logged
        failure and the call's cost are kept."""
        try:
            [score] = triage_headlines(
                session,
                client.backend(session),
                headlines=[(record.id, self._text(record))],
                now=self._time.now(),
            )
        except DecisionFailed as failure:
            _stop_if_unreachable(failure)
            session.flush()
            return Failed(str(failure))
        return self._keep(record, score)

    def run_many(
        self, session: Session, records: Sequence[LinkLead], client: DecisionClient
    ) -> list[WorkOutcome | Failed]:
        """Score several leads in one call. When the call leaves a lead unanswered, the
        answers it did give are kept and only the leads without one are asked again,
        each alone. Nothing is rolled back: every decision and every cost stays logged."""
        now = self._time.now()
        try:
            scores = triage_headlines(
                session,
                client.backend(session),
                headlines=[(record.id, self._text(record)) for record in records],
                now=now,
            )
        except DecisionFailed as failure:
            _stop_if_unreachable(failure)
            session.flush()
            if len(records) == 1:
                return [Failed(str(failure))]
            answered = dict(
                session.execute(
                    select(DecisionLog.input_ref, DecisionLog.output).where(
                        DecisionLog.step == LEAD_TRIAGE,
                        DecisionLog.created_at == now,
                        DecisionLog.output.is_not(None),
                        DecisionLog.input_ref.in_([lead_ref(record.id) for record in records]),
                    )
                ).all()
            )
            outcomes: list[WorkOutcome | Failed] = []
            for record in records:
                given = answered.get(lead_ref(record.id))
                if given is not None:
                    outcomes.append(self._keep(record, given["probabilities"][TREATMENT_REPORT]))
                else:
                    outcomes.append(self.run(session, record, client))
            return outcomes
        return [self._keep(record, score) for record, score in zip(records, scores, strict=True)]
