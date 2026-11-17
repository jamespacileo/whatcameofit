"""Clinical categories against the database: reading the MeSH records they need, and the
reports. Behavior: openspec clinical-classification.

Categories themselves are never stored. Each function here gathers a claim's records the
way the export does and derives from them, so a report and the export always agree.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.verticals import GROUPS, VERTICAL_GROUPS, VERTICALS
from thenwhat.clinical.categories import Category, ClaimRecords, Derived, derive
from thenwhat.clinical.topics import (
    TOPIC_DESCRIPTORS,
    DerivedTopic,
    configuration_problems,
    derived_topics,
    mapped_descriptors,
    uncovered,
)
from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.db.models import Claim, Entity, TermRecord
from thenwhat.domain import EntityType
from thenwhat.export.build import claim_clinical_records
from thenwhat.export.records import PostgresRecords, Records
from thenwhat.sources.base import SourceRecord


class MeshSource(Protocol):
    name: str

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None: ...

    def descriptor_labelled(self, label: str) -> str | None: ...


def stored_vocabulary(records: Records) -> Vocabulary:
    return Vocabulary((record.external_id, record.payload) for record in records.mesh_records())


@dataclass(frozen=True, slots=True)
class ClaimClinical:
    derived: Derived
    # Descriptors the tree above the categories needs and the vocabulary does not hold.
    missing: tuple[str, ...]

    @property
    def read(self) -> bool:
        """Whether every record the categories need has been read."""
        return not self.missing and not self.derived.unread_headings

    @property
    def categories(self) -> tuple[Category, ...]:
        return self.derived.categories


def _placed(given: ClaimRecords, vocabulary: Vocabulary) -> ClaimClinical:
    derived = derive(given.trials, given.papers, vocabulary, given.terms)
    missing = vocabulary.missing(category.identifier for category in derived.categories)
    return ClaimClinical(derived, tuple(missing))


def clinical_of(records: Records, claim: Claim, vocabulary: Vocabulary) -> ClaimClinical:
    """The claim's clinical categories now, and what is still to be read for them."""
    return _placed(claim_clinical_records(records, claim), vocabulary)


# --- reading the tree ------------------------------------------------------------------


@dataclass(slots=True)
class TreeRun:
    read: int = 0
    # Paper headings no descriptor's label equals, so they are never categories.
    unknown_headings: list[str] = field(default_factory=list)
    # Descriptors the vocabulary no longer holds.
    retired: list[str] = field(default_factory=list)


def _keep(session: Session, record: SourceRecord) -> None:
    kept = session.get(TermRecord, (record.source_name, record.external_id))
    if kept is None:
        kept = TermRecord(source_name=record.source_name, external_id=record.external_id)
        session.add(kept)
    kept.url = record.url
    kept.payload = record.payload
    kept.fetched_at = record.fetched_at
    session.flush()


def read_tree(
    session: Session,
    source: MeshSource,
    claims: Sequence[Claim],
    *,
    mapping: Mapping[str, tuple[tuple[str, str], ...]] = TOPIC_DESCRIPTORS,
) -> TreeRun:
    """Read and store the MeSH record of every category the claims have, of every
    descriptor the topic mapping names and of each descriptor broader than those, up to
    the top of its tree. A record already stored is not asked for again."""
    records = PostgresRecords(session)
    gathered = [claim_clinical_records(records, claim) for claim in claims]
    run = TreeRun()
    asked: set[str] = set()
    asked_headings: set[str] = set()
    while True:
        vocabulary = stored_vocabulary(records)
        wanted = set(mapped_descriptors(mapping))
        headings: set[str] = set()
        for given in gathered:
            placed = _placed(given, vocabulary)
            wanted.update(category.identifier for category in placed.categories)
            headings.update(placed.derived.unread_headings)
        waiting = [one for one in vocabulary.missing(wanted) if one not in asked]
        for heading in sorted(headings - asked_headings):
            asked_headings.add(heading)
            identifier = source.descriptor_labelled(heading)
            if identifier is None:
                run.unknown_headings.append(heading)
            elif identifier not in vocabulary and identifier not in asked:
                waiting.append(identifier)
        if not waiting:
            return run
        for identifier in waiting:
            if identifier in asked:
                continue
            asked.add(identifier)
            record = source.term(identifier)
            if record is None:
                run.retired.append(identifier)
                continue
            _keep(session, record)
            run.read += 1


# --- the reports -----------------------------------------------------------------------


@dataclass(slots=True)
class Coverage:
    """How many claims have a category, and from what."""

    from_trials: int = 0
    from_papers_only: int = 0
    # Only from the reading of the claim's own condition: a model's, not a record's.
    from_term_only: int = 0
    none: int = 0
    not_read: int = 0


def _kinds(placed: ClaimClinical) -> set[str]:
    return {source.kind for category in placed.categories for source in category.sources}


def coverage(records: Records, claims: Sequence[Claim], vocabulary: Vocabulary) -> Coverage:
    counted = Coverage()
    for claim in claims:
        placed = clinical_of(records, claim, vocabulary)
        if not placed.read:
            counted.not_read += 1
        elif not placed.categories:
            counted.none += 1
        elif _kinds(placed) & {"trial"}:
            counted.from_trials += 1
        elif _kinds(placed) & {"paper"}:
            counted.from_papers_only += 1
        else:
            counted.from_term_only += 1
    return counted


