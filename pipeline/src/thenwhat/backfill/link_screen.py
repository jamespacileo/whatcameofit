"""The screening step: what rules and stored data alone say about a link lead.
Behavior: openspec lead-screening.

It sends no request and calls no model. It decides whether a lead goes on to triage,
and records which claims and registry trials the database already holds for it. A link
is a candidate: it approves nothing and changes no claim, match or status.
"""

import re
import threading
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, delete, select, true
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.backfill.steps import NO_SOURCE
from thenwhat.db.models import (
    ArticleLead,
    Entity,
    LinkLead,
    LinkLeadLink,
    RegistryTrial,
    SourceArticle,
)
from thenwhat.domain import EntityType, OutletKind, ScreenOutcome, WorkOutcome

CLAIM = "claim"
REGISTRY_TRIAL = "registry_trial"

FOUND_BY_NEWS_SEARCH = "the news search found this address for the trial"
TITLE_NAMES_CLAIM = "the title names the claim's intervention"
TITLE_NAMES_TRIAL = "the title names the trial's intervention and its indication"

WORD = re.compile(r"[a-z0-9]+")


def words_of(text: str) -> tuple[str, ...]:
    """A text as whole words in lower case, the form names and titles are compared in."""
    return tuple(WORD.findall(text.lower()))


@dataclass(frozen=True, slots=True)
class Name:
    """A stored name to look for in a title, and the record it belongs to."""

    words: tuple[str, ...]
    record_kind: str
    record_id: int
    # For a trial: the telling words of its indication that are not words of its name,
    # one of which the title must hold too. Empty for a claim.
    beside: frozenset[str] = frozenset()


@dataclass(slots=True)
class Stored:
    """What the database held when a run began: the addresses of source articles and of
    article leads, and the names of claims' interventions and of registry trials."""

    tracked: dict[str, int] = field(default_factory=dict)
    searched: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    # Names by their first word, so a title is checked only against names that could
    # start at one of its words.
    names: dict[str, list[Name]] = field(default_factory=lambda: defaultdict(list))

    def add_name(self, name: Name) -> None:
        if name.words:
            self.names[name.words[0]].append(name)


def read_stored(session: Session) -> Stored:
    stored = Stored()
    for claim_id, url in session.execute(select(SourceArticle.claim_id, SourceArticle.url)):
        key = article_key(url)
        if key is not None:
            stored.tracked.setdefault(key, claim_id)
    for trial_id, url in session.execute(
        select(ArticleLead.registry_trial_id, ArticleLead.url).order_by(ArticleLead.id)
    ):
        key = article_key(url)
        if key is not None and trial_id not in stored.searched[key]:
            stored.searched[key].append(trial_id)
    for claim_id, name, synonyms in session.execute(
        select(Entity.claim_id, Entity.name, Entity.synonyms)
        .where(Entity.type == EntityType.INTERVENTION)
        .order_by(Entity.claim_id)
    ):
        for known in dict.fromkeys(words_of(text) for text in (name, *synonyms)):
            stored.add_name(Name(known, CLAIM, claim_id))
    for trial_id, name, indication in session.execute(
        select(RegistryTrial.id, RegistryTrial.search_name, RegistryTrial.search_indication)
        .where(RegistryTrial.search_name.is_not(None), RegistryTrial.search_indication.is_not(None))
        .order_by(RegistryTrial.id)
    ):
        named = words_of(name or "")
        # The indication's words that are not also the name's. A trial named by its own
        # disease, as a vaccine is, has none: its name alone in a title says nothing
        # about the trial, so it is not linked by title.
        beside = frozenset(words_of(indication or "")) - frozenset(named)
        if beside:
            stored.add_name(Name(named, REGISTRY_TRIAL, trial_id, beside))
    return stored


def links_for(lead: LinkLead, stored: Stored, most: int) -> list[tuple[str, int, str]]:
    """The stored records a lead is linked to, each with its reason, strongest first:
    trials the news search found this address for, then claims and trials its title
    names. A name matches only as whole words, and a trial only when a word of its
    indication is in the title too."""
    found: list[tuple[str, int, str]] = [
        (REGISTRY_TRIAL, trial_id, FOUND_BY_NEWS_SEARCH)
        for trial_id in stored.searched.get(lead.url_key, [])
    ]
    title = words_of(lead.title)
    in_title = frozenset(title)
    named: list[tuple[str, int, str]] = []
    for place, word in enumerate(title):
        for name in stored.names.get(word, ()):
            if title[place : place + len(name.words)] != name.words:
                continue
            if name.record_kind == CLAIM:
                named.append((CLAIM, name.record_id, TITLE_NAMES_CLAIM))
            elif name.beside & in_title:
                named.append((REGISTRY_TRIAL, name.record_id, TITLE_NAMES_TRIAL))
    # Claims before trials, each in the order of its record, and each link once.
    named.sort(key=lambda link: (link[0] != CLAIM, link[1]))
    return list(dict.fromkeys([*found, *named]))[:most]


class LinkScreen:
    name = "link_screen"
    # 2: a trial is linked by title only on a word of its indication that is not also a
    # word of its name (found on the first real run, 2026-11-14).
    version = 2
    record_kind = "link_lead"
    model = LinkLead
    source = NO_SOURCE
    requests_per_record = 0
    # Screening costs nothing per lead, so many are saved in one transaction.
    batch_size = 500

    def __init__(self, links_max: int = 10) -> None:
        self.links_max = links_max
        self._stored: Stored | None = None
        self._lock = threading.Lock()

    def scope(self) -> ColumnElement[bool]:
        """Every link lead is screened."""
        return true()

    def inputs(self, record: LinkLead) -> dict[str, Any]:
        return {"key": record.url_key, "title": record.title}

    def stored(self, session: Session) -> Stored:
        """What the database holds, read once for a run. A claim or an article lead
        added while the run is under way is seen by the next run; reading a lead checks
        again whether its article has become tracked."""
        with self._lock:
            if self._stored is None:
                self._stored = read_stored(session)
            return self._stored

    def run(self, session: Session, record: LinkLead, client: Any) -> WorkOutcome:
        stored = self.stored(session)
        session.execute(delete(LinkLeadLink).where(LinkLeadLink.link_lead_id == record.id))
        # The outlet list may have grown since the lead was loaded.
        record.outlet_kind = kind_of(record.outlet)
        claim_id = stored.tracked.get(record.url_key)
        if claim_id is not None:
            record.screen_outcome = ScreenOutcome.ALREADY_TRACKED
            session.add(
                LinkLeadLink(
                    link_lead_id=record.id,
                    record_kind=CLAIM,
                    record_id=claim_id,
                    reason="the address is one of the claim's source articles",
                )
            )
        elif record.outlet_kind is OutletKind.UNKNOWN:
            record.screen_outcome = ScreenOutcome.UNLISTED_OUTLET
        else:
            record.screen_outcome = ScreenOutcome.IN_SCOPE
            session.add_all(
                LinkLeadLink(
                    link_lead_id=record.id, record_kind=kind, record_id=record_id, reason=reason
                )
                for kind, record_id, reason in links_for(record, stored, self.links_max)
            )
        session.flush()
        return WorkOutcome.DONE

    def run_many(
        self, session: Session, records: Sequence[LinkLead], client: Any
    ) -> list[WorkOutcome]:
        return [self.run(session, record, client) for record in records]
