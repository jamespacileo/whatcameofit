"""What is held for the trials of the rolling set, counted by group. Counts only: no
trial is named, nothing is scored and no source is asked. Behavior: openspec
trial-coverage, "A coverage report counts what is held for the set".

A count here says what the database holds for a group of trials. It says nothing of how
any trial turned out, and a trial with no paper or no claim is not one that failed.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_references import references_of
from thenwhat.backfill.trial_sets import groups_of
from thenwhat.db.models import RegistryTrial, TrialPaper

# One rule says which trials a published claim cites: the listing's, which is the
# site's own index of cited trials.
from thenwhat.export.trials_listing import _cited as cited_by_published_claims


@dataclass(slots=True)
class GroupCoverage:
    name: str
    trials: int = 0
    with_results: int = 0
    # The registry record lists a paper as a result or links one from PubMed.
    with_listed_paper: int = 0
    # A paper's own PubMed record carries the trial's number.
    with_pubmed_paper: int = 0
    cited_by_published_claim: int = 0
    # The registry last updated the record before 1 January of last year.
    not_updated_since_before_last_year: int = 0

    def add(self, other: "GroupCoverage") -> None:
        self.trials += other.trials
        self.with_results += other.with_results
        self.with_listed_paper += other.with_listed_paper
        self.with_pubmed_paper += other.with_pubmed_paper
        self.cited_by_published_claim += other.cited_by_published_claim
        self.not_updated_since_before_last_year += other.not_updated_since_before_last_year


@dataclass(slots=True)
class Coverage:
    year: int
    groups: list[GroupCoverage]

    @property
    def total(self) -> GroupCoverage:
        total = GroupCoverage("all")
        for group in self.groups:
            total.add(group)
        return total


def coverage_of(session: Session, year: int) -> Coverage:
    """Count, for each group of the rolling set chosen in `year`, the trials and how
    many have results posted, a paper the registry record lists, a paper found by
    number, a published claim that cites them, and a record not updated since before
    last year. The groups share no trial, so their counts add up."""
    names = list(groups_of(year))
    group = case(
        *((rule, place) for place, rule in enumerate(groups_of(year).values())), else_=None
    )
    stale_before = date(year - 1, 1, 1)
    has_paper = (
        select(TrialPaper.id).where(TrialPaper.registry_trial_id == RegistryTrial.id).exists()
    )
    counted = {place: GroupCoverage(name) for place, name in enumerate(names)}
    for place, trials, results, papers, stale in session.execute(
        select(
            group,
            func.count(),
            func.count().filter(RegistryTrial.has_results.is_(True)),
            func.count().filter(has_paper),
            func.count().filter(RegistryTrial.last_update_posted < stale_before),
        )
        .where(group.is_not(None))
        .group_by(group)
    ):
        one = counted[place]
        one.trials, one.with_results = trials, results
        one.with_pubmed_paper, one.not_updated_since_before_last_year = papers, stale

    # The papers a record lists are read by the one rule that reads them anywhere.
    module = RegistryTrial.raw_payload["protocolSection"]["referencesModule"]
    listed: Counter[int] = Counter()
    for place, references in session.execute(
        select(group, module)
        .where(group.is_not(None), module.is_not(None))
        .execution_options(yield_per=2000)
    ):
        if references_of({"protocolSection": {"referencesModule": references}}).papers:
            listed[place] += 1

    cited = list(cited_by_published_claims(session))
    cited_in: Counter[int] = Counter()
    for start in range(0, len(cited), 5000):
        for place, number in session.execute(
            select(group, func.count())
            .where(group.is_not(None), RegistryTrial.external_id.in_(cited[start : start + 5000]))
            .group_by(group)
        ):
            cited_in[place] += number
    for place, one in counted.items():
        one.with_listed_paper = listed[place]
        one.cited_by_published_claim = cited_in[place]
    return Coverage(year, list(counted.values()))
