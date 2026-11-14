"""The news search step: which articles name a registry trial's intervention and
indication. What it finds are article leads, never source articles.
Behavior: openspec article-leads."""

from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import ColumnElement
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.mediacloud import Story
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.db.models import ArticleLead, RegistryTrial
from thenwhat.domain import WorkOutcome
from thenwhat.sources.base import SystemTime, Time


class NewsIndex(Protocol):
    name: str
    requests_made: int

    def search(self, query: str, *, limit: int) -> list[Story]: ...


def query_for(name: str, indication: str) -> str:
    """The intervention's name as a phrase, with any of the indication's telling words."""
    words = " OR ".join(indication.split())
    phrase = name.replace('"', " ")
    return f'"{phrase}" AND ({words})'


class NewsSearch:
    name = "news_search"
    version = 1
    record_kind = "registry_trial"
    model = RegistryTrial
    source = "mediacloud"
    requests_per_record = 1

    def __init__(self, leads_per_trial: int = 20, time: Time | None = None) -> None:
        self.leads_per_trial = leads_per_trial
        self._time = time or SystemTime()

    def scope(self) -> ColumnElement[bool]:
        """Trials that name an intervention and a condition. A trial whose interventions
        are only a placebo or a description has no name and is never searched."""
        return RegistryTrial.search_name.is_not(None) & RegistryTrial.search_indication.is_not(None)

    def inputs(self, record: RegistryTrial) -> dict[str, Any]:
        return {"name": record.search_name, "indication": record.search_indication}

    def run(self, session: Session, record: RegistryTrial, client: NewsIndex) -> WorkOutcome:
        assert record.search_name and record.search_indication  # the scope guarantees both
        query = query_for(record.search_name, record.search_indication)
        stories = client.search(query, limit=self.leads_per_trial)
        fetched_at: datetime = self._time.now()
        for story in stories:
            # Once per trial and address: an article found again adds nothing.
            session.execute(
                insert(ArticleLead)
                .values(
                    registry_trial_id=record.id,
                    url=story.url,
                    outlet=story.outlet,
                    title=story.title,
                    published_date=story.published,
                    outlet_kind=kind_of(story.outlet),
                    source_name=client.name,
                    search_query=query,
                    raw_result=story.raw,
                    fetched_at=fetched_at,
                )
                .on_conflict_do_nothing(constraint="uq_article_lead_trial_url")
            )
        return WorkOutcome.DONE if stories else WorkOutcome.NOTHING_FOUND
