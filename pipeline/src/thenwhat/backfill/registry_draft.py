"""Plan and apply one registry drafting batch on the private writer."""

from collections import Counter, defaultdict
from collections.abc import Collection, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.link_read import CLAIM_IDENTITY_LOCK
from thenwhat.backfill.registry_claim_plan import PlanGroup, plan_registry_claims
from thenwhat.backfill.registry_draft_choices import DraftAction, GroupChoice, choose_drafts
from thenwhat.backfill.registry_scope_review import ScopeReview
from thenwhat.backfill.trial_names import generic_intervention_name
from thenwhat.backfill.trial_sets import REGISTRY_CLAIMS_2026, registry_claims_2026
from thenwhat.claims.audit import register_audit_batch
from thenwhat.claims.entry import (
    SLUG_PATTERN,
    add_registry_claim,
    condition_words,
    name_key,
    nominate_registry_trials,
)
from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.db.models import AuditBatch, Claim, ClaimChange, Entity, EntityMatch, RegistryTrial
from thenwhat.domain import EntityType, ReviewState
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.store.form import payload_of
from thenwhat.work.errors import BackfillError

Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class VerifiedLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: Digest
    trial_id: Annotated[str, StringConstraints(pattern=r"^NCT[0-9]{8}$")]
    slug: Text
    trial_sha256: Digest
    claim_sha256: Digest
    reviewed_by: Text
    reason: Text


class VerifiedLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    links: list[VerifiedLink]


def _group_id(group: PlanGroup) -> str:
    identity: dict[str, Any] = {
        "regimen": name_key(group.regimen),
        "indication": name_key(group.indication),
        "purpose": group.purpose,
    }
    # A registered component can itself contain the display separator. Keep the arm's
    # structure in its identifier and retain the previous IDs for unambiguous labels.
    components = tuple(map(name_key, group.components))
    if any(" + " in component for component in components):
        identity["components"] = sorted(components)
    return payload_of(identity).sha256


