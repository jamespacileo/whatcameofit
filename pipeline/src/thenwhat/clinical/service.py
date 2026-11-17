"""Clinical categories against the database: reading the MeSH records they need, and the
reports. Behavior: openspec clinical-classification.

Categories themselves are never stored. Each function here gathers a claim's records the
way the export does and derives from them, so a report and the export always agree.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.claims.verticals import GROUPS, VERTICAL_GROUPS, VERTICALS
from thenwhat.clinical.categories import (
    Category,
    ClaimRecords,
    Derived,
    derive,
    paper_major_headings,
)
from thenwhat.clinical.topics import (
    TOPIC_DESCRIPTORS,
    DerivedTopic,
    configuration_problems,
    derived_topics,
    mapped_descriptors,
    uncovered,
)
from thenwhat.clinical.vocabulary import DESCRIPTOR_CHECK, Vocabulary, describe, label_key
from thenwhat.db.models import Claim, Entity, TermRecord
from thenwhat.domain import EntityType
from thenwhat.export.build import claim_clinical_records
from thenwhat.export.records import PostgresRecords, Records
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.mesh import BASE


class MeshSource(Protocol):
    """NLM's service as the tree reads it. A source that also has `vocabulary_year`, the
    year of the vocabulary its requests name as a string, has its answers kept for that
    year: a label no descriptor has is not asked again, and a stored descriptor in use is
    read again once that year's vocabulary has not been checked for it. A source without
    it is asked as before and nothing but the records it returns is kept."""

    name: str

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None: ...

    def descriptor_labelled(self, label: str) -> str | None: ...


def stored_vocabulary(records: Records, *, year: str | None = None) -> Vocabulary:
    return Vocabulary(
        ((record.external_id, record.payload) for record in records.mesh_records()),
        year=year or str(datetime.now(UTC).year),
    )


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
    # Of those, the ones a record is still stored for, to the year it was last read from.
    # The record is kept, so the descriptor keeps its last known place in the tree.
    retired_years: dict[str, str] = field(default_factory=dict)


def _keep(session: Session, record: SourceRecord) -> None:
    # Concurrent claim workers often read the same ancestors or paper headings.
    put = insert(TermRecord).values(
        source_name=record.source_name,
        external_id=record.external_id,
        url=record.url,
        payload=record.payload,
        fetched_at=record.fetched_at,
    )
    session.scalars(
        put.on_conflict_do_update(
            index_elements=[TermRecord.source_name, TermRecord.external_id],
            set_={col: getattr(put.excluded, col) for col in ("url", "payload", "fetched_at")},
            where=put.excluded.fetched_at >= TermRecord.fetched_at,
        ).returning(TermRecord),
        execution_options={"populate_existing": True},
    ).all()


def read_tree(
    session: Session,
    source: MeshSource,
    claims: Sequence[Claim],
    *,
    mapping: Mapping[str, tuple[tuple[str, str], ...]] = TOPIC_DESCRIPTORS,
    now: datetime | None = None,
) -> TreeRun:
    """Read and store the MeSH record of every category the claims have, of every
    descriptor the topic mapping names and of each descriptor broader than those, up to
    the top of its tree.

    With a source that names its vocabulary year, what is stored is checked against that
    year: a stored descriptor in use, or in the tree above one, whose record and checks
    are of an earlier year is read again, and kept as it was when the year no longer
    holds it; a paper heading an earlier year's lookup found no descriptor for is looked
    up again. Each such answer is kept, so it is asked once per year. A request that
    fails raises, and nothing of it is kept as an answer."""
    records = PostgresRecords(session)
    gathered = [claim_clinical_records(records, claim) for claim in claims]
    year: str | None = getattr(source, "vocabulary_year", None)
    at = now or datetime.now(UTC)
    run = TreeRun()
    asked: set[str] = set()
    asked_headings: set[str] = set()

    def retired(identifier: str, vocabulary: Vocabulary) -> None:
        if identifier not in run.retired:
            run.retired.append(identifier)
        held = vocabulary.get(identifier)
        if held is not None and held.year:
            run.retired_years[identifier] = held.year

    while True:
        vocabulary = stored_vocabulary(records, year=year)
        wanted = set(mapped_descriptors(mapping))
        headings: set[str] = set()
        labelled: set[str] = set()
        for given in gathered:
            placed = _placed(given, vocabulary)
            wanted.update(category.identifier for category in placed.categories)
            headings.update(placed.derived.unread_headings)
            for heading in placed.derived.unlabelled_headings:
                if heading not in run.unknown_headings:
                    run.unknown_headings.append(heading)
            for _, payload in given.papers:
                for label in paper_major_headings(payload):
                    descriptor = vocabulary.labelled(label)
                    if descriptor is not None:
                        labelled.add(descriptor.identifier)
        parents, missing = vocabulary.hierarchy(wanted)
        candidates = missing | ({*parents, *labelled} if year else set())
        waiting: set[str] = set()
        for identifier in candidates - asked:
            current = vocabulary.current(identifier, year) if year else None
            if current is None:
                waiting.add(identifier)
            elif current is False:
                retired(identifier, vocabulary)
        for heading in sorted(headings):
            key = label_key(heading)
            if key in asked_headings:
                continue
            asked_headings.add(key)
            identifier = source.descriptor_labelled(heading)
            if identifier is None:
                if heading not in run.unknown_headings:
                    run.unknown_headings.append(heading)
                if year is not None:
                    query = urlencode({"label": heading, "match": "exact", "year": year})
                    _keep(
                        session,
                        SourceRecord(
                            source.name,
                            key,
                            f"{BASE}/lookup/descriptor?{query}",
                            {"year": year},
                            at,
                        ),
                    )
            elif identifier in asked:
                continue
            elif identifier not in vocabulary or (
                year is not None and vocabulary.current(identifier, year) is None
            ):
                waiting.add(identifier)
        if not waiting:
            return run
        for identifier in sorted(waiting):
            asked.add(identifier)
            record = source.term(identifier)
            if record is None:
                retired(identifier, vocabulary)
            else:
                _keep(session, record)
                run.read += 1
            if year and (record is None or describe(identifier, record.payload).year != year):
                # A retired or unversioned record cannot itself show when we checked it.
                _keep(
                    session,
                    SourceRecord(
                        source.name,
                        DESCRIPTOR_CHECK + identifier,
                        f"{BASE}/{year}/{identifier}.json",
                        {"year": year, "held": record is not None},
                        at,
                    ),
                )


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
        filed_group = VERTICAL_GROUPS.get(claim.vertical)
        if filed_group in {topic.group for topic in topics}:
            result.agrees += 1
            from_records = (
                category.identifier
                for category in placed.categories
                if any(source.kind in {"trial", "paper"} for source in category.sources)
            )
            if all(
                topic.group != filed_group for topic in derived_topics(from_records, vocabulary)
            ):
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
