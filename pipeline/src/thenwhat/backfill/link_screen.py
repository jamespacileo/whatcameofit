"""The screening step: what rules and stored data alone say about a link lead.
Behavior: openspec lead-screening.

It sends no request and calls no model. It decides whether a lead goes on to triage,
and records which claims and registry trials the database already holds for it. A link
is a candidate: it approves nothing and changes no claim, match or status.
"""

import threading
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, delete, func, select, true
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.backfill.trial_terms import (
    CODE,
    NOT_A_CODE,
    REGISTRY_NUMBER,
    acronym_words,
    code_key,
    codes_of,
    condition_words,
    other_names_of,
    words_of,
)
from thenwhat.db.models import (
    ArticleLead,
    Entity,
    LinkLead,
    LinkLeadLink,
    RegistryTrial,
    SourceArticle,
)
from thenwhat.domain import EntityType, OutletKind, ScreenOutcome, WorkOutcome
from thenwhat.work.steps import NO_SOURCE

CLAIM = "claim"
REGISTRY_TRIAL = "registry_trial"

FOUND_BY_NEWS_SEARCH = "the news search found this address for the trial"
TITLE_NAMES_CLAIM = "the title names the claim's intervention"
TITLE_NAMES_TRIAL = "the title names the trial's intervention and its indication"
GIVES_NUMBER = "the title or the address gives the trial's registry number"
CODE_AND_CONDITION = "the title holds a development code of the trial and a word of its condition"
CODE_ALONE = "the title holds a development code of the trial"
ACRONYM_AND_CONDITION = "the title holds the trial's acronym and a word of its condition"
OTHER_NAME_AND_CONDITION = (
    "the title holds another name of the trial's intervention and a word of its condition"
)

# How much a link to a trial says, strongest first. Measured on 2026-11-17 on forty links
# judged from headline and outlet (openspec trial-first-route, design.md):
# - exact: the registry number itself. It names one registry record.
# - strong: a development code beside a word of the trial's condition. Eight of eight
#   named the right treatment for the right condition.
# - named: a code with no word of the condition (three of four the right treatment), or
#   an acronym that carries a number beside a word of the condition (too few to judge).
# - candidate: the intervention's name, or another of its names, beside a word of the
#   condition. One of sixteen named the right treatment for the right condition.
# Only an exact or a strong link is enough for a held lead to be read; the others order
# what is read. No link says which trial a report is about.
EXACT = "exact"
STRONG = "strong"
NAMED = "named"
CANDIDATE = "candidate"
STRENGTH_TO_READ = (EXACT, STRONG)
STRENGTHS = {
    FOUND_BY_NEWS_SEARCH: CANDIDATE,
    TITLE_NAMES_TRIAL: CANDIDATE,
    GIVES_NUMBER: EXACT,
    CODE_AND_CONDITION: STRONG,
    CODE_ALONE: NAMED,
    ACRONYM_AND_CONDITION: NAMED,
    OTHER_NAME_AND_CONDITION: CANDIDATE,
}
# An acronym more trials than this share is a word, not one study's name.
ACRONYM_MAX_TRIALS = 3


@dataclass(frozen=True, slots=True)
class Link:
    """A stored record a lead is linked to, the reason, and for a trial how much the
    link says, the term it was made on and the condition word found beside it."""

    record_kind: str
    record_id: int
    reason: str
    strength: str | None = None
    term: str | None = None
    beside: str | None = None


