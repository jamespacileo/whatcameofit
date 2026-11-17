"""A claim's clinical categories, derived from the records of its approved trials and
papers. Pure: no database, network, clock or model.

From a trial: the MeSH descriptors the registry lists for the trial's conditions. The
broader terms the registry lists beside them are not the claim's own categories; what is
broader comes from the tree.

From a paper: the subject headings it is indexed under as a major topic, when the
descriptor sits in the tree of diseases or of mental disorders. The index gives a heading
by its descriptor's label, so it is a category only once the vocabulary holds a
descriptor with that label; until then it is reported as not yet read.

From the claim's own condition: the MeSH descriptor that was found by the condition's
name and read, by the terms step's decision, as the claim's condition itself, when that
reading is approved (openspec knowledge-cards). It is a model's reading, so its score
goes with it wherever the category is shown. A term read as broader is not a category:
the tree already places what is broader.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.sources.mesh import IDENTIFIER


@dataclass(frozen=True, slots=True)
class Source:
    # The site words each.
    kind: Literal["trial", "paper", "term"]
    # The trial's or the paper's identifier; for a term, the descriptor's own.
    identifier: str
    # The score of the reading that made the term the claim's condition. None for a
    # trial or a paper, which state their terms themselves.
    score: float | None = None


@dataclass(frozen=True, slots=True)
class CheckedTerm:
    """An approved reading of a MeSH descriptor as the claim's own condition."""

    identifier: str
    label: str
    score: float | None


@dataclass(frozen=True, slots=True)
class ClaimRecords:
    """What a claim's clinical categories are derived from: each approved trial's
    registry record and each paper's index record, by identifier, and the checked terms
    of its condition."""

    trials: tuple[tuple[str, Mapping[str, Any]], ...] = ()
    papers: tuple[tuple[str, Mapping[str, Any]], ...] = ()
    terms: tuple[CheckedTerm, ...] = ()


@dataclass(frozen=True, slots=True)
class Category:
    identifier: str
    # The descriptor's label as its source gave it; the vocabulary's own once it is read.
    label: str
    sources: tuple[Source, ...]


@dataclass(frozen=True, slots=True)
class Derived:
    categories: tuple[Category, ...]
    # Paper headings that are major topics and whose descriptor is not stored yet, so
    # whether they are conditions is not known.
    unread_headings: tuple[str, ...]


def trial_terms(payload: Mapping[str, Any]) -> list[tuple[str, str]]:
    """The MeSH descriptors a trial's registry record lists for its conditions, as
    identifier and label. Its ancestors are not read."""
    module = payload.get("derivedSection", {}).get("conditionBrowseModule", {})
    return [
        (entry["id"], str(entry.get("term") or ""))
        for entry in module.get("meshes", [])
        if isinstance(entry, Mapping)
        and isinstance(entry.get("id"), str)
        and IDENTIFIER.match(entry["id"])
        and entry["id"].startswith("D")
    ]


def _major(heading: Mapping[str, Any]) -> bool:
    if heading.get("majorTopic_YN") == "Y":
        return True
    qualifiers = heading.get("meshQualifierList")
    listed = qualifiers.get("meshQualifier") if isinstance(qualifiers, Mapping) else None
    return any(
        isinstance(qualifier, Mapping) and qualifier.get("majorTopic_YN") == "Y"
        for qualifier in (listed if isinstance(listed, list) else [])
    )


def paper_major_headings(payload: Mapping[str, Any]) -> list[str]:
    """The labels of the subject headings a paper's index record marks as a major topic,
    on the heading itself or on one of its qualifiers."""
    headings = payload.get("meshHeadingList")
    listed = headings.get("meshHeading") if isinstance(headings, Mapping) else None
    return [
        heading["descriptorName"]
        for heading in (listed if isinstance(listed, list) else [])
        if isinstance(heading, Mapping)
        and isinstance(heading.get("descriptorName"), str)
        and _major(heading)
    ]


def derive(
    trials: Iterable[tuple[str, Mapping[str, Any]]],
    papers: Iterable[tuple[str, Mapping[str, Any]]],
    vocabulary: Vocabulary,
    terms: Iterable[CheckedTerm] = (),
) -> Derived:
    """The categories the records give, by label, each naming every record that gave it.
    `trials` and `papers` are each record's identifier with its stored payload; a record
    given twice counts once. `terms` are the approved readings of the claim's own
    condition; one that is not a descriptor is no category."""
    labels: dict[str, str] = {}
    sources: dict[str, set[Source]] = {}
    unread: set[str] = set()

    def give(identifier: str, label: str, source: Source) -> None:
        held = vocabulary.get(identifier)
        labels[identifier] = held.label if held and held.label else labels.get(identifier, label)
        sources.setdefault(identifier, set()).add(source)

    for trial_id, payload in trials:
        for identifier, label in trial_terms(payload):
            give(identifier, label, Source("trial", trial_id))
    for paper_id, payload in papers:
        for label in paper_major_headings(payload):
            descriptor = vocabulary.labelled(label)
            if descriptor is None:
                unread.add(label)
            elif descriptor.is_condition:
                give(descriptor.identifier, descriptor.label, Source("paper", paper_id))
    for term in terms:
        if IDENTIFIER.match(term.identifier) and term.identifier.startswith("D"):
            give(term.identifier, term.label, Source("term", term.identifier, term.score))

    return Derived(
        categories=tuple(
            Category(
                identifier,
                labels[identifier],
                tuple(sorted(sources[identifier], key=lambda one: (one.kind, one.identifier))),
            )
            for identifier in sorted(labels, key=lambda one: (labels[one].casefold(), one))
        ),
        unread_headings=tuple(sorted(unread, key=str.casefold)),
    )
