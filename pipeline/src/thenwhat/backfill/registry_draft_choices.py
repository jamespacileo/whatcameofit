"""Pure selection of registry draft claims and existing-claim nominations.

Nothing here touches a database or the network, and no input is mutated.
The host verifies evidence hashes before building ``verified`` and persists
whatever this module selects.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from thenwhat.claims.entry import MAX_SLUG_LENGTH, InvalidSlug, condition_words, name_key, slug_for

__all__ = ["GroupChoice", "DraftAction", "DraftSelection", "choose_drafts"]

DRAFT = "draft"
NOMINATE = "nominate"

NEEDS_VERIFICATION = "existing_claim_needs_verification"
UNAVAILABLE = "existing_claim_unavailable"
DUPLICATE_OF_EXISTING = "duplicate_of_existing_claim"
MULTIPLE_VERIFIED = "multiple_verified_claims"
MULTIPLE_EXISTING = "multiple_existing_claims"
QUEUE_CONFLICT = "verified_claim_conflicts_with_queue"
VERTICAL_REVIEW = "vertical_needs_review"
CONFLICTING_VERTICAL = "conflicting_vertical"
PURPOSE_REVIEW = "study_purpose_needs_review"
CONFLICTING_PURPOSE = "conflicting_study_purpose"
DUPLICATE_GROUP = "duplicate_regimen_indication"
REGISTRY_ALIAS_REVIEW = "registry_alias_needs_review"
SLUG_REVIEW = "slug_needs_review"

_SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_DIGEST_LENGTHS = (8, 12, 16, 24)


@dataclass(frozen=True, slots=True)
class GroupChoice:
    group_id: str
    regimen: str
    indication: str
    purpose: str | None
    vertical: str | None
    trial_ids: tuple[str, ...]
    existing_claims: tuple[str, ...] = ()
    unavailable_claims: tuple[str, ...] = ()
    reciprocal_registry_alias: bool = False


@dataclass(frozen=True, slots=True)
class DraftAction:
    group_id: str
    operation: str
    slug: str
    regimen: str
    indication: str
    purpose: str | None
    vertical: str | None
    trial_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DraftSelection:
    actions: tuple[DraftAction, ...]
    holds: Mapping[str, str]
    remaining_trials: Mapping[str, tuple[str, ...]]
    remaining_actionable: int


@dataclass(frozen=True, slots=True)
class _Plan:
    """Outcome for one group before the limit is applied."""

    operation: str | None = None
    slug: str | None = None
    trial_ids: tuple[str, ...] = ()
    hold: str | None = None
    held_trials: tuple[str, ...] = ()


def _text_tuple(value: object, what: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ValueError(f"{what} must be a collection of strings")
    items = tuple(value)
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{what} must contain non-empty strings")
    if len(set(items)) != len(items):
        raise ValueError(f"{what} contains duplicates")
    return items


def _checked_groups(groups: Iterable[GroupChoice]) -> tuple[GroupChoice, ...]:
    checked = []
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, GroupChoice):
            raise ValueError("groups must contain GroupChoice values")
        for name in ("group_id", "regimen", "indication"):
            value = getattr(group, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"group {name} must be a non-empty string")
        for name in ("purpose", "vertical"):
            value = getattr(group, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"group {name} must be a string or None")
        if group.group_id in seen:
            raise ValueError(f"duplicate group id {group.group_id!r}")
        seen.add(group.group_id)
        trials = _text_tuple(group.trial_ids, "trial_ids")
        if not trials:
            raise ValueError(f"group {group.group_id!r} has no trials")
        existing = _text_tuple(group.existing_claims, "existing_claims")
        unavailable = _text_tuple(group.unavailable_claims, "unavailable_claims")
        if set(existing) & set(unavailable):
            raise ValueError(
                f"group {group.group_id!r} lists a claim as both active and unavailable"
            )
        if not isinstance(group.reciprocal_registry_alias, bool):
            raise ValueError(f"group {group.group_id!r} must have a boolean registry alias flag")
        checked.append(
            GroupChoice(
                group.group_id,
                group.regimen,
                group.indication,
                group.purpose,
                group.vertical,
                trials,
                existing,
                unavailable,
                group.reciprocal_registry_alias,
            )
        )
    return tuple(checked)


def _checked_verified(
    verified: Mapping[tuple[str, str], str], by_id: Mapping[str, GroupChoice]
) -> dict[tuple[str, str], str]:
    if not isinstance(verified, Mapping):
        raise ValueError("verified must be a mapping")
    checked = {}
    for key, slug in verified.items():
        if not (
            isinstance(key, tuple) and len(key) == 2 and all(isinstance(part, str) for part in key)
        ):
            raise ValueError(f"malformed verification key {key!r}")
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError(f"malformed verified slug for {key!r}")
        group_id, trial_id = key
        group = by_id.get(group_id)
        if group is None or trial_id not in group.trial_ids:
            raise ValueError(f"verification {key!r} does not match a planned group trial")
        if slug not in group.existing_claims:
            raise ValueError(
                f"verified claim {slug!r} is not an active claim of group {group_id!r}"
            )
        checked[key] = slug
    return checked


def _checked_queue(already_queued: Mapping[str, Collection[str]]) -> dict[str, frozenset[str]]:
    if not isinstance(already_queued, Mapping):
        raise ValueError("already_queued must be a mapping")
    checked = {}
    for slug, trials in already_queued.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("already_queued keys must be non-empty strings")
        if isinstance(trials, (str, bytes)) or not isinstance(trials, Iterable):
            raise ValueError(f"already_queued[{slug!r}] must be a collection of trial ids")
        trial_set = frozenset(trials)
        if not all(isinstance(trial, str) for trial in trial_set):
            raise ValueError(f"already_queued[{slug!r}] must contain strings")
        checked[slug] = trial_set
    return checked


def _plan_existing(
    group: GroupChoice,
    verified: Mapping[tuple[str, str], str],
    queued: Mapping[str, frozenset[str]],
) -> _Plan:
    """Nominate individually verified trials to the group's single active owner."""
    owners = {
        verified[(group.group_id, trial)]
        for trial in group.trial_ids
        if (group.group_id, trial) in verified
    }
    nominate: list[str] = []
    unverified: list[str] = []
    unsettled: list[str] = []
    recorded_owners: set[str] = set()
    conflict: str | None = None
    for trial in group.trial_ids:
        owner = verified.get((group.group_id, trial))
        recorded = [slug for slug in group.existing_claims if trial in queued.get(slug, ())]
        if recorded:
            if owner is not None and owner in recorded:
                recorded_owners.add(owner)
                continue  # an exact verified owner already holds this trial
            if len(recorded) == 1 and owner is None:
                recorded_owners.update(recorded)
                continue  # already recorded for exactly one active claim
            conflict = conflict or (MULTIPLE_EXISTING if len(recorded) > 1 else QUEUE_CONFLICT)
            unsettled.append(trial)
        elif owner is not None:
            nominate.append(trial)
            unsettled.append(trial)
        else:
            unverified.append(trial)
            unsettled.append(trial)
    if len(owners) > 1:
        return _Plan(hold=MULTIPLE_VERIFIED, held_trials=tuple(unsettled))
    if len(recorded_owners | owners) > 1:
        return _Plan(hold=MULTIPLE_EXISTING, held_trials=group.trial_ids)
    if conflict is not None:
        return _Plan(hold=conflict, held_trials=tuple(unsettled))
    hold = NEEDS_VERIFICATION if unverified else None
    if not nominate:
        return _Plan(hold=hold, held_trials=tuple(unverified))
    (owner,) = owners
    return _Plan(NOMINATE, owner, tuple(nominate), hold, tuple(unverified))