@dataclass(slots=True)
class Term:
    """A term of stored trials to look for in a title: a code, an acronym or another
    name, as written, and the trials that carry it."""

    written: str
    reason: str
    words: tuple[str, ...] = ()
    trial_ids: list[int] = field(default_factory=list)


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

    # Development codes by their key, and acronyms and other names by their first word.
    codes: dict[str, Term] = field(default_factory=dict)
    terms: dict[str, list[Term]] = field(default_factory=lambda: defaultdict(list))
    # The telling words of the conditions of each trial that carries a term.
    conditions: dict[int, frozenset[str]] = field(default_factory=dict)

    def add_name(self, name: Name) -> None:
        if name.words:
            self.names[name.words[0]].append(name)

    def add_trial_terms(self, rows: Iterable[Any]) -> None:
        """Gather the terms of stored trials: each row is a trial's id, acronym,
        interventions, conditions and the name it is searched by. An acronym or another
        name that holds a word of any trial's condition is a word of the subject, not a
        name, and is left out; so is an acronym that several trials share."""
        acronyms: dict[tuple[str, ...], Term] = {}
        others: dict[tuple[str, ...], Term] = {}
        every_condition_word: set[str] = set()
        for trial_id, acronym, interventions, conditions, search_name in rows:
            beside = condition_words(conditions or [])
            every_condition_word |= beside
            carries = False
            for code in codes_of(interventions or []):
                term = self.codes.setdefault(code_key(code), Term(code, CODE_ALONE))
                term.trial_ids.append(trial_id)
                carries = True
            shaped = acronym_words(acronym)
            if shaped is not None:
                found = acronyms.setdefault(
                    shaped, Term(acronym or "", ACRONYM_AND_CONDITION, shaped)
                )
                found.trial_ids.append(trial_id)
                carries = True
            for name in other_names_of(interventions or [], search_name):
                words = words_of(name)
                found = others.setdefault(words, Term(name, OTHER_NAME_AND_CONDITION, words))
                found.trial_ids.append(trial_id)
                carries = True
            if carries and beside:
                self.conditions[trial_id] = beside
        for words, term in acronyms.items():
            if len(term.trial_ids) <= ACRONYM_MAX_TRIALS and not every_condition_word & set(words):
                self.terms[words[0]].append(term)
        for words, term in others.items():
            if not every_condition_word & set(words):
                self.terms[words[0]].append(term)


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
    stored.add_trial_terms(
        session.execute(
            select(
                RegistryTrial.id,
                RegistryTrial.acronym,
                RegistryTrial.interventions,
                RegistryTrial.conditions,
                RegistryTrial.search_name,
            )
            .order_by(RegistryTrial.id)
            .execution_options(yield_per=5000)
        )
    )
    return stored


def numbers_in(lead: LinkLead) -> list[str]:
    """The registry numbers a lead's title or address gives, in upper case, each once."""
    found = REGISTRY_NUMBER.findall(f"{lead.title} {lead.url}")
    return list(dict.fromkeys(number.upper() for number in found))


def term_links(lead: LinkLead, stored: Stored, most: int) -> list[Link]:
    """The trials a lead is linked to on a term of theirs, strongest first.

    A development code beside a word of a trial's condition is a strong link to every
    stored trial that carries both: a headline cannot choose among them, so none is
    left out and none is marked as the one reported. Every other link is kept for at
    most `most` trials of each term."""
    title = words_of(lead.title)
    in_title = frozenset(title)

    def beside(trial_id: int, name: tuple[str, ...] = ()) -> str | None:
        found = (stored.conditions.get(trial_id, frozenset()) - frozenset(name)) & in_title
        return min(found) if found else None

    strong: list[Link] = []
    named: list[Link] = []
    candidates: list[Link] = []
    for match in CODE.finditer(lead.title):
        term = stored.codes.get(code_key(match.group(0)))
        if term is None or match.group(1).lower() in NOT_A_CODE:
            continue
        with_condition = [(one, word) for one in term.trial_ids if (word := beside(one))]
        strong += [
            Link(REGISTRY_TRIAL, one, CODE_AND_CONDITION, STRONG, term.written, word)
            for one, word in with_condition
        ]
        if not with_condition:
            named += [
                Link(REGISTRY_TRIAL, one, CODE_ALONE, NAMED, term.written)
                for one in term.trial_ids[:most]
            ]
    for place, first in enumerate(title):
        for term in stored.terms.get(first, ()):
            if title[place : place + len(term.words)] != term.words:
                continue
            found = [
                Link(REGISTRY_TRIAL, one, term.reason, STRENGTHS[term.reason], term.written, word)
                for one in term.trial_ids
                if (word := beside(one, term.words))
            ][:most]
            (named if term.reason == ACRONYM_AND_CONDITION else candidates).extend(found)
    return [*strong, *named, *candidates]


