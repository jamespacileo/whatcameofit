"""What a stored trial's registry record itself lists: the papers it names and the links
it gives. Read by rule from the stored record alone, asking no source.
Behavior: openspec trial-coverage, "Papers the registry record names" and "Links the
registry record gives".

A record lists a paper with one of three kinds (docs/sources.md): RESULT, which the
sponsor listed as reporting the study's results; DERIVED, which the registry filled in
from PubMed and says may or may not be about the study; and BACKGROUND, which is not the
trial's paper at all. The first two are kept apart from each other and from the third,
which is only counted.

How a listed paper becomes a paper record: it does not, here. This module names the
paper by the same rule and the same type a claim's trial uses
(`events.trial_facts.results_papers_of`), so the one store of paper records
(`events.paper_records.keep_paper`: one request to the paper index a paper, the record
reduced, "not held" kept as an answer) takes it from either caller and holds it once.
A paper named here is attached to its trial by the registry's own listing. It is not a
match, has no score, is no evidence event, and is no related paper of any claim: only
the literature search's scored match makes one of those.
"""

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import BackfillError
from thenwhat.backfill.outlet_kinds import kind_of, outlet_of
from thenwhat.backfill.trial_sets import SETS
from thenwhat.db.models import RegistryTrial
from thenwhat.domain import OutletKind
from thenwhat.events.trial_facts import ResultsPaper, results_papers_of

BACKGROUND = "BACKGROUND"
LISTED_BY_SPONSOR = "listed_by_sponsor"
LINKED_BY_REGISTRY = "linked_by_registry"


class UnknownSet(BackfillError):
    """No set of stored trials has the name given."""


def rule_of(name: str) -> Any:
    """The rule of a named set of stored trials. Refuses a name it does not know with
    the list of sets."""
    if name not in SETS:
        raise UnknownSet(f"No set of stored trials is named '{name}'. Sets: {', '.join(SETS)}.")
    return SETS[name]


@dataclass(frozen=True, slots=True)
class Link:
    url: str
    # The outlet's domain, and whether it is on a list of outlets.
    domain: str
    listed: bool


@dataclass(frozen=True, slots=True)
class TrialReferences:
    """What one record lists. A paper is named once, by its PubMed number; one the
    sponsor listed and the registry also linked is the sponsor's."""

    papers: tuple[ResultsPaper, ...] = ()
    # Papers listed as background: counted, never named.
    background: int = 0
    links: tuple[Link, ...] = ()

    @property
    def listed_by_sponsor(self) -> tuple[str, ...]:
        return tuple(p.pubmed_id for p in self.papers if p.listed == LISTED_BY_SPONSOR)

    @property
    def linked_by_registry(self) -> tuple[str, ...]:
        return tuple(p.pubmed_id for p in self.papers if p.listed == LINKED_BY_REGISTRY)


def references_of(study: dict[str, Any]) -> TrialReferences:
    """What a registry record lists, from the record as stored. The citation text of a
    reference names authors and is not read."""
    protocol = study.get("protocolSection")
    module = protocol.get("referencesModule") if isinstance(protocol, dict) else None
    if not isinstance(module, dict):
        return TrialReferences()
    references = [one for one in module.get("references") or [] if isinstance(one, dict)]
    links: dict[str, Link] = {}
    for given in module.get("seeAlsoLinks") or []:
        url = str(given.get("url") or "").strip() if isinstance(given, dict) else ""
        domain = outlet_of(url) if url.startswith(("http://", "https://")) else ""
        if domain and url not in links:
            links[url] = Link(url, domain, kind_of(domain) is not OutletKind.UNKNOWN)
    return TrialReferences(
        papers=results_papers_of(study),
        background=sum(1 for one in references if one.get("type") == BACKGROUND),
        links=tuple(links.values()),
    )


def references_in(session: Session, set_name: str) -> Iterator[tuple[str, TrialReferences]]:
    """Each trial of a named set whose stored record has a references section, by its
    registry identifier, with what the record lists. One query; no source is asked."""
    module = RegistryTrial.raw_payload["protocolSection"]["referencesModule"]
    rows = session.execute(
        select(RegistryTrial.external_id, module)
        .where(rule_of(set_name)(), module.is_not(None))
        .order_by(RegistryTrial.external_id)
        .execution_options(yield_per=2000)
    )
    for external_id, references in rows:
        yield external_id, references_of({"protocolSection": {"referencesModule": references}})


@dataclass(slots=True)
class ReferenceCount:
    name: str
    trials: int = 0
    # Trials whose record lists at least one paper of the kind.
    with_sponsor_paper: int = 0
    with_registry_paper: int = 0
    with_either: int = 0
    with_background_only: int = 0
    with_link: int = 0
    with_listed_link: int = 0
    # Papers, each counted once however many trials list it.
    sponsor_papers: int = 0
    registry_papers: int = 0
    links: int = 0
    listed_links: int = 0
    domains: Counter[str] = field(default_factory=Counter)


def count_references(session: Session, set_name: str) -> ReferenceCount:
    """How many trials of a set list what, and how many papers and links that is."""
    counted = ReferenceCount(set_name)
    counted.trials = (
        session.scalar(select(func.count()).select_from(RegistryTrial).where(rule_of(set_name)()))
        or 0
    )
    sponsor: set[str] = set()
    registry: set[str] = set()
    for _, listed in references_in(session, set_name):
        by_sponsor, by_registry = listed.listed_by_sponsor, listed.linked_by_registry
        counted.with_sponsor_paper += bool(by_sponsor)
        counted.with_registry_paper += bool(by_registry)
        counted.with_either += bool(listed.papers)
        counted.with_background_only += bool(listed.background and not listed.papers)
        counted.with_link += bool(listed.links)
        counted.with_listed_link += any(link.listed for link in listed.links)
        sponsor.update(by_sponsor)
        registry.update(by_registry)
        counted.links += len(listed.links)
        counted.listed_links += sum(link.listed for link in listed.links)
        counted.domains.update(link.domain for link in listed.links)
    counted.sponsor_papers = len(sponsor)
    # A paper one trial's sponsor listed and another trial's record links is the
    # sponsor's once.
    counted.registry_papers = len(registry - sponsor)
    return counted