def _registry_alias_groups(
    groups: Mapping[str, PlanGroup],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Find whole registered names used as aliases by peers with the same indication."""
    identities: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    for group_id, group in groups.items():
        key = (name_key(group.regimen), tuple(condition_words(group.indication)))
        identities[key].append(group_id)
    evidence: dict[tuple[str, str], set[str]] = defaultdict(set)
    for group_id, group in groups.items():
        condition = tuple(condition_words(group.indication))
        for alias, trial_ids in group.registry_aliases.items():
            for peer in identities.get((name_key(alias), condition), ()):
                if peer != group_id:
                    evidence[group_id, peer].update(trial_ids)
    pair_ids = {(min(source, target), max(source, target)) for source, target in evidence}
    pairs = []
    reciprocal = set()
    for one, two in sorted(pair_ids):
        forward = sorted(evidence.get((one, two), ()))
        reverse = sorted(evidence.get((two, one), ()))
        if forward and reverse:
            reciprocal.update((one, two))
        pairs.append(
            {
                "group_ids": [one, two],
                "regimens": [groups[one].regimen, groups[two].regimen],
                "purposes": [groups[one].purpose, groups[two].purpose],
                "indication": groups[one].indication,
                "one_names_two": forward,
                "two_names_one": reverse,
            }
        )
    return pairs, reciprocal


def _trial_hashes(session: Session, trial_ids: Collection[str]) -> dict[str, str]:
    return {
        identifier: payload_of(raw).sha256
        for identifier, raw in session.execute(
            select(RegistryTrial.external_id, RegistryTrial.raw_payload).where(
                registry_claims_2026(), RegistryTrial.external_id.in_(trial_ids)
            )
        )
    }


@dataclass(slots=True)
class ClaimCatalogue:
    trial_ids: dict[str, set[str]]
    evidence: dict[str, str]
    unavailable: dict[tuple[str, tuple[str, ...]], set[str]]
    slugs: set[str]


def _claim_catalogue(session: Session, targets: Collection[str]) -> ClaimCatalogue:
    catalogue = ClaimCatalogue({}, {}, defaultdict(set), set(session.scalars(select(Claim.slug))))
    catalogue.slugs.update(
        slug
        for slug in session.scalars(
            select(ClaimChange.former_slug).where(ClaimChange.former_slug.is_not(None))
        )
        if slug is not None
    )
    approved: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for slug, trial_id, state, facts in session.execute(
        select(
            Claim.slug, EntityMatch.external_id, EntityMatch.review_state, EntityMatch.record_facts
        )
        .join(Entity, Entity.claim_id == Claim.id)
        .join(EntityMatch, EntityMatch.entity_id == Entity.id)
        .where(
            Claim.slug.in_(targets),
            Entity.type == EntityType.INTERVENTION,
            EntityMatch.source_name == ClinicalTrials.name,
        )
        .order_by(Claim.slug, EntityMatch.external_id)
    ):
        catalogue.trial_ids.setdefault(slug, set()).add(trial_id)
        if state is ReviewState.APPROVED:
            approved[slug].append((trial_id, facts))
    for claim, entity in session.execute(
        select(Claim, Entity)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(Entity.type == EntityType.INTERVENTION, Claim.merged_into_id.is_(None))
    ):
        if claim.archived_at is not None or claim.review_state is ReviewState.REJECTED:
            indication = tuple(condition_words(claim.indication))
            for name in (entity.name, *entity.synonyms):
                catalogue.unavailable[(name_key(name), indication)].add(claim.slug)
        elif claim.slug in targets:
            catalogue.trial_ids.setdefault(claim.slug, set()).update(
                (*claim.drafting_trial_ids, *claim.registry_candidate_trial_ids)
            )
            catalogue.evidence[claim.slug] = payload_of(
                {
                    "slug": claim.slug,
                    "regimen": entity.name,
                    "aliases": sorted(entity.synonyms),
                    "indication": claim.indication,
                    "headline": claim.headline,
                    "summary": claim.summary,
                    "vertical": claim.vertical,
                    "approved_trials": approved[claim.slug],
                }
            ).sha256
    return catalogue


def _verified_map(
    links: Sequence[VerifiedLink],
    groups: Mapping[str, GroupChoice],
    trial_hashes: Mapping[str, str],
    evidence: Mapping[str, str],
) -> dict[tuple[str, str], str]:
    verified: dict[tuple[str, str], str] = {}
    for link in links:
        group = groups.get(link.group_id)
        if (
            group is None
            or link.trial_id not in group.trial_ids
            or link.slug not in group.existing_claims
        ):
            raise BackfillError(
                f"{link.trial_id} and '{link.slug}' no longer form a plan candidate."
            )
        if (
            trial_hashes.get(link.trial_id) != link.trial_sha256
            or evidence.get(link.slug) != link.claim_sha256
        ):
            raise BackfillError(
                f"Evidence for {link.trial_id} and '{link.slug}' changed. Review it again."
            )
        key = (link.group_id, link.trial_id)
        if key in verified:
            raise BackfillError(
                f"The review receipt lists {link.trial_id} twice for the same group."
            )
        verified[key] = link.slug
    return verified


@dataclass(frozen=True, slots=True)
class DraftBatchPlan:
    batch: str
    actions: tuple[DraftAction, ...]
    apply_plan: str
    report: dict[str, Any]
    verified: tuple[VerifiedLink, ...]


def prepare_draft_plan(
    session: Session,
    batch: str,
    *,
    limit: int | None,
    scope_reviews: Mapping[str, ScopeReview] | None,
    vocabulary: Vocabulary | None,
    links: Sequence[VerifiedLink],
    arm_evidence: Mapping[str, dict[str, Any]] | None = None,
) -> DraftBatchPlan:
    if len(batch) > 60 or SLUG_PATTERN.fullmatch(batch) is None:
        raise BackfillError("Use a batch name with lowercase letters, digits and single hyphens.")
    plan = plan_registry_claims(
        session, scope_reviews=scope_reviews, vocabulary=vocabulary, arm_evidence=arm_evidence
    )
    targets = {
        slug
        for group in plan.groups
        for slug in group.exact_claim_candidates | group.alias_claim_candidates
    }
    catalogue = _claim_catalogue(session, targets)
    details: dict[str, PlanGroup] = {}
    for group in plan.groups:
        group_id = _group_id(group)
        if group_id in details:
            raise BackfillError(
                "Registry draft groups share an identifier. Correct the group plan."
            )
        details[group_id] = group
    alias_pairs, reciprocal_aliases = _registry_alias_groups(details)
    groups = {}
    for group_id, group in details.items():
        candidates = group.exact_claim_candidates | group.alias_claim_candidates
        unavailable = catalogue.unavailable.get(
            (name_key(group.regimen), tuple(condition_words(group.indication))), set()
        )
        groups[group_id] = GroupChoice(
            group_id,
            group.regimen,
            group.indication,
            group.purpose,
            group.vertical,
            tuple(group.trials),
            tuple(sorted(candidates & catalogue.evidence.keys())),
            tuple(sorted(unavailable | (candidates - catalogue.evidence.keys()))),
            group_id in reciprocal_aliases,
        )
    candidate_groups = [group for group in groups.values() if group.existing_claims]
    candidate_hashes = _trial_hashes(
        session, {trial for group in candidate_groups for trial in group.trial_ids}
    )
    verified = _verified_map(links, groups, candidate_hashes, catalogue.evidence)
    try:
        selected = choose_drafts(
            groups.values(),
            verified=verified,
            already_queued=catalogue.trial_ids,
            occupied=catalogue.slugs,
            limit=limit,
        )
    except ValueError as error:
        raise BackfillError(str(error)) from error
    actions = selected.actions
    selected_ids = {trial for action in actions for trial in action.trial_ids}
    record_hashes = _trial_hashes(session, selected_ids)
    if record_hashes.keys() != selected_ids:
        raise BackfillError("A proposed trial left the eligible set. Generate a new plan.")
    reviewed_hashes = {
        trial: payload_of(asdict(review)).sha256
        for trial, review in (scope_reviews or {}).items()
        if trial in selected_ids and trial in plan.applied_reviews
    }
    if any(record_hashes[trial] != plan.reviewed_record_hashes[trial] for trial in reviewed_hashes):
        raise BackfillError(
            "A reviewed trial changed while building the plan. Generate a new plan."
        )
    nominated_keys = {
        (action.group_id, trial_id)
        for action in actions
        if action.operation == "nominate"
        for trial_id in action.trial_ids
    }
    used_links = tuple(link for link in links if (link.group_id, link.trial_id) in nominated_keys)
    action_rows = [asdict(action) for action in actions]
    plan_content: dict[str, Any] = {
        "set": REGISTRY_CLAIMS_2026,
        "batch": batch,
        "actions": action_rows,
        "records": record_hashes,
        "verified": sorted(
            (link.model_dump() for link in used_links),
            key=lambda link: (link["group_id"], link["trial_id"]),
        ),
    }
    if reviewed_hashes:
        plan_content["scope_review_sha256"] = reviewed_hashes
    selected_groups = {action.group_id for action in actions}
    selected_alias_pairs = [
        pair for pair in alias_pairs if not selected_groups.isdisjoint(pair["group_ids"])
    ]
    if selected_alias_pairs:
        plan_content["registry_alias_pairs"] = selected_alias_pairs
    plan_id = payload_of(plan_content).sha256
    held_counts = Counter(selected.holds.values())
    report = {
        "set": REGISTRY_CLAIMS_2026,
        "batch": batch,
        "apply_plan": plan_id,
        "trial_count": plan.trial_count,
        "trials_without_stored_search_name": session.scalar(
            select(func.count())
            .select_from(RegistryTrial)
            .where(registry_claims_2026(), RegistryTrial.search_name.is_(None))
        ),
        "generic_stored_search_names": {
            trial_id: name
            for trial_id, name in session.execute(
                select(RegistryTrial.external_id, RegistryTrial.search_name)
                .where(registry_claims_2026(), RegistryTrial.search_name.is_not(None))
                .order_by(RegistryTrial.external_id)
            )
            if name is not None and generic_intervention_name(name)
        },
        "group_count": len(groups),
        "registry_alias_pairs": alias_pairs,
        "trials_currently_linked": len(plan.current_claim_links),
        "trial_scope_needs_review": {key: value.issues for key, value in plan.needs_review.items()},
        "held_groups_by_reason": dict(held_counts),
        "held_groups": [
            {
                "group_id": identifier,
                "regimen": groups[identifier].regimen,
                "components": details[identifier].components,
                "indication": groups[identifier].indication,
                "reason": reason,
                "trials": selected.remaining_trials.get(identifier, groups[identifier].trial_ids),
                "condition_terms": sorted(details[identifier].condition_terms),
                "vertical_evidence": {
                    name: sorted(terms)
                    for name, terms in details[identifier].vertical_evidence.items()
                },
            }
            for identifier, reason in selected.holds.items()
        ],
        "existing_claim_candidates": [
            {
                "group_id": group.group_id,
                "regimen": group.regimen,
                "components": details[group.group_id].components,
                "indication": group.indication,
                "purpose": group.purpose,
                "trial_sha256": {
                    trial: candidate_hashes[trial]
                    for trial in group.trial_ids
                    if trial in candidate_hashes
                },
                "claim_sha256": {slug: catalogue.evidence[slug] for slug in group.existing_claims},
            }
            for group in candidate_groups
        ],
        "actions": action_rows,
        "scope_review_sha256": reviewed_hashes,
        "remaining_actionable": selected.remaining_actionable,
    }
    return DraftBatchPlan(batch, actions, plan_id, report, used_links)


def lock_drafting(session: Session) -> None:
    """Share the claim identity lock used by the news reader."""
    session.execute(select(func.pg_advisory_xact_lock(CLAIM_IDENTITY_LOCK)))


def applied_batch(session: Session, batch: str, apply_plan: str | None) -> dict[str, Any] | None:
    stored = session.get(AuditBatch, batch)
    if stored is None or stored.draft_record is None:
        return None
    if apply_plan is not None and stored.draft_record["apply_plan"] != apply_plan:
        raise BackfillError(f"Batch '{batch}' already has a different applied plan.")
    return {
        "set": REGISTRY_CLAIMS_2026,
        "batch": batch,
        "outcome": "already_applied",
        "drafted": [],
        "nominated": {},
        "receipt": stored.draft_record,
    }


def apply_draft_plan(session: Session, plan: DraftBatchPlan, apply_plan: str) -> dict[str, Any]:
    if plan.apply_plan != apply_plan:
        raise BackfillError("The batch plan changed. Inspect a new preview before applying it.")
    if not plan.actions:
        return {"outcome": "nothing_to_apply", "drafted": [], "nominated": {}}
    register_audit_batch(session, plan.batch)
    batch = session.get(AuditBatch, plan.batch, with_for_update=True)
    assert batch is not None and batch.draft_record is None
    drafted = []
    nominated = {}
    for action in plan.actions:
        if action.operation == "nominate":
            added = nominate_registry_trials(session, action.slug, action.trial_ids)
            nominated[action.slug] = sorted(set(nominated.get(action.slug, ())).union(added))
        else:
            assert action.vertical is not None
            claim = add_registry_claim(
                session,
                slug=action.slug,
                vertical=action.vertical,
                intervention=action.regimen,
                indication=action.indication,
                trial_ids=action.trial_ids,
                audit_batch=plan.batch,
            )
            drafted.append(claim.slug)
    receipt = {
        "set": REGISTRY_CLAIMS_2026,
        "apply_plan": plan.apply_plan,
        "drafted": drafted,
        "nominated": nominated,
        "actions": [asdict(action) for action in plan.actions],
        "scope_review_sha256": plan.report["scope_review_sha256"],
        "verified_links": [link.model_dump() for link in plan.verified],
    }
    batch.draft_record = receipt
    session.flush()
    return {"outcome": "applied", **receipt}