def links_for(
    lead: LinkLead, stored: Stored, most: int, numbered: Sequence[int] = ()
) -> list[Link]:
    """The stored records a lead is linked to, each with its reason, strongest first:
    the trials whose registry number it gives (`numbered`), those it names by a code
    beside their condition, trials the news search found this address for, then the
    claims and trials its title names, and last the weaker links on a trial's terms.

    A name matches only as whole words, and a trial only when a word of its condition
    is in the title too, a code excepted. The present link on the intervention's name
    is kept as it was, with the same limit; exact and strong links are never limited."""
    found = [
        Link(REGISTRY_TRIAL, trial_id, FOUND_BY_NEWS_SEARCH, CANDIDATE)
        for trial_id in stored.searched.get(lead.url_key, [])
    ]
    title = words_of(lead.title)
    in_title = frozenset(title)
    named: list[Link] = []
    for place, word in enumerate(title):
        for name in stored.names.get(word, ()):
            if title[place : place + len(name.words)] != name.words:
                continue
            if name.record_kind == CLAIM:
                named.append(Link(CLAIM, name.record_id, TITLE_NAMES_CLAIM))
            elif name.beside & in_title:
                named.append(
                    Link(
                        REGISTRY_TRIAL,
                        name.record_id,
                        TITLE_NAMES_TRIAL,
                        CANDIDATE,
                        " ".join(name.words),
                        min(name.beside & in_title),
                    )
                )
    # Claims before trials, each in the order of its record.
    named.sort(key=lambda link: (link.record_kind != CLAIM, link.record_id))
    present = _once([*found, *named])[:most]
    on_terms = term_links(lead, stored, most)
    sure = [Link(REGISTRY_TRIAL, trial_id, GIVES_NUMBER, EXACT) for trial_id in numbered]
    sure += [link for link in on_terms if link.strength == STRONG]
    weaker = [link for link in on_terms if link.strength != STRONG]
    return _once([*sure, *present, *weaker])


def _once(links: Sequence[Link]) -> list[Link]:
    """Each link once for a record and a reason, the first kept."""
    kept: dict[tuple[str, int, str], Link] = {}
    for link in links:
        kept.setdefault((link.record_kind, link.record_id, link.reason), link)
    return list(kept.values())


class LinkScreen:
    name = "link_screen"
    # 2: a trial is linked by title only on a word of its indication that is not also a
    # word of its name (found on the first real run, 2026-11-14).
    # 3: a trial is also linked on its registry number, a development code, an acronym
    # that carries a number and its interventions' other names, each link with its
    # strength, its term and the condition word beside it. Every lead is screened again,
    # so the link table describes one corpus (openspec trial-first-route, task 3.1).
    version = 3
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
            numbers = numbers_in(record)
            numbered = (
                list(
                    session.scalars(
                        select(RegistryTrial.id)
                        .where(func.upper(RegistryTrial.external_id).in_(numbers))
                        .order_by(RegistryTrial.id)
                    )
                )
                if numbers
                else []
            )
            session.add_all(
                LinkLeadLink(
                    link_lead_id=record.id,
                    record_kind=link.record_kind,
                    record_id=link.record_id,
                    reason=link.reason,
                    strength=link.strength,
                    term=link.term,
                    beside=link.beside,
                )
                for link in links_for(record, stored, self.links_max, numbered)
            )
        session.flush()
        return WorkOutcome.DONE

    def run_many(
        self, session: Session, records: Sequence[LinkLead], client: Any
    ) -> list[WorkOutcome]:
        return [self.run(session, record, client) for record in records]
