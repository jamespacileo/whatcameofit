"""Propose regimen and indication groups from stored registry records, without drafting."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.registry_indication import has_named_cohorts, resolve_indication
from thenwhat.backfill.registry_scope_review import ScopeReview, validate_scope_review
from thenwhat.backfill.trial_sets import registry_claims_2026
from thenwhat.claims.entry import condition_words, name_key, tidy
from thenwhat.clinical.categories import trial_terms
from thenwhat.clinical.topics import derived_topics
from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.db.models import Claim, Entity, RegistryTrial
from thenwhat.domain import EntityType, ReviewState
from thenwhat.events.trial_facts import Arm, trial_arms
from thenwhat.export.records import PostgresRecords
from thenwhat.export.trials_listing import _cited as cited_by_published_claims
from thenwhat.store.form import payload_of
from thenwhat.work.errors import BackfillError

# A placebo can be used to blind an experimental arm. Other co-interventions, including
# standard care, are retained if the registry identifies them as a member of that arm.
_PLACEBO = re.compile(r"(?:intervention: )?(?:matching |matched |dummy )?placebo\b")
_NAMED_PLACEBO = re.compile(
    r"(?P<intervention>[\w(). -]+) placebo(?: (?:tablets?|capsules?|injections?|oral solution))?"
)
_NON_TREATMENT_LABELS = {"placebo", "sham", "no treatment", "no intervention", "control"}
_CONTROL_LABEL = re.compile(r"^control(?: (?:arm|group))?$")
_DOSE_ESCALATION = re.compile(r"\bdose[- ]escalation regimens? (?:for|of) ")
_SUPPORTIVE_LABEL = "non investigational medicinal product"
_MEASUREMENT_TYPES = {"PROCEDURE", "DIAGNOSTIC_TEST", "OTHER"}
_MEASUREMENT_LABELS = {
    "biospecimen collection",
    "bone marrow aspiration and biopsy",
    "chest radiography",
    "computed tomography",
    "echocardiography",
    "magnetic resonance imaging",
    "multigated acquisition scan",
    "positron emission tomography",
    "quality of life assessment",
    "questionnaire administration",
}


@dataclass(frozen=True, slots=True)
class Regimen:
    components: tuple[str, ...]
    # Names the registry attaches to the same intervention record. Used for retrieval.
    aliases: tuple[str, ...] = ()
    assessments: tuple[str, ...] = ()
    background: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return " + ".join(self.components)


@dataclass(frozen=True, slots=True)
class TrialScope:
    regimens: tuple[Regimen, ...]
    conditions: tuple[str, ...]
    purpose: str | None
    issues: tuple[str, ...] = ()
    indication_title_phrase: str | None = None
    registered_conditions: tuple[str, ...] = ()
    reference_arms: tuple[str, ...] = ()


def _members_of(arm: Arm, interventions: Mapping[str, dict[str, Any]]) -> dict[str, str]:
    members = {name_key(name): tidy(name) for name in arm.interventions if name.strip()}
    if arm.label:
        for key, item in interventions.items():
            if arm.label in item.get("armGroupLabels", []):
                members.setdefault(key, tidy(item["name"]))
    return members


def _active_members(members: Mapping[str, str]) -> dict[str, str]:
    return {
        key: label
        for key, label in members.items()
        if key not in _NON_TREATMENT_LABELS
        and not _PLACEBO.match(key)
        and not _NAMED_PLACEBO.fullmatch(key)
    }


def _escalated_intervention(title: str, names: Iterable[str]) -> str | None:
    anchor = _DOSE_ESCALATION.search(name_key(title))
    if anchor is None:
        return None
    tail = name_key(title)[anchor.end() :]
    found = [
        name
        for name in names
        if re.match(rf"{re.escape(name)}(?!\w)", tail)
        and not re.match(r"^\s*(?:[,/+]|and\b|or\b|with\b)", tail[len(name) :])
    ]
    return found[0] if len(found) == 1 else None


def _reference_arms(
    assignments: list[tuple[Arm, dict[str, str]]], title: str, model: str | None
) -> set[int]:
    profile = [
        (name_key(arm.label or ""), set(_active_members(members))) for arm, members in assignments
    ]
    names = {key for _, active in profile for key in active}
    focus = _escalated_intervention(title, names) if model == "PARALLEL" else None
    reference = set()
    for index, (label, active) in enumerate(profile):
        named_placebos = {
            placeholder["intervention"].strip()
            for member in assignments[index][1]
            if (placeholder := _NAMED_PLACEBO.fullmatch(member))
        }
        placebo_on_background = (
            model == "PARALLEL"
            and active
            and any(
                active < peer
                and (
                    (_PLACEBO.match(label) and not _PLACEBO.match(peer_label))
                    or peer - active <= named_placebos
                )
                for peer_label, peer in profile
            )
        )
        outside_escalation = focus is not None and bool(active) and focus not in active
        if _CONTROL_LABEL.fullmatch(label) or placebo_on_background or outside_escalation:
            reference.add(index)
    return reference


def _documented_background(
    active: Mapping[str, str], names: Mapping[str, dict[str, Any]], titles: tuple[str, ...]
) -> dict[str, str]:
    labelled = {
        key: label
        for key, label in active.items()
        if any(
            " ".join(condition_words(alias)) == _SUPPORTIVE_LABEL
            for alias in names.get(key, {}).get("otherNames", [])
        )
    }
    tested = active.keys() - labelled.keys()
    if labelled and len(tested) == 1:
        name = next(iter(tested))
        compared = re.compile(rf"(?<!\w){re.escape(name)}\s+(?:versus|vs\.?)(?!\w)")
        if any(compared.search(name_key(title)) for title in titles):
            return labelled
    return {}


def trial_scope(study: dict[str, Any]) -> TrialScope:
    """Read registered regimen membership and full condition labels.

    Keep the study visible for review if roles or condition assignments need evidence.
    A sponsor's wording is retained, including route and formulation.
    """
    protocol = study.get("protocolSection") or {}
    listed_conditions = tuple(
        {
            tuple(condition_words(label)): tidy(label)
            for label in protocol.get("conditionsModule", {}).get("conditions", [])
            if condition_words(label)
        }.values()
    )
    identification = protocol.get("identificationModule", {})
    titles = tuple(
        title for field in ("officialTitle", "briefTitle") if (title := identification.get(field))
    )
    conditions, indication_title_phrase = resolve_indication(listed_conditions, titles)
    design = protocol.get("designModule", {}).get("designInfo", {})
    purpose = design.get("primaryPurpose")
    intervention_model = design.get("interventionModel")
    treatment = protocol.get("armsInterventionsModule", {})
    interventions = treatment.get("interventions", [])
    names = {name_key(item["name"]): item for item in interventions if item.get("name")}
    arms = trial_arms(study)
    experimental = [arm for arm in arms if arm.kind == "experimental"]
    tested = experimental or [arm for arm in arms if arm.kind == "active_comparator"]
    assignments = [(arm, _members_of(arm, names)) for arm in tested]
    reference = _reference_arms(
        assignments, identification.get("officialTitle") or "", intervention_model
    )
    tested_assignments = [
        entry for index, entry in enumerate(assignments) if index not in reference
    ]

    regimens: dict[tuple[str, ...], Regimen] = {}
    incomplete = False
    measurement_only = False
    for _, members in tested_assignments:
        active = _active_members(members)
        if not active:
            incomplete = True
            continue
        assessments = {
            key: label
            for key, label in active.items()
            if purpose in {"TREATMENT", "PREVENTION"}
            and names.get(key, {}).get("type") in _MEASUREMENT_TYPES
            and " ".join(condition_words(label)) in _MEASUREMENT_LABELS
        }
        if active.keys() == assessments.keys():
            measurement_only = True
        else:
            for key in assessments:
                del active[key]
        background = _documented_background(active, names, titles)
        for key in background:
            del active[key]
        key = tuple(sorted(active))
        aliases = ()
        if len(key) == 1:
            aliases = tuple(
                dict.fromkeys(
                    tidy(alias)
                    for alias in names.get(key[0], {}).get("otherNames", [])
                    if alias.strip()
                    and name_key(alias) != key[0]
                    and " ".join(condition_words(alias)) != _SUPPORTIVE_LABEL
                )
            )
        previous = regimens.get(key)
        measured = set(assessments.values())
        supportive = set(background.values())
        if previous is not None:
            measured.update(previous.assessments)
            supportive.update(previous.background)
        regimens[key] = Regimen(
            tuple(active[part] for part in key),
            aliases,
            tuple(sorted(measured)),
            tuple(sorted(supportive)),
        )

    issues = []
    if not tested_assignments:
        issues.append("missing_tested_arm")
    elif incomplete:
        issues.append("missing_arm_interventions")
    if measurement_only:
        issues.append("measurement_only_arm_needs_review")
    if intervention_model in {"CROSSOVER", "SEQUENTIAL"} and any(
        len(regimen.components) > 1 for regimen in regimens.values()
    ):
        issues.append("arm_time_order_needs_review")
    if not conditions:
        issues.append("missing_indication")
    elif len(conditions) > 1 and not (
        len(regimens) == 1
        and has_named_cohorts(conditions, (arm.label for arm, _ in tested_assignments if arm.label))
    ):
        issues.append("condition_assignment_needs_review")
    if not purpose:
        issues.append("missing_primary_purpose")
    return TrialScope(
        tuple(regimens.values()),
        conditions,
        purpose,
        tuple(issues),
        indication_title_phrase,
        listed_conditions,
        tuple(assignments[index][0].label or "" for index in sorted(reference)),
    )


@dataclass(slots=True)
class PlanGroup:
    regimen: str
    indication: str
    purpose: str
    trials: list[str] = field(default_factory=list)
    exact_claim_candidates: set[str] = field(default_factory=set)
    alias_claim_candidates: set[str] = field(default_factory=set)
    condition_terms: set[tuple[str, str]] = field(default_factory=set)
    vertical_evidence: dict[str, set[str]] = field(default_factory=dict)
    vertical: str | None = None


@dataclass(frozen=True, slots=True)
class RegistryClaimPlan:
    groups: tuple[PlanGroup, ...]
    needs_review: dict[str, TrialScope]
    trial_count: int
    current_claim_links: dict[str, str]
    applied_reviews: dict[str, str]
    reviews_outside_plan: tuple[str, ...]


def _evidence_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _evidence_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _evidence_strings(item)


def _scope_evidence(record: dict[str, Any]) -> Iterable[str]:
    protocol = record.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    for title in ("briefTitle", "officialTitle"):
        yield from _evidence_strings(identification.get(title))
    for module in ("conditionsModule", "armsInterventionsModule", "outcomesModule"):
        yield from _evidence_strings(protocol.get(module))


def _regimen_key(label: str) -> tuple[str, ...]:
    return tuple(sorted(name_key(part) for part in re.split(r"\s+\+\s+", label)))


def _record_vertical(
    group: PlanGroup,
    terms: list[tuple[str, str]],
    listed_conditions: tuple[str, ...],
    vocabulary: Vocabulary,
) -> None:
    group.condition_terms.update(terms)
    wanted = condition_words(group.indication)
    exact = [identifier for identifier, label in terms if condition_words(label) == wanted]
    selected = exact or (
        [identifier for identifier, _ in terms] if len(listed_conditions) == 1 else []
    )
    if not selected or vocabulary.missing(selected):
        return
    for topic in derived_topics(selected, vocabulary):
        group.vertical_evidence.setdefault(topic.group, set()).add(topic.category)


def group_registry_trials(
    trials: Iterable[tuple[str, dict[str, Any]]],
    claims: Iterable[tuple[str, str, str, list[str]]] = (),
    *,
    current_links: Mapping[str, str] | None = None,
    scope_reviews: Mapping[str, ScopeReview] | None = None,
    vocabulary: Vocabulary | None = None,
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
    applied_reviews: dict[str, str] = {}
    reviews = scope_reviews or {}
    trial_count = 0
    for identifier, record in trials:
        trial_count += 1
        if current_links is not None and identifier in current_links:
            current_claim_links[identifier] = current_links[identifier]
        scope = trial_scope(record)
        review = reviews.get(identifier)
        if scope.purpose is None or (scope.issues and review is None):
            needs_review[identifier] = scope
            continue
        if review is not None:
            try:
                validate_scope_review(
                    review,
                    trial_id=identifier,
                    registry_sha256=payload_of(record).sha256,
                    source_text=_scope_evidence(record),
                )
            except ValueError as error:
                raise BackfillError(str(error)) from error
            applied_reviews[identifier] = review.reviewed_by
            pairs = [(Regimen(pair.regimen), pair.indication) for pair in review.pairs]
        else:
            pairs = [
                (regimen, indication)
                for indication in scope.conditions
                for regimen in scope.regimens
            ]
        terms = trial_terms(record) if vocabulary is not None else []
        for regimen, indication in pairs:
            condition = tuple(condition_words(indication))
            key = tuple(sorted(map(name_key, regimen.components))), condition, scope.purpose
            group = groups.setdefault(key, PlanGroup(regimen.label, indication, scope.purpose))
            if not group.trials or group.trials[-1] != identifier:
                group.trials.append(identifier)
            group.exact_claim_candidates.update(
                by_pair.get((_regimen_key(regimen.label), condition), ())
            )
            for alias in regimen.aliases:
                group.alias_claim_candidates.update(
                    by_pair.get((_regimen_key(alias), condition), ())
                )
            if vocabulary is not None and terms:
                _record_vertical(group, terms, scope.registered_conditions, vocabulary)
    for group in groups.values():
        group.alias_claim_candidates.difference_update(group.exact_claim_candidates)
        if len(group.vertical_evidence) == 1:
            group.vertical = next(iter(group.vertical_evidence))
    return RegistryClaimPlan(
        tuple(groups[key] for key in sorted(groups)),
        needs_review,
        trial_count,
        current_claim_links,
        applied_reviews,
        tuple(sorted(reviews.keys() - applied_reviews.keys() - needs_review.keys())),
    )


def plan_registry_claims(
    session: Session,
    *,
    scope_reviews: Mapping[str, ScopeReview] | None = None,
    vocabulary: Vocabulary | None = None,
) -> RegistryClaimPlan:
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
    if vocabulary is None:
        vocabulary = Vocabulary(
            (record.external_id, record.payload)
            for record in PostgresRecords(session).mesh_records()
        )
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
        scope_reviews=scope_reviews,
        vocabulary=vocabulary,
    )
