"""Gathering a claim's candidate subject terms by rule. Pure: no database, network,
clock or model. Behavior: openspec knowledge-cards, "Candidate terms are gathered by rule".

A candidate comes from two places only: the terms the trial registry files the claim's
approved trials under, and vocabulary terms whose label equals one of the claim's own
names. A search's near misses are never candidates.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from thenwhat.domain import TermRole

MESH = "mesh"
# The registry files this many of the claim's approved trials under the term.
FILED_BY_REGISTRY = "filed_by_registry"
# The term's label equals this name of the claim.
LABEL_EQUALS_NAME = "label_equals_name"
# Every reason code, in the order they are given.
REASON_CODES = (FILED_BY_REGISTRY, LABEL_EQUALS_NAME)

# Where a stored trial record lists the terms the registry derived for it.
_MODULES = {
    TermRole.CONDITION: "conditionBrowseModule",
    TermRole.INTERVENTION: "interventionBrowseModule",
}


@dataclass(frozen=True, slots=True)
class LabelMatch:
    """A vocabulary term whose label equals a name of the claim."""

    role: TermRole
    identifier: str
    label: str
    # The claim's name the label equals, as the claim writes it.
    name: str


@dataclass(frozen=True, slots=True)
class Candidate:
    role: TermRole
    source_name: str
    identifier: str
    label: str
    reasons: tuple[dict[str, Any], ...]


def _trial_id(payload: Mapping[str, Any]) -> str | None:
    section = payload.get("protocolSection")
    if not isinstance(section, Mapping):
        return None
    identification = section.get("identificationModule")
    number = identification.get("nctId") if isinstance(identification, Mapping) else None
    return number if isinstance(number, str) and number else None


def _filed_under(payload: Mapping[str, Any], role: TermRole) -> dict[str, str]:
    """The terms one trial is filed under for the role, as identifier to label. The
    registry's broader ancestors of those terms are not among them."""
    derived = payload.get("derivedSection")
    module = derived.get(_MODULES[role]) if isinstance(derived, Mapping) else None
    meshes = module.get("meshes") if isinstance(module, Mapping) else None
    found: dict[str, str] = {}
    for entry in meshes if isinstance(meshes, Sequence) else []:
        if not isinstance(entry, Mapping):
            continue
        identifier, label = entry.get("id"), entry.get("term")
        if isinstance(identifier, str) and identifier and isinstance(label, str) and label:
            found.setdefault(identifier, label)
    return found


def gather_candidates(
    *,
    trial_payloads: Iterable[Mapping[str, Any]],
    label_matches: Sequence[LabelMatch],
    limit: int,
) -> list[Candidate]:
    """The claim's candidate terms, at most `limit` of them.

    `trial_payloads` are the stored registry records of the claim's approved trials; a
    trial stored with several of its events counts once. A term the registry files fewer
    than half of those trials under is left out. Terms whose label equals a name come
    first, then terms by the number of trials that carry them, so the cap drops the
    least carried.
    """
    trials: dict[str, Mapping[str, Any]] = {}
    for payload in trial_payloads:
        number = _trial_id(payload)
        if number is not None:
            trials[number] = payload  # the record stored last is the latest

    labels: dict[tuple[TermRole, str], str] = {}
    counts: dict[tuple[TermRole, str], int] = {}
    for payload in trials.values():
        for role in TermRole:
            for identifier, label in _filed_under(payload, role).items():
                labels.setdefault((role, identifier), label)
                counts[(role, identifier)] = counts.get((role, identifier), 0) + 1

    reasons: dict[tuple[TermRole, str], list[dict[str, Any]]] = {}
    for key, count in counts.items():
        if count * 2 >= len(trials):
            reasons[key] = [{"code": FILED_BY_REGISTRY, "trials": count, "of": len(trials)}]
    equal: set[tuple[TermRole, str]] = set()
    for match in label_matches:
        key = (match.role, match.identifier)
        labels.setdefault(key, match.label)
        if key not in equal:
            equal.add(key)
            reasons.setdefault(key, []).append({"code": LABEL_EQUALS_NAME, "name": match.name})

    roles = list(TermRole)
    ordered = sorted(
        reasons,
        key=lambda key: (
            key not in equal,
            -counts.get(key, 0),
            roles.index(key[0]),
            labels[key].casefold(),
            key[1],
        ),
    )
    return [
        Candidate(
            role, MESH, identifier, labels[(role, identifier)], tuple(reasons[(role, identifier)])
        )
        for role, identifier in ordered[: max(limit, 0)]
    ]
