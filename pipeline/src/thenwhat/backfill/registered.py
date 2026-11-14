"""The steps a backfill can run. A new step is one module and one line here."""

from thenwhat.backfill.news_search import NewsSearch
from thenwhat.backfill.steps import Step
from thenwhat.config import Settings


def registered_steps(settings: Settings) -> list[Step]:
    return [NewsSearch(leads_per_trial=settings.leads_per_trial)]
