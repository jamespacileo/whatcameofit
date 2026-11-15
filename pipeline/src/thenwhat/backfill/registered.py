"""The steps a backfill can run. A new step is one module and one line here."""

from thenwhat.backfill.link_read import LinkRead
from thenwhat.backfill.link_screen import LinkScreen
from thenwhat.backfill.link_triage import LinkTriage
from thenwhat.backfill.news_search import NewsSearch
from thenwhat.backfill.steps import Step
from thenwhat.config import Settings


def registered_steps(settings: Settings) -> list[Step]:
    triage = LinkTriage()
    return [
        NewsSearch(leads_per_trial=settings.leads_per_trial),
        LinkScreen(links_max=settings.lead_links_max),
        triage,
        LinkRead(
            pass_above=settings.lead_pass_above,
            reject_below=settings.lead_reject_below,
            triage_version=triage.version,
            min_labels=settings.lead_evaluation_min_labels,
            reads_per_claim=settings.lead_reads_per_claim,
            vertical_accept_above=settings.vertical_accept_above,
            same_claim_accept_above=settings.same_claim_accept_above,
            treatment_accept_above=settings.treatment_accept_above,
            approve_drafts_by_rule=settings.approve_drafts_by_rule,
            match_reject_below=settings.match_reject_below,
            match_accept_above=settings.match_accept_above,
        ),
    ]
