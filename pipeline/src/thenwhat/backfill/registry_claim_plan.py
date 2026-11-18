"""Propose regimen and indication groups from stored registry records, without drafting."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_sets import registry_claims_2026
from thenwhat.claims.entry import condition_words, name_key, tidy
from thenwhat.db.models import Claim, Entity, RegistryTrial
from thenwhat.domain import EntityType, ReviewState
from thenwhat.events.trial_facts import trial_arms
from thenwhat.export.trials_listing import _cited as cited_by_published_claims

# A placebo can be used to blind an experimental arm. Other co-interventions, including
# standard care, are retained if the registry identifies them as a member of that arm.
_PLACEBO = re.compile(r"(?:intervention: )?(?:matching |matched |dummy )?placebo\b")
_NON_TREATMENT_LABELS = {"placebo", "sham", "no treatment", "no intervention", "control"}


@dataclass(frozen=True, slots=True)
class Regimen:
    components: tuple[str, ...]
    # Names the registry attaches to the same intervention record. Used for retrieval.
    aliases: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return " + ".join(self.components)


@dataclass(frozen=True, slots=True)
class TrialScope:
    regimens: tuple[Regimen, ...]
    conditions: tuple[str, ...]
    purpose: str | None
    issues: tuple[str, ...] = ()


def trial_scope(study: dict[str, Any]) -> TrialScope:
    """Read registered regimen membership and full condition labels.

    Keep the study visible for review if roles or condition assignments need evidence.
    A sponsor's wording is retained, including route and formulation.
    """
    protocol = study.get("protocolSection") or {}
    conditions = tuple(
        {
            tuple(condition_words(label)): tidy(label)
            for label in protocol.get("conditionsModule", {}).get("conditions", [])
            if condition_words(label)
        }.values()
    )
    design = protocol.get("designModule", {}).get("designInfo", {})
    purpose = design.get("primaryPurpose")
    intervention_model = design.get("interventionModel")
    treatment = protocol.get("armsInterventionsModule", {})
    interventions = treatment.get("interventions", [])
    names = {name_key(item["name"]): item for item in interventions if item.get("name")}
    arms = trial_arms(study)
    experimental = [arm for arm in arms if arm.kind == "experimental"]
    tested = experimental or [arm for arm in arms if arm.kind == "active_comparator"]

    regimens: dict[tuple[str, ...], Regimen] = {}
    incomplete = False
    for arm in tested:
        # Membership can be recorded in either direction. Keep identical entries once.
        members = {name_key(name): tidy(name) for name in arm.interventions if name.strip()}
        if arm.label:
            for key, item in names.items():
                if arm.label in item.get("armGroupLabels", []):
                    members.setdefault(key, tidy(item["name"]))
        active = {
            key: label
            for key, label in members.items()
            if key not in _NON_TREATMENT_LABELS and not _PLACEBO.match(key)
        }
        if not active:
            incomplete = True
            continue
        key = tuple(sorted(active))
        aliases = ()
        if len(key) == 1:
            aliases = tuple(
                dict.fromkeys(
                    tidy(alias)
                    for alias in names.get(key[0], {}).get("otherNames", [])
                    if alias.strip() and name_key(alias) != key[0]
                )
            )
        regimens[key] = Regimen(tuple(active[part] for part in key), aliases)

    issues = []
    if not tested:
        issues.append("missing_tested_arm")
    elif incomplete:
        issues.append("missing_arm_interventions")
    if intervention_model in {"CROSSOVER", "SEQUENTIAL"} and any(
        len(regimen.components) > 1 for regimen in regimens.values()
    ):
        issues.append("arm_time_order_needs_review")
    if not conditions:
        issues.append("missing_indication")
    elif len(conditions) > 1:
        issues.append("condition_assignment_needs_review")
    if not purpose:
        issues.append("missing_primary_purpose")
    return TrialScope(tuple(regimens.values()), conditions, purpose, tuple(issues))


@dataclass(slots=True)
class PlanGroup:
    regimen: str
    indication: str
    purpose: str
    trials: list[str] = field(default_factory=list)
    exact_claim_candidates: set[str] = field(default_factory=set)
    alias_claim_candidates: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class RegistryClaimPlan:
    groups: tuple[PlanGroup, ...]
    needs_review: dict[str, TrialScope]
    trial_count: int
    current_claim_links: dict[str, str]


def _regimen_key(label: str) -> tuple[str, ...]:
    return tuple(sorted(name_key(part) for part in re.split(r"\s+\+\s+", label)))


def group_registry_trials(
    trials: Iterable[tuple[str, dict[str, Any]]],
    claims: Iterable[tuple[str, str, str, list[str]]] = (),
    *,
    current_links: Mapping[str, str] | None = None,
) -> RegistryClaimPlan:
    """Group only supported arm and condition pairs. Claim candidates still need checking."""
    by_pair: dict[tuple[tuple[str, ...], tuple[str, ...]], set[str]] = {}
    for slug, indication, intervention, aliases in claims:
        condition = tuple(condition_words(indication))
        for name in (intervention, *aliases):
            by_pair.setdefault((_regimen_key(name), condition), set()).add(slug)
    groups: dict[tuple[tuple[str, ...], tuple[str, ...], str], PlanGroup] = {}
    needs_review: dict[str, TrialScope] = {}
    current_claim_links: dict[str, str] = {}
    trial_count = 0
    for identifier, record in trials:
        trial_count += 1
        if current_links is not None and identifier in current_links:
            current_claim_links[identifier] = current_links[identifier]
        scope = trial_scope(record)
        if scope.issues or scope.purpose is None:
            needs_review[identifier] = scope
            continue
        indication = scope.conditions[0]
        condition = tuple(condition_words(indication))
        for regimen in scope.regimens:
            key = tuple(map(name_key, regimen.components)), condition, scope.purpose
            group = groups.setdefault(key, PlanGroup(regimen.label, indication, scope.purpose))
            group.trials.append(identifier)
            group.exact_claim_candidates.update(
                by_pair.get((_regimen_key(regimen.label), condition), ())
            )
            for alias in regimen.aliases:
                group.alias_claim_candidates.update(
                    by_pair.get((_regimen_key(alias), condition), ())
                )
    for group in groups.values():
        group.alias_claim_candidates.difference_update(group.exact_claim_candidates)
    return RegistryClaimPlan(
        tuple(groups[key] for key in sorted(groups)), needs_review, trial_count, current_claim_links
    )


def plan_registry_claims(session: Session) -> RegistryClaimPlan:
    """Read the target cohort and active claim identities in the current database."""
    claims = session.execute(
        select(Claim.slug, Claim.indication, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(
            Entity.type == EntityType.INTERVENTION,
            Claim.archived_at.is_(None),
            Claim.merged_into_id.is_(None),
            Claim.review_state != ReviewState.REJECTED,
        )
    ).all()
    current_links = cited_by_published_claims(session)
    trials = session.execute(
        select(RegistryTrial.external_id, RegistryTrial.raw_payload)
        .where(registry_claims_2026())
        .order_by(RegistryTrial.external_id)
        .execution_options(yield_per=1000)
    )
    return group_registry_trials(
        ((identifier, payload) for identifier, payload in trials),
        ((slug, indication, name, aliases) for slug, indication, name, aliases in claims),
        current_links=current_links,
    )
