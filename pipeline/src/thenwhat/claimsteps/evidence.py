"""What a claim's approved matches give: the evidence events their registry records
show, and the readings of its trials' planned outcomes. Behavior: openspec
evidence-events and record-readings, as steps of the work ledger."""

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from thenwhat.claimsteps.inputs import Inputs
from thenwhat.claimsteps.reasons import (
    NO_TRIAL_TO_READ,
    SOURCE_FAILED,
    attempt,
    model_failed,
    put_off,
)
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.clinical.service import TreeRun, read_tree
from thenwhat.db.models import Claim
from thenwhat.decide.core import DecisionFailed
from thenwhat.domain import WorkOutcome
from thenwhat.events.fetch import fetch_claim
from thenwhat.llm.errors import BudgetExceeded, LlmError
from thenwhat.readings.service import INSTRUCTIONS_VERSION, ReadingsRun, read_trials, trials_of
from thenwhat.sources.base import SourceError
from thenwhat.work.errors import SpendCeilingReached, StopAfterProgress
from thenwhat.work.outcome import NothingFound
from thenwhat.work.steps import Failed


class ClaimFetch(ClaimStep):
    """Read the registries for the claim's approved matches and record the events they
    show, then derive its status again. It is due again when its approved matches
    change."""

    name = "claim_fetch"
    reasons = (SOURCE_FAILED,)

    def __init__(
        self,
        *,
        threshold: float,
        no_signal_years: int,
        paper_max_age: timedelta,
        papers_enabled: bool = True,
        **step: Any,
    ) -> None:
        super().__init__(**step)
        self.threshold = threshold
        self.no_signal_years = no_signal_years
        self.paper_max_age = paper_max_age
        self.papers_enabled = papers_enabled
        # What reading the MeSH tree gave for each claim fetched: the run, or why not.
        self.trees: dict[int, TreeRun | SourceError] = {}

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        snapshot = {"approved": inputs.approved.get(claim_id, [])}
        if not self.papers_enabled:
            return {**snapshot, "papers_enabled": False}
        return snapshot

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        now = self.now()
        trials, literature, notices = sources.make_evidence(session)
        created = attempt(
            session,
            lambda: fetch_claim(
                session,
                claim,
                trials=trials,
                literature=literature if self.papers_enabled else None,
                notices=notices,
                threshold=self.threshold,
                no_signal_years=self.no_signal_years,
                paper_max_age=self.paper_max_age,
                now=now,
            ),
        )
        if isinstance(created, SourceError):
            return put_off(created, now)
        if isinstance(created, DecisionFailed | LlmError):
            return model_failed(created)
        self.results[claim.id] = created
        # The claim's clinical categories are derived from the records just stored, and
        # placed in MeSH's tree by NLM's own records. Reading those here keeps a new term
        # from leaving the claim's categories unread in the next export. NLM not
        # answering, or being paused, is no failure of the fetch and does not stop the
        # run: the records above are kept, and `thenwhat clinical tree` reads what is
        # missing.
        try:
            self.trees[claim.id] = read_tree(session, sources.make_mesh(session), [claim])
        except SourceError as error:
            self.trees[claim.id] = error
        return WorkOutcome.DONE


class ClaimReadings(ClaimStep):
    """Have the model read the stored registry records of the claim's approved trials. A
    trial whose record and instructions have not changed is not read again. It is due
    again when the claim's approved trial events, which hold those records, change."""

    name = "claim_readings"
    version = 2
    reasons = (NO_TRIAL_TO_READ,)

    def __init__(self, *, at_once: int, **step: Any) -> None:
        super().__init__(**step)
        self.at_once = at_once

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        return {
            "trial_events": inputs.trial_events.get(claim_id, []),
            "instructions": INSTRUCTIONS_VERSION,
        }

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        trials = trials_of(session, claim)
        if not trials:
            return NothingFound(NO_TRIAL_TO_READ)
        run: ReadingsRun = read_trials(
            session, sources.make_llm(session), trials, now=self.now(), at_once=self.at_once
        )
        self.results[claim.id] = run
        if run.stop is not None:
            if isinstance(run.stop, BudgetExceeded):
                raise StopAfterProgress(SpendCeilingReached(str(run.stop), until=run.stop.until))
            raise StopAfterProgress(run.stop)
        if run.failed:
            # The trials read stay read; the others are read when the claim comes back.
            return Failed("; ".join(f"{trial} was not read: {said}" for trial, said in run.failed))
        return WorkOutcome.DONE
