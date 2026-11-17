"""The part of the MeSH tree the stored descriptor records give. Pure: no database,
network, clock or model.

The hierarchy is NLM's own. A descriptor's record names the descriptors directly broader
than it and its tree numbers; a descriptor with several tree numbers sits under each of
its broader descriptors. Nothing is taken from the trial registry's flat ancestor list.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from thenwhat.sources.mesh import IDENTIFIER, RESOURCE, broader_descriptors, tree_numbers

# Local lookup metadata kept beside the descriptor records, under the same source: what a
# lookup answered that is not itself a record. Its key never matches a MeSH identifier,
# and its payload says which lookup it was, so it is never read as a descriptor.
LABEL_CHECK = "lookup:descriptor-label:"
DESCRIPTOR_CHECK = "lookup:descriptor:"

# The trees a paper's subject heading must sit in to be a condition: Diseases, and
# Mental Disorders within Psychiatry and Psychology.
CONDITION_TREES = ("C", "F03")


@dataclass(frozen=True, slots=True)
class Descriptor:
    identifier: str
    label: str
    tree_numbers: tuple[str, ...]
    broader: tuple[str, ...]
    # The year of the vocabulary the record was read from.
    year: str | None

    @property
    def is_top(self) -> bool:
        """At the top of a tree: no descriptor is broader."""
        return not self.broader

    @property
    def is_condition(self) -> bool:
        return any(number.startswith(CONDITION_TREES) for number in self.tree_numbers)


def _label(term: Mapping[str, Any]) -> str:
    value = term.get("label")
    if isinstance(value, Mapping):
        value = value.get("@value")
    return " ".join(value.split()) if isinstance(value, str) else ""


def _key(label: str) -> str:
    return " ".join(label.split()).casefold()


def label_key(label: str) -> str:
    """The stored key of an exact-label lookup: the label as MeSH compares it."""
    return LABEL_CHECK + _key(label)


def describe(identifier: str, payload: Mapping[str, Any]) -> Descriptor:
    """A stored descriptor record as the tree needs it."""
    term = payload.get("term") or {}
    address = RESOURCE.match(str(term.get("@id") or ""))
    return Descriptor(
        identifier=identifier,
        label=_label(term),
        tree_numbers=tree_numbers(dict(payload)),
        broader=broader_descriptors(dict(payload)),
        year=address.group(1) if address else None,
    )


class Vocabulary:
    """The stored descriptors, by identifier and by label, with what is broader."""

    def __init__(
        self, records: Iterable[tuple[str, Mapping[str, Any]]], *, year: str | None = None
    ) -> None:
        self._by_id: dict[str, Descriptor] = {}
        # Label key to the year whose exact-label lookup found no descriptor.
        self._unlabelled: set[str] = set()
        self._checked: dict[str, bool] = {}
        for identifier, payload in records:
            if identifier.startswith(LABEL_CHECK):
                if payload.get("year") == year:
                    self._unlabelled.add(identifier.removeprefix(LABEL_CHECK))
            elif identifier.startswith(DESCRIPTOR_CHECK):
                if payload.get("year") == year:
                    self._checked[identifier.removeprefix(DESCRIPTOR_CHECK)] = payload["held"]
            # Only descriptors sit in the tree; a supplementary record (C...) does not.
            elif IDENTIFIER.match(identifier) and identifier.startswith("D"):
                self._by_id[identifier] = describe(identifier, payload)
        self._by_label = {_key(d.label): d.identifier for d in self._by_id.values() if d.label}

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, identifier: str) -> Descriptor | None:
        return self._by_id.get(identifier)

    def labelled(self, label: str) -> Descriptor | None:
        """The descriptor whose own label equals this one, whatever its case."""
        identifier = self._by_label.get(_key(label))
        return self._by_id[identifier] if identifier else None

    def label_absent(self, label: str) -> bool:
        """Whether an exact lookup in this year's vocabulary ruled out the heading."""
        return _key(label) in self._unlabelled

    def current(self, identifier: str, year: str) -> bool | None:
        """True if present this year, false if checked and absent, otherwise unread."""
        held = self.get(identifier)
        if held is not None and held.year == year:
            return True
        return self._checked.get(identifier)

    def hierarchy(self, identifiers: Iterable[str]) -> tuple[dict[str, set[str]], set[str]]:
        """Reached edges and unread descriptors, following each placement up its own branch."""
        parents: dict[str, set[str]] = {}
        missing: set[str] = set()
        waiting: list[tuple[str, str]] = []
        for identifier in identifiers:
            held = self.get(identifier)
            if held is None:
                missing.add(identifier)
            else:
                parents.setdefault(identifier, set())
                waiting.extend((identifier, number) for number in held.tree_numbers)
        seen: set[tuple[str, str]] = set()
        while waiting:
            placement = waiting.pop()
            if placement in seen:
                continue
            seen.add(placement)
            identifier, number = placement
            unresolved: set[str] = set()
            placed = False
            for broader in self._by_id[identifier].broader:
                parent = self.get(broader)
                if parent is None:
                    unresolved.add(broader)
                    continue
                for prefix in parent.tree_numbers:
                    if number.startswith(prefix + "."):
                        parents[identifier].add(broader)
                        parents.setdefault(broader, set())
                        waiting.append((broader, prefix))
                        placed = True
            if not placed and "." in number:
                missing.update(unresolved)
        return parents, missing

    def above(self, identifier: str) -> frozenset[str]:
        return self.at_or_above(identifier) - {identifier}

    def at_or_above(self, identifier: str) -> frozenset[str]:
        parents, _ = self.hierarchy([identifier])
        return frozenset(parents) | {identifier}

    def missing(self, identifiers: Iterable[str]) -> list[str]:
        """The descriptors not stored that the tree above these needs, these included."""
        return sorted(self.hierarchy(identifiers)[1])

    def years(self) -> list[str]:
        """Each MeSH year the stored descriptors were read from, oldest first. A lookup
        that found nothing is no descriptor, so its year is not one of these."""
        return sorted({d.year for d in self._by_id.values() if d.year})