@dataclass(frozen=True, slots=True)
class Disagreement:
    slug: str
    intervention: str
    indication: str
    vertical: str
    topics: tuple[DerivedTopic, ...]
    categories: tuple[Category, ...]


@dataclass(slots=True)
class Comparison:
    """Derived topics against the vertical each claim is filed under."""

    agrees: int = 0
    # Of those that agree, the ones whose categories rest on the reading of the claim's
    # own condition alone. A model read the condition and a model chose the vertical, so
    # their agreeing is weaker evidence than a registry's or an index's.
    agrees_by_term_only: int = 0
    disagreeing: list[Disagreement] = field(default_factory=list)
    # Nothing to compare, by why.
    no_category: int = 0
    no_topic: int = 0
    not_read: int = 0
    several_topics: int = 0
    per_topic: dict[str, int] = field(default_factory=dict)
    # Categories no topic covers: label and identifier, to the number of claims.
    uncovered: dict[tuple[str, str], int] = field(default_factory=dict)

    @property
    def claims(self) -> int:
        return (
            self.agrees + len(self.disagreeing) + self.no_category + self.no_topic + self.not_read
        )


def _intervention(session: Session, claim: Claim) -> str:
    return (
        session.scalar(
            select(Entity.name).where(
                Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
            )
        )
        or ""
    )


def compare(session: Session, claims: Sequence[Claim], vocabulary: Vocabulary) -> Comparison:
    """How each claim's derived topics compare with its vertical. Reads stored records
    only and changes nothing."""
    records = PostgresRecords(session)
    result = Comparison()
    for claim in claims:
        placed = clinical_of(records, claim, vocabulary)
        if not placed.read:
            result.not_read += 1
            continue
        if not placed.categories:
            result.no_category += 1
            continue
        identifiers = [category.identifier for category in placed.categories]
        labels = {category.identifier: category.label for category in placed.categories}
        for identifier in uncovered(identifiers, vocabulary):
            key = (labels[identifier], identifier)
            result.uncovered[key] = result.uncovered.get(key, 0) + 1
        topics = derived_topics(identifiers, vocabulary)
        if not topics:
            result.no_topic += 1
            continue
        for topic in topics:
            result.per_topic[topic.topic] = result.per_topic.get(topic.topic, 0) + 1
        if len(topics) > 1:
            result.several_topics += 1
        if VERTICAL_GROUPS.get(claim.vertical) in {topic.group for topic in topics}:
            result.agrees += 1
            if _kinds(placed) == {"term"}:
                result.agrees_by_term_only += 1
        else:
            result.disagreeing.append(
                Disagreement(
                    slug=claim.slug,
                    intervention=_intervention(session, claim),
                    indication=claim.indication,
                    vertical=claim.vertical,
                    topics=tuple(topics),
                    categories=placed.categories,
                )
            )
    return result


# --- the suggestion shown beside a claim -------------------------------------------------

TREE_FIRST = "run `thenwhat clinical tree`"


def suggestion_line(session: Session, claim: Claim) -> str:
    """One line for the operator: the groups the claim's clinical categories derive and
    the MeSH term behind each, or why there are none. A suggestion changes nothing: only
    the operator changes a vertical (openspec health-areas)."""
    records = PostgresRecords(session)
    vocabulary = stored_vocabulary(records)
    placed = clinical_of(records, claim, vocabulary)
    if not placed.read:
        return (
            "Health area: no suggestion, as the MeSH records of its clinical categories are"
            f" not read yet; {TREE_FIRST}."
        )
    if not placed.categories:
        return "Health area: no suggestion, as its approved trials and papers give no category."
    labels = {category.identifier: category.label for category in placed.categories}
    reasons: dict[str, str] = {}
    for topic in derived_topics(labels, vocabulary):
        covering = vocabulary.get(topic.covered_by)
        reason = labels[topic.category]
        if covering is not None and topic.covered_by != topic.category:
            reason = f"{reason}, under {covering.label}"
        reasons.setdefault(topic.group, reason)
    if not reasons:
        return "Health area: no suggestion, as no topic covers its clinical categories."
    listed = "; ".join(
        f"{GROUPS[group]} (MeSH: {reasons[group]})" for group in GROUPS if group in reasons
    )
    filed = VERTICALS.get(claim.vertical, claim.vertical)
    return f"Health area suggested: {listed}. Filed under: {filed}."


def prepared_line(session: Session, claims: Sequence[Claim]) -> str:
    """One line for `thenwhat prepare`: how many of the claims it handled are filed under
    a group their clinical categories do not derive. Nothing is changed."""
    vocabulary = stored_vocabulary(PostgresRecords(session))
    if configuration_problems(vocabulary):
        return (
            "Clinical categories not compared with verticals: the topic mapping's MeSH"
            f" records are not read; {TREE_FIRST}."
        )
    differing = len(compare(session, claims, vocabulary).disagreeing)
    if not differing:
        return "No claim prepared is filed under a group its clinical categories do not derive."
    filed = (
        "is filed under a group its clinical categories do"
        if differing == 1
        else "are filed under a group their clinical categories do"
    )
    return (
        f"{differing} of the {len(claims)} claims prepared {filed} not derive;"
        " `thenwhat clinical compare --disagreeing` lists them."
    )
