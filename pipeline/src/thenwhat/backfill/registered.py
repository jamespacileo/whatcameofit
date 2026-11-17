"""The steps a backfill can run. A new step is one module and one line here."""

from typing import Any

from thenwhat.backfill.link_read import LinkRead
from thenwhat.backfill.link_screen import LinkScreen
from thenwhat.backfill.link_triage import LinkTriage
from thenwhat.backfill.news_search import NewsSearch
from thenwhat.backfill.steps import Step
from thenwhat.backfill.topics import terms_of
from thenwhat.backfill.trial_papers import TrialPapers
from thenwhat.config import Settings


def link_read_step(settings: Settings, triage_version: int, **options: Any) -> LinkRead:
    """The reading step as the settings give it. `options` narrow it to a set of trials
    for `thenwhat backfill read-set`; the step, its name and its ledger are the same."""
    options.setdefault("trial_set", settings.lead_read_trial_set)
    return LinkRead(
        pass_above=settings.lead_pass_above,
        reject_below=settings.lead_reject_below,
        triage_version=triage_version,
        min_labels=settings.lead_evaluation_min_labels,
        reads_per_claim=settings.lead_reads_per_claim,
        vertical_accept_above=settings.vertical_accept_above,
        same_claim_accept_above=settings.same_claim_accept_above,
        treatment_accept_above=settings.treatment_accept_above,
        topic_terms=terms_of(),
        approve_drafts_by_rule=settings.approve_drafts_by_rule,
        match_reject_below=settings.match_reject_below,
        match_accept_above=settings.match_accept_above,
        outlet_gap_seconds=settings.reader_outlet_gap_seconds,
        read_since=settings.lead_read_since,
        **options,
    )


def make_triage(settings: Settings) -> LinkTriage:
    return LinkTriage(topic_terms=terms_of(), since=settings.lead_triage_since)


def registered_steps(settings: Settings, year: int | None = None) -> list[Step]:
    """Every step, as the settings give it. `year` is the calendar year the rolling set
    of trials is chosen in, read from the clock by the command."""
    triage = make_triage(settings)
    return [
        NewsSearch(leads_per_trial=settings.leads_per_trial),
        TrialPapers(trials_per_request=settings.pubmed_trials_per_request, year=year),
        LinkScreen(links_max=settings.lead_links_max),
        triage,
        link_read_step(settings, triage.version),
    ]
