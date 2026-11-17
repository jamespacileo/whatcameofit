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
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_sets import SETS, completed_with_results_since_2025
from thenwhat.db.models import RegistryTrial, TrialPaper
from thenwhat.domain import WorkOutcome
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.europepmc import MAX_TRIALS_OF_ONE_PAPER
from thenwhat.sources.pubmed import REGISTRY_NUMBER, Paper, PubMed


class PaperIndex(Protocol):
    name: str
    requests_made: int

    def papers_carrying(self, numbers: Sequence[str]) -> tuple[list[Paper], datetime]: ...


class TrialPapers:
    name = "pubmed_papers"
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

    def __init__(self, trials_per_request: int = 50) -> None:
        self.batch_size = trials_per_request

    def requests_for(self, due: int) -> int:
        """About how many requests this many due trials need, asked in batches."""
        return -(-due // self.batch_size) * self.REQUESTS_PER_BATCH

    def records_for(self, requests: int) -> int:
        """About how many due trials this many requests cover."""
        return requests // self.REQUESTS_PER_BATCH * self.batch_size

    def scope(self) -> ColumnElement[bool]:
        """The trials of the named sets, cited by a claim or not: a paper belongs on a
        trial's page either way. Only ClinicalTrials.gov's numbers are in PubMed's field
        under that registry's name."""
        return and_(
            RegistryTrial.registry_name == ClinicalTrials.name,
            or_(*(rule() for rule in SETS.values())),
        )

    def first(self) -> ColumnElement[bool]:
        """The completed set first: it is the smaller, and where papers are."""
        return completed_with_results_since_2025()

    def inputs(self, record: RegistryTrial) -> dict[str, Any]:
        return {"number": record.external_id}

    def run(self, session: Session, record: RegistryTrial, client: PaperIndex) -> WorkOutcome:
        return self.run_many(session, [record], client)[0]

    def run_many(
        self, session: Session, records: Sequence[RegistryTrial], client: PaperIndex
    ) -> list[WorkOutcome]:
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
            WorkOutcome.DONE if record.id in found else WorkOutcome.NOTHING_FOUND
            for record in records
        ]