def _draft_key(group: GroupChoice) -> tuple[str, tuple[str, ...]]:
    return name_key(group.regimen), tuple(condition_words(group.indication))


def _plan_draft(
    group: GroupChoice,
    cohort: tuple[GroupChoice, ...],
    claimed_keys: Mapping[tuple[str, tuple[str, ...]], bool],
) -> tuple[_Plan, str | None]:
    """Check a group with no active claim; returns the plan and its base slug."""

    def held(reason: str) -> tuple[_Plan, None]:
        return _Plan(hold=reason, held_trials=group.trial_ids), None

    if group.unavailable_claims:
        return held(UNAVAILABLE)
    key = _draft_key(group)
    if key in claimed_keys:
        return held(DUPLICATE_OF_EXISTING if claimed_keys[key] else UNAVAILABLE)
    if group.reciprocal_registry_alias:
        return held(REGISTRY_ALIAS_REVIEW)
    if group.purpose is None or not group.purpose.strip():
        return held(PURPOSE_REVIEW)
    if len({name_key(member.purpose or "") for member in cohort}) > 1:
        return held(CONFLICTING_PURPOSE)
    if group.vertical is None or not group.vertical.strip():
        return held(VERTICAL_REVIEW)
    if len({member.vertical for member in cohort}) > 1:
        return held(CONFLICTING_VERTICAL)
    if len(cohort) > 1:
        return held(DUPLICATE_GROUP)
    try:
        base = slug_for(group.regimen, group.indication)
    except InvalidSlug:
        return held(SLUG_REVIEW)
    if not _valid_slug(base):
        return held(SLUG_REVIEW)
    return _Plan(DRAFT, None, group.trial_ids), base


