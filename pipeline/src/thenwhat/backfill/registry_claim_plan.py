"""Propose regimen and indication groups from stored registry records, without drafting."""

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.registry_arm_choices import DescribedChoice, described_choice
from thenwhat.backfill.registry_indication import (
    condition_without_treatment_setting,
    has_named_cohorts,
    indication_key,
    resolve_indication,
    title_treatment_settings,
)
from thenwhat.backfill.registry_scope_review import (
    ScopeReview,
    confirm_protocol_evidence,
    validate_scope_review,
)
from thenwhat.backfill.trial_names import generic_intervention_name
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
_SHAM = re.compile(r"(?:intervention: )?sham\b")
_CONTROL_MARKER = re.compile(r"\b(?:placebo|sham)\b|^ptm\s")
_CONTROL_JOIN = re.compile(
    r"[+&;]|\b(?:and|or|plus|with|versus|vs)\b|\b(?:placebo|sham)\s*/|/\s*(?:placebo|sham)\b"
)
_CONTROL_SUFFIX = re.compile(r"\((?:placebo|sham)\)$")
_MATCHED_SHORT = re.compile(r"^ptm\s")
_MATCHED_DEFINITION = re.compile(r"\bplacebo[- ]to[- ]match\s*\(ptm\)", re.IGNORECASE)
_ALTERNATIVE = re.compile(r"\s+or\s+")
_OPTIONAL_ARM_TREATMENT = re.compile(r"±|\+\s*/\s*-|\bwith or without\b", re.IGNORECASE)
_DISTINCT_LINE_REGIMENS = re.compile(
    r"\bas (?P<first>first|second|third)[ -]line\s*/[^.;/]{2,120}\s+"
    r"as (?P<second>first|second|third)[ -]line\b",
    re.IGNORECASE,
)
_NUMBER = r"\d+(?:\.\d+)?"
_NUMERIC_CHOICE = re.compile(
    rf"\b(?:{_NUMBER} or {_NUMBER}|"
    rf"{_NUMBER}\s*(?P<unit>mg|mcg|µg|ug|g|ml|iu|units?) or {_NUMBER}\s*(?P=unit))\b"
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
_POPULATION_WORDS = {
    "adolescents",
    "adults",
    "children",
    "infants",
    "men",
    "newborns",
    "participants",
    "patients",
    "people",
    "subjects",
    "women",
}
# Topic groups covering an organ or anatomical system. An overlap solely with
# infection, allergy or another non-anatomical group awaits topic review.
_ORGAN_TOPIC_GROUPS = frozenset(
    {
        "bones-joints-and-muscles",
        "brain-and-nerves",
        "diabetes-and-hormones",
        "eyes-and-ears",
        "gut-and-liver",
        "heart-and-circulation",
        "kidneys-and-bladder",
        "lungs-and-breathing",
        "mouth-and-teeth",
        "skin-and-hair",
    }
)


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
    arm_choices: tuple[tuple[str, DescribedChoice], ...] = ()


def _members_of(arm: Arm, interventions: Mapping[str, dict[str, Any]]) -> dict[str, str]:
    members = {name_key(name): tidy(name) for name in arm.interventions if name.strip()}
    if arm.label:
        for key, item in interventions.items():
            if arm.label in item.get("armGroupLabels", []):
                members.setdefault(key, tidy(item["name"]))
    return members


def _is_control(key: str, *, matched_short: bool) -> bool:
    if key in _NON_TREATMENT_LABELS:
        return True
    if _CONTROL_JOIN.search(key):
        return False
    return any(
        (
            _PLACEBO.match(key),
            _NAMED_PLACEBO.fullmatch(key),
            _SHAM.match(key),
            _CONTROL_SUFFIX.search(key),
            matched_short and _MATCHED_SHORT.match(key),
        )
    )


def _active_members(members: Mapping[str, str], *, matched_short: bool) -> dict[str, str]:
    return {
        key: label
        for key, label in members.items()
        if not _is_control(key, matched_short=matched_short)
    }


def _has_alternatives(key: str) -> bool:
    # A choice of amounts in the same unit doesn't name two components.
    return _ALTERNATIVE.search(_NUMERIC_CHOICE.sub(" ", key)) is not None


def _has_distinct_line_regimens(title: str) -> bool:
    match = _DISTINCT_LINE_REGIMENS.search(title)
    return match is not None and match["first"].casefold() != match["second"].casefold()


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
    assignments: list[tuple[Arm, dict[str, str]]],
    active_assignments: list[dict[str, str]],
    title: str,
    model: str | None,
) -> set[int]:
    profile = [
        (name_key(arm.label or ""), set(active))
        for (arm, _), active in zip(assignments, active_assignments, strict=True)
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
        only_controls = bool(assignments[index][1]) and not active
        if (
            _CONTROL_LABEL.fullmatch(label)
            or only_controls
            or placebo_on_background
            or outside_escalation
        ):
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
            key: tidy(label)
            for label in protocol.get("conditionsModule", {}).get("conditions", [])
            if (key := indication_key(label))
        }.values()
    )
    identification = protocol.get("identificationModule", {})
    titles = tuple(
        title for field in ("officialTitle", "briefTitle") if (title := identification.get(field))
    )
    conditions, indication_title_phrase = resolve_indication(listed_conditions, titles)
    design = protocol.get("designModule", {}).get("designInfo", {})
    purpose = design.get("primaryPurpose")
    settings = (
        title_treatment_settings(conditions[0], titles)
        if purpose == "TREATMENT" and len(conditions) == 1
        else {}
    )
    if len(settings) == 1:
        ((setting, indication_title_phrase),) = settings.items()
        conditions = (f"{conditions[0]} ({setting} treatment)",)
    intervention_model = design.get("interventionModel")
    treatment = protocol.get("armsInterventionsModule", {})
    descriptions: dict[str, list[str]] = defaultdict(list)
    for raw_arm in treatment.get("armGroups", []):
        if (label := raw_arm.get("label")) and isinstance(text := raw_arm.get("description"), str):
            descriptions[label].append(text)
    interventions = treatment.get("interventions", [])
    names = {name_key(item["name"]): item for item in interventions if item.get("name")}
    arms = trial_arms(study)
    experimental = [arm for arm in arms if arm.kind == "experimental"]
    tested = experimental or [arm for arm in arms if arm.kind == "active_comparator"]
    assignments = [(arm, _members_of(arm, names)) for arm in tested]
    matched_short = any(
        _MATCHED_DEFINITION.search(arm.get(field) or "")
        for arm in treatment.get("armGroups", [])
        for field in ("label", "description")
    )
    active_assignments = [
        _active_members(members, matched_short=matched_short) for _, members in assignments
    ]
    reference = _reference_arms(
        assignments,
        active_assignments,
        identification.get("officialTitle") or "",
        intervention_model,
    )
    tested_assignments = [
        entry for index, entry in enumerate(assignments) if index not in reference
    ]

    regimens: dict[tuple[str, ...], Regimen] = {}
    incomplete = False
    measurement_only = False
    mixed_control = False
    arm_choices = []
    alternatives = len(tested_assignments) == 1 and any(
        _has_distinct_line_regimens(title) for title in titles
    )
    for index, active in enumerate(active_assignments):
        if index in reference:
            continue
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
        mixed_control |= any(_CONTROL_MARKER.search(name) for name in active)
        alternatives |= any(_has_alternatives(name) for name in active)
        alternatives |= len(active) > 1 and bool(
            _OPTIONAL_ARM_TREATMENT.search(assignments[index][0].label or "")
        )
        arm_label = assignments[index][0].label or ""
        arm_texts = descriptions.get(arm_label, [])
        choices = [
            choice
            for text in arm_texts
            if (
                choice := described_choice(
                    text,
                    {key: names.get(key, {}).get("otherNames") or () for key in active},
                    may_separate=len(arm_texts) == 1
                    and intervention_model in {"PARALLEL", "SINGLE_GROUP"}
                    and len(conditions) == 1,
                )
            )
            is not None
        ]
        arm_choices.extend((arm_label, choice) for choice in choices)
        alternatives |= any(not choice.variants for choice in choices)
        variants = choices[0].variants if choices else ()
        for key in variants or (tuple(sorted(active)),):
            aliases = ()
            if len(key) == 1:
                aliases = tuple(
                    dict.fromkeys(
                        tidy(alias)
                        for alias in names.get(key[0], {}).get("otherNames") or ()
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
    if mixed_control:
        issues.append("control_component_needs_review")
    if alternatives:
        issues.append("alternative_regimen_needs_review")
    if len(settings) > 1:
        issues.append("treatment_setting_needs_review")
    if any(
        generic_intervention_name(component)
        for regimen in regimens.values()
        for component in regimen.components
    ):
        issues.append("generic_intervention_needs_review")
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
        tuple(arm_choices),
    )


@dataclass(slots=True)
class PlanGroup:
    regimen: str
    indication: str
    purpose: str
    components: tuple[str, ...]
    trials: list[str] = field(default_factory=list)
    exact_claim_candidates: set[str] = field(default_factory=set)
    alias_claim_candidates: set[str] = field(default_factory=set)
    registry_aliases: dict[str, set[str]] = field(default_factory=dict)
    condition_terms: set[tuple[str, str]] = field(default_factory=set)
    vertical_evidence: dict[str, set[str]] = field(default_factory=dict)
    vertical: str | None = None
    primary_cancer_descriptor: str | None = None


@dataclass(frozen=True, slots=True)
class RegistryClaimPlan:
    groups: tuple[PlanGroup, ...]
    needs_review: dict[str, TrialScope]
    trial_count: int
    current_claim_links: dict[str, str]
    applied_reviews: dict[str, str]
    reviewed_record_hashes: dict[str, str]
    reviews_outside_plan: tuple[str, ...]
    protocol_scope_sha256: dict[str, str]
    protocol_record_hashes: dict[str, str]
    described_arm_choices: dict[str, tuple[tuple[str, DescribedChoice], ...]]


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
    eligibility = protocol.get("eligibilityModule") or {}
    for key in ("eligibilityCriteria", "studyPopulation", "minimumAge", "maximumAge"):
        yield from _evidence_strings(eligibility.get(key))


def _regimen_key(label: str) -> tuple[str, ...]:
    return tuple(sorted(name_key(part) for part in re.split(r"\s+\+\s+", label)))


def _condition_anchors(
    wanted: tuple[str, ...], listed: tuple[str, ...]
) -> dict[tuple[str, ...], str]:
    """Match a registered condition as the head of an explicitly qualified population."""
    anchors = {}
    for label in listed:
        words = indication_key(label)
        if not words or wanted[: len(words)] != words:
            continue
        context = wanted[len(words) :]
        if not context or (
            len(context) >= 2 and context[0] in {"in", "among"} and context[1] in _POPULATION_WORDS
        ):
            anchors[words] = label
    return anchors


def _record_vertical(
    group: PlanGroup,
    terms: list[tuple[str, str]],
    listed_conditions: tuple[str, ...],
    vocabulary: Vocabulary,
) -> None:
    group.condition_terms.update(terms)
    wanted = indication_key(condition_without_treatment_setting(group.indication))
    selected = [identifier for identifier, label in terms if indication_key(label) == wanted]
    if not selected:
        anchors = _condition_anchors(wanted, listed_conditions)
        selected = [identifier for identifier, label in terms if indication_key(label) in anchors]
        if not terms:
            # Exact preferred names are useful when the registry provides labels without
            # its MeSH projection. Keep them distinct from fuzzy or title-only matches.
            for label in anchors.values():
                descriptor = vocabulary.labelled(label)
                if descriptor is not None and descriptor.is_condition:
                    selected.append(descriptor.identifier)
                    group.condition_terms.add((descriptor.identifier, label))
        elif not selected and len(listed_conditions) == 1:
            selected = [identifier for identifier, _ in terms]
    if not selected or vocabulary.missing(selected):
        return
    for identifier in sorted(set(selected)):
        for topic in derived_topics((identifier,), vocabulary):
            group.vertical_evidence.setdefault(topic.group, set()).add(identifier)


def _primary_cancer_descriptor(
    evidence: Mapping[str, set[str]], vocabulary: Vocabulary
) -> str | None:
    """One tumor descriptor supports the full overlap and every other term is broader."""
    if "cancer" not in evidence or _ORGAN_TOPIC_GROUPS.isdisjoint(evidence):
        return None
    descriptors = set().union(*evidence.values())
    for identifier in sorted(evidence["cancer"]):
        if all(identifier in supported for supported in evidence.values()) and (
            descriptors <= vocabulary.at_or_above(identifier)
        ):
            return identifier
    return None


def group_registry_trials(
    trials: Iterable[tuple[str, dict[str, Any]]],
    claims: Iterable[tuple[str, str, str, list[str]]] = (),
    *,
    current_links: Mapping[str, str] | None = None,
    scope_reviews: Mapping[str, ScopeReview] | None = None,
    arm_evidence: Mapping[str, dict[str, Any]] | None = None,
    vocabulary: Vocabulary | None = None,
) -> RegistryClaimPlan:
    """Group only supported arm and condition pairs. Claim candidates still need checking."""
    by_pair: dict[tuple[tuple[str, ...], tuple[str, ...]], set[str]] = {}
    for slug, indication, intervention, aliases in claims:
        condition = indication_key(indication)
        for name in (intervention, *aliases):
            by_pair.setdefault((_regimen_key(name), condition), set()).add(slug)
    groups: dict[tuple[tuple[str, ...], tuple[str, ...], str], PlanGroup] = {}
    needs_review: dict[str, TrialScope] = {}
    current_claim_links: dict[str, str] = {}
    applied_reviews: dict[str, str] = {}
    reviewed_record_hashes: dict[str, str] = {}
    protocol_scope_hashes: dict[str, str] = {}
    protocol_record_hashes: dict[str, str] = {}
    described_arm_choices = {}
    reviews = scope_reviews or {}
    protocols = arm_evidence or {}
    trial_count = 0
    for identifier, record in trials:
        trial_count += 1
        if current_links is not None and identifier in current_links:
            current_claim_links[identifier] = current_links[identifier]
        detail = protocols.get(identifier)
        if detail is not None:
            try:
                confirm_protocol_evidence(identifier, record, detail)
            except ValueError as error:
                raise BackfillError(str(error)) from error
            protocol_scope_hashes[identifier] = payload_of(detail).sha256
            protocol_record_hashes[identifier] = payload_of(record).sha256
        scope = trial_scope(detail if detail is not None else record)
        if scope.arm_choices:
            described_arm_choices[identifier] = scope.arm_choices
        review = reviews.get(identifier)
        if scope.purpose is None or (scope.issues and review is None):
            needs_review[identifier] = scope
            continue
        if review is not None:
            source = record
            stored_digest = payload_of(record).sha256
            digest = stored_digest
            try:
                if digest != review.registry_sha256 and detail is not None:
                    source = detail
                    digest = protocol_scope_hashes[identifier]
                validate_scope_review(
                    review,
                    trial_id=identifier,
                    registry_sha256=digest,
                    source_text=_scope_evidence(source),
                )
            except ValueError as error:
                raise BackfillError(str(error)) from error
            applied_reviews[identifier] = review.reviewed_by
            reviewed_record_hashes[identifier] = stored_digest
            pairs = [(Regimen(pair.regimen), pair.indication) for pair in review.pairs]
        else:
            pairs = [
                (regimen, indication)
                for indication in scope.conditions
                for regimen in scope.regimens
            ]
        terms = trial_terms(record) if vocabulary is not None else []
        for regimen, indication in pairs:
            condition = indication_key(indication)
            key = tuple(sorted(map(name_key, regimen.components))), condition, scope.purpose
            group = groups.setdefault(
                key, PlanGroup(regimen.label, indication, scope.purpose, regimen.components)
            )
            if not group.trials or group.trials[-1] != identifier:
                group.trials.append(identifier)
            group.exact_claim_candidates.update(
                by_pair.get((_regimen_key(regimen.label), condition), ())
            )
            for alias in regimen.aliases:
                group.registry_aliases.setdefault(alias, set()).add(identifier)
                group.alias_claim_candidates.update(
                    by_pair.get((_regimen_key(alias), condition), ())
                )
            if vocabulary is not None:
                _record_vertical(group, terms, scope.registered_conditions, vocabulary)
    for group in groups.values():
        group.alias_claim_candidates.difference_update(group.exact_claim_candidates)
        if len(group.vertical_evidence) == 1:
            group.vertical = next(iter(group.vertical_evidence))
        elif vocabulary is not None and group.vertical_evidence:
            descriptor = _primary_cancer_descriptor(group.vertical_evidence, vocabulary)
            if descriptor is not None:
                group.vertical = "cancer"
                group.primary_cancer_descriptor = descriptor
    return RegistryClaimPlan(
        tuple(groups[key] for key in sorted(groups)),
        needs_review,
        trial_count,
        current_claim_links,
        applied_reviews,
        reviewed_record_hashes,
        tuple(sorted(reviews.keys() - applied_reviews.keys() - needs_review.keys())),
        protocol_scope_hashes,
        protocol_record_hashes,
        described_arm_choices,
    )


def plan_registry_claims(
    session: Session,
    *,
    scope_reviews: Mapping[str, ScopeReview] | None = None,
    arm_evidence: Mapping[str, dict[str, Any]] | None = None,
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
        arm_evidence=arm_evidence,
        vocabulary=vocabulary,
    )
