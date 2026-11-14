"""Suggesting a claim's group from the MeSH terms of its approved trials.

Advisory only: a suggestion never changes a claim's vertical; the operator chooses.
Behavior: openspec health-areas.

ClinicalTrials.gov derives MeSH terms from each trial's conditions and lists them,
with their broader ancestors, in `derivedSection.conditionBrowseModule`. The table
below maps the broad disease headings of the MeSH tree to groups. Headings that say
nothing about a body system, such as "Signs and Symptoms", are not in it.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.verticals import GROUPS, VERTICALS
from thenwhat.db.models import Claim, EntityMatch, EvidenceEvent
from thenwhat.domain import ReviewState
from thenwhat.sources.clinicaltrials import ClinicalTrials

# MeSH heading to group slug.
MESH_GROUPS: dict[str, str] = {
    "Neoplasms": "cancer",
    "Nervous System Diseases": "brain-and-nerves",
    "Mental Disorders": "mental-health",
    "Cardiovascular Diseases": "heart-and-circulation",
    "Hemic and Lymphatic Diseases": "heart-and-circulation",
    "Respiratory Tract Diseases": "lungs-and-breathing",
    "Digestive System Diseases": "gut-and-liver",
    "Stomatognathic Diseases": "mouth-and-teeth",
    "Skin and Connective Tissue Diseases": "skin-and-hair",
    "Musculoskeletal Diseases": "bones-joints-and-muscles",
    "Wounds and Injuries": "bones-joints-and-muscles",
    "Eye Diseases": "eyes-and-ears",
    "Ear Diseases": "eyes-and-ears",
    "Infections": "infections",
    "Immune System Diseases": "immune-system-and-allergies",
    "Nutritional and Metabolic Diseases": "diabetes-and-hormones",
    "Endocrine System Diseases": "diabetes-and-hormones",
    "Kidney Diseases": "kidneys-and-bladder",
    "Urologic Diseases": "kidneys-and-bladder",
    "Pregnancy Complications": "pregnancy-and-fertility",
    "Infertility": "pregnancy-and-fertility",
}


@dataclass(frozen=True, slots=True)
class GroupSuggestion:
    group: str
    # The MeSH term that produced the suggestion.
    mesh_term: str

    @property
    def title(self) -> str:
        return GROUPS[self.group]


def _terms(payload: Mapping[str, Any]) -> list[str]:
    """A trial's MeSH condition terms, then their ancestors."""
    module = payload.get("derivedSection", {}).get("conditionBrowseModule", {})
    return [
        entry["term"]
        for key in ("meshes", "ancestors")
        for entry in module.get(key, [])
        if isinstance(entry, Mapping) and isinstance(entry.get("term"), str)
    ]


def suggest_groups(payloads: Iterable[Mapping[str, Any]]) -> list[GroupSuggestion]:
    """Every group the trials' MeSH terms point to, each once, with the first term that
    pointed to it. None is preferred: they are listed in the order the groups are configured."""
    found: dict[str, str] = {}
    for payload in payloads:
        for term in _terms(payload):
            group = MESH_GROUPS.get(term)
            if group is not None:
                found.setdefault(group, term)
    return [GroupSuggestion(group, found[group]) for group in GROUPS if group in found]


def approved_trial_payloads(session: Session, claim: Claim) -> list[dict[str, Any]]:
    """The stored registry records of the claim's trials whose match was approved."""
    return list(
        session.scalars(
            select(EvidenceEvent.raw_payload)
            .join(EntityMatch, EntityMatch.id == EvidenceEvent.entity_match_id)
            .where(
                EvidenceEvent.claim_id == claim.id,
                EvidenceEvent.source_name == ClinicalTrials.name,
                EntityMatch.review_state == ReviewState.APPROVED,
            )
            .order_by(EvidenceEvent.id)
        )
    )


def suggestion_line(session: Session, claim: Claim) -> str:
    """One line for the operator: the suggested groups and why, or why there are none."""
    payloads = approved_trial_payloads(session, claim)
    if not payloads:
        return "Health area: no suggestion, as no trial match is approved."
    suggestions = suggest_groups(payloads)
    if not suggestions:
        return (
            "Health area: no suggestion, as the approved trials carry no MeSH term the table maps."
        )
    listed = "; ".join(f"{s.title} (MeSH: {s.mesh_term})" for s in suggestions)
    filed = VERTICALS.get(claim.vertical, claim.vertical)
    return f"Health area suggested: {listed}. Filed under: {filed}."
