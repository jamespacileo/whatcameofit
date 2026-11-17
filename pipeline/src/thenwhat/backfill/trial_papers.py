"""The step that asks the paper index which papers carry a stored trial's registry
number. Behavior: openspec trial-coverage, "Papers that carry the trial's number" and
"Nothing found is an answer".

The numbers of many trials go in one search. A paper is given to a trial only when the
paper's own record, read back, carries that trial's number, and never when it carries
more than three: such a paper is a review of many trials and identifies none. What is
stored is the tie and the paper's reduced record. No claim, match or event is made, and
nothing here says a paper reports a trial's results: only the registry record does.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_sets import (
    SETS,
    active_or_ended_in,
    completed_with_results_since_2025,
    ended_in,
)
from thenwhat.config import SourceAllowance
from thenwhat.db.models import RegistryTrial, TrialPaper
from thenwhat.domain import WorkOutcome
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.europepmc import MAX_TRIALS_OF_ONE_PAPER
from thenwhat.sources.pubmed import REGISTRY_NUMBER, Paper, PubMed
from thenwhat.work.outcome import NothingFound, Reason, ReasonClass


class PaperIndex(Protocol):
    name: str
    requests_made: int

    def papers_carrying(self, numbers: Sequence[str]) -> tuple[list[Paper], datetime]: ...


# The index was asked and holds no paper that names the trial's registry number.
NO_PAPERS = Reason("no_papers", ReasonClass.FINAL, "the paper index holds no paper for it")


class TrialPapers:
    name = "pubmed_papers"
    reasons = (NO_PAPERS,)
    version = 1
    record_kind = "registry_trial"
    model = RegistryTrial
    source = PubMed.name
    # Kept for the step protocol. A search carries many trials: what the due trials
    # need is `requests_for`, which the plan shows instead.
    requests_per_record = 1
    # One search for each batch of trials and, in the sample of 2026-11-17, one fetch of
    # the papers it found: a fetch holds 200 papers and a batch of 25 trials found 12.
    REQUESTS_PER_BATCH = 2

    def __init__(self, trials_per_request: int = 50, year: int | None = None) -> None:
        self.batch_size = trials_per_request
        # The calendar year the rolling set is chosen in, given by the command that
        # builds the step. Without it only the two dated sets are asked for.
        self.year = year

    def requests_for(self, due: int) -> int:
        """About how many requests this many due trials need, asked in batches."""
        return -(-due // self.batch_size) * self.REQUESTS_PER_BATCH

    def records_for(self, requests: int) -> int:
        """About how many due trials this many requests cover."""
        return requests // self.REQUESTS_PER_BATCH * self.batch_size

    def scope(self) -> ColumnElement[bool]:
        """The trials of the rolling set (under way now, or ended in the year) and of
        the two dated sets it replaced as the target, so a trial already in scope stays
        in scope. Cited by a claim or not: a paper belongs on a trial's page either way.
        Only ClinicalTrials.gov's numbers are in PubMed's field under that registry's
        name."""
        rules = [rule() for rule in SETS.values()]
        if self.year is not None:
            rules.append(active_or_ended_in(self.year))
        return and_(RegistryTrial.registry_name == ClinicalTrials.name, or_(*rules))

    def first(self) -> ColumnElement[bool]:
        """Trials that ended in the year and trials with results posted first: they are
        the fewer, and where papers are."""
        with_results = RegistryTrial.has_results.is_(True)
        if self.year is None:
            return or_(completed_with_results_since_2025(), with_results)
        return or_(ended_in(self.year), with_results)

    def inputs(self, record: RegistryTrial) -> dict[str, Any]:
        return {"number": record.external_id}

    def run(
        self, session: Session, record: RegistryTrial, client: PaperIndex
    ) -> WorkOutcome | NothingFound:
        return self.run_many(session, [record], client)[0]

    def run_many(
        self, session: Session, records: Sequence[RegistryTrial], client: PaperIndex
    ) -> list[WorkOutcome | NothingFound]:
        asked = {
            record.external_id.upper(): record
            for record in records
            if REGISTRY_NUMBER.fullmatch(record.external_id.upper())
        }
        papers, fetched_at = client.papers_carrying(list(asked))
        found: set[int] = set()
        for paper in papers:
            if len(paper.trial_numbers) > MAX_TRIALS_OF_ONE_PAPER:
                continue
            for number in paper.trial_numbers:
                trial = asked.get(number)
                if trial is None:
                    continue
                found.add(trial.id)
                kept = {"raw_payload": paper.raw, "fetched_at": fetched_at}
                session.execute(
                    insert(TrialPaper)
                    .values(
                        registry_trial_id=trial.id,
                        source_name=client.name,
                        pubmed_id=paper.pubmed_id,
                        **kept,
                    )
                    .on_conflict_do_update(
                        constraint="uq_trial_paper_trial_source_paper", set_=kept
                    )
                )
        return [
            WorkOutcome.DONE if record.id in found else NothingFound(NO_PAPERS)
            for record in records
        ]


# A weeknight's off-peak hours at NCBI: 21:00 to 05:00 Eastern.
OFF_PEAK_NIGHT_HOURS = 8
# What NCBI allows a client a second without a key and with one (docs/sources.md).
PER_SECOND_WITHOUT_KEY, PER_SECOND_WITH_KEY = 3, 10


@dataclass(frozen=True, slots=True)
class PaperEstimate:
    """What asking the paper index for the trials not yet asked would take."""

    trials: int
    requests: int
    # At the configured least interval between requests.
    minutes: float
    # Weeknights of off-peak hours, under the allowance for a day and the interval.
    nights: int
    # At the fastest NCBI allows a client with a key, were the interval set to it.
    minutes_with_key: float


def estimate_for(step: TrialPapers, due: int, allowance: SourceAllowance) -> PaperEstimate:
    """How many requests the due trials need, how long they take at the allowed rate,
    and how many off-peak nights, with no key and with one. No request is sent."""
    requests = step.requests_for(due)
    window = OFF_PEAK_NIGHT_HOURS * 3600
    by_rate = int(window / allowance.interval_seconds) if allowance.interval_seconds else requests
    by_count = int(allowance.requests * max(1, OFF_PEAK_NIGHT_HOURS / allowance.period_hours))
    a_night = max(1, min(by_rate, by_count))
    return PaperEstimate(
        trials=due,
        requests=requests,
        minutes=requests * allowance.interval_seconds / 60,
        nights=-(-requests // a_night),
        minutes_with_key=requests / PER_SECOND_WITH_KEY / 60,
    )