def _valid_slug(slug: str) -> bool:
    return 0 < len(slug) <= MAX_SLUG_LENGTH and _SLUG_RE.fullmatch(slug) is not None


def _unique_slug(group: GroupChoice, base: str, taken: set[str]) -> str | None:
    """Return ``base`` or a stable digest-suffixed variant not in ``taken``."""
    if base not in taken:
        return base
    regimen, indication = name_key(group.regimen), name_key(group.indication)
    material = "\x1f".join((regimen, indication, name_key(group.purpose or ""))).encode()
    digest = hashlib.sha256(material).hexdigest()
    for size in _DIGEST_LENGTHS:
        room = MAX_SLUG_LENGTH - size - 1
        stem = ""
        for word in base.split("-"):
            longer = f"{stem}-{word}" if stem else word
            if len(longer) > room:
                break
            stem = longer
        stem = stem or base[:room].rstrip("-")
        candidate = f"{stem}-{digest[:size]}" if stem else digest[:size]
        if _valid_slug(candidate) and candidate not in taken:
            return candidate
    return None


def choose_drafts(
    groups: Iterable[GroupChoice],
    *,
    verified: Mapping[tuple[str, str], str],
    already_queued: Mapping[str, Collection[str]],
    occupied: Collection[str],
    limit: int | None,
) -> DraftSelection:
    """Select up to ``limit`` actionable groups (drafts and nominations) in input order."""
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError("limit must be a non-negative integer or None")
    ordered = _checked_groups(groups)
    by_id = {group.group_id: group for group in ordered}
    checked_verified = _checked_verified(verified, by_id)
    queued = _checked_queue(already_queued)
    if isinstance(occupied, (str, bytes)) or not isinstance(occupied, Iterable):
        raise ValueError("occupied must be a collection of slugs")
    taken = set()
    for slug in occupied:
        if not isinstance(slug, str):
            raise ValueError("occupied must contain strings")
        taken.add(slug.casefold())
    for group in ordered:
        taken.update(slug.casefold() for slug in group.existing_claims + group.unavailable_claims)

    # Regimen/indication keys already bound to a claim (True if any is active).
    claimed_keys: dict[tuple[str, tuple[str, ...]], bool] = {}
    cohorts: dict[tuple[str, tuple[str, ...]], list[GroupChoice]] = {}
    for group in ordered:
        key = _draft_key(group)
        if group.existing_claims:
            claimed_keys[key] = True
        elif group.unavailable_claims:
            claimed_keys.setdefault(key, False)
        else:
            cohorts.setdefault(key, []).append(group)

    actions: list[DraftAction] = []
    holds: dict[str, str] = {}
    remaining_trials: dict[str, tuple[str, ...]] = {}
    remaining_actionable = 0
    for group in ordered:
        base = None
        if group.existing_claims:
            plan = _plan_existing(group, checked_verified, queued)
        else:
            plan, base = _plan_draft(group, tuple(cohorts.get(_draft_key(group), ())), claimed_keys)
        operation = plan.operation
        if operation is not None and (limit is None or len(actions) < limit):
            slug = plan.slug
            if operation == DRAFT:
                assert base is not None
                slug = _unique_slug(group, base, taken)
                if slug is None:
                    plan = _Plan(hold=SLUG_REVIEW, held_trials=group.trial_ids)
                else:
                    taken.add(slug)
            if slug is not None:
                actions.append(
                    DraftAction(
                        group.group_id,
                        operation,
                        slug,
                        group.regimen,
                        group.indication,
                        group.purpose,
                        group.vertical,
                        plan.trial_ids,
                    )
                )
        elif operation is not None:
            remaining_actionable += 1
        if plan.hold is not None:
            holds[group.group_id] = plan.hold
            if plan.held_trials:
                remaining_trials[group.group_id] = plan.held_trials
    return DraftSelection(
        tuple(actions),
        MappingProxyType(holds),
        MappingProxyType(remaining_trials),
        remaining_actionable,
    )
