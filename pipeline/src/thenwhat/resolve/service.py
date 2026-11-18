"""Proposing registry matches for a claim's entities. Behavior: openspec entity-resolution.

Every candidate is stored and scored. A rule rejects one scored near zero and approves
a trial scored high for the claim's indication; the rest wait for review.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import development_codes, entities_of, substance_name
from thenwhat.claims.entry import name_key
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import (
    NOT_WHAT_IS_TESTED,
    OTHER_INDICATION,
    latest_scoring,
    score_matches,
)
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.events.trial import PHASES
from thenwhat.events.trial_facts import STATES, is_registry_record, read_trial
from thenwhat.measure import spans as measure
from thenwhat.resolve.stored import (
    filed_under_another_name,
    is_a_kind_of_care,
    parts_of,
    stored_trials,
)
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord, UnsearchableTerm
from thenwhat.sources.clinicaltrials import ClinicalTrials, NotSent, Searched

MAX_SUMMARY_CHARACTERS = 400


def what_it_says(record: SourceRecord) -> str | None:
    """One line on what a registry record is: for a trial its title, conditions,
    interventions, phase and state; for a paper its title."""
    section = record.payload.get("protocolSection")
    if isinstance(section, dict):
        parts: list[str] = []
        title = section.get("identificationModule", {}).get("briefTitle")
        if title:
            parts.append(str(title).rstrip("."))
        conditions = section.get("conditionsModule", {}).get("conditions", [])
        if conditions:
            parts.append(f"For: {', '.join(conditions)}")
        tested = [
            intervention.get("name")
            for intervention in section.get("armsInterventionsModule", {}).get("interventions", [])
        ]
        if any(tested):
            parts.append(f"Tests: {', '.join(name for name in tested if name)}")
        phases = "/".join(
            _plain_phase(phase) for phase in section.get("designModule", {}).get("phases", [])
        )
        state = section.get("statusModule", {}).get("overallStatus")
        standing = ", ".join(
            part for part in (phases, state.replace("_", " ").lower() if state else "") if part
        )
        if standing:
            parts.append(standing)
        text = ". ".join(parts)
        return f"{text[:MAX_SUMMARY_CHARACTERS]}." if text else None
    title = record.payload.get("title")
    if isinstance(title, list):
        title = title[0] if title else None
    return str(title)[:MAX_SUMMARY_CHARACTERS] if title else None


def facts_of(record: SourceRecord) -> dict[str, Any] | None:
    """What a trial's registry record says of it, field by field, for the site to lay out:
    its title, conditions, interventions, phases, state and size, as written or as codes. None
    for a record that is not a trial's. Behavior: openspec registry-record-rows."""
    if not is_registry_record(record.payload):
        return None
    section = record.payload["protocolSection"]
    tested = [
        intervention.get("name")
        for intervention in section.get("armsInterventionsModule", {}).get("interventions", [])
    ]
    return {
        "title": section.get("identificationModule", {}).get("briefTitle"),
        "conditions": list(section.get("conditionsModule", {}).get("conditions", [])),
        "interventions": [name for name in tested if name],
        "phases": [
            PHASES[phase].value
            for phase in section.get("designModule", {}).get("phases", [])
            if phase in PHASES
        ],
        "state": STATES.get(section.get("statusModule", {}).get("overallStatus"), "unknown"),
        "participants": (
            {"count": participants.count, "basis": participants.basis}
            if (participants := read_trial(record.payload).facts.participants)
            else None
        ),
    }


def _plain_phase(phase: str) -> str:
    if phase == "NA":
        return "No phase"
    words = phase.replace("_", " ").replace("PHASE", "Phase ").split()
    return " ".join(word.capitalize() if word.isalpha() else word for word in words)


class TrialSearch(Protocol):
    def name_search(self, intervention: str, condition: str | None = None) -> Searched: ...

    def phrase_search(self, phrase: str, condition: str | None) -> Searched | NotSent: ...


# Told of each search of the registry, and of each term not sent, as it is made.
Searches = Callable[[Searched | NotSent], None]


def combination_search(name: str) -> str | None:
    """The registry search for each treatment of a combination at once, or None when the
    name names one treatment. The registry reads the name as written as one treatment
    whose description holds every word, joining words such as "plus" included, so a
    combination is never found by its name; the search for its parts joined by AND finds
    the trials that give all of them.

    Each part is a name alone: "eloralintide and tirzepatide combination regimen" is
    searched as eloralintide and tirzepatide. A part that names a kind of care
    ("standard chemotherapy") is left out when two named treatments remain, as no
    registry entry need carry those words."""
    parts = parts_of(name)
    named = [part for part in parts if not is_a_kind_of_care(part)]
    if len(named) >= 2:
        parts = named
    if len(parts) < 2:
        return None
    return " AND ".join(f"({part})" for part in parts)


def trials_of(
    trials: TrialSearch,
    entity: Entity,
    indication: str | None,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
    codes: Sequence[str] = (),
    substance: str | None = None,
    filed_under: Sequence[str] = (),
    searched: Searches | None = None,
) -> list[SourceRecord]:
    """Every trial the registry holds under the intervention's name, its other names, its
    search phrases and its development codes. A phrase or a code is searched within the
    indication only. A name that joins several treatments is also searched for all of
    them together. The name the registry of substances gives the intervention's
    substance is searched as a name too, so a brand such as Mosquirix or Aduhelm finds
    the trials filed under the substance. So is each name the stored trials file the
    intervention under (`filed_under`), such as XL092 for zanzalintinib.

    A term the registry cannot search for as written is passed to `unsearchable` and the
    other terms are still searched: each term is its own search. Nothing simpler is
    tried in its place. With no `unsearchable`, the failure is raised. Each search made,
    and each term not sent, is passed to `searched`.
    """
    names = [entity.name, *entity.synonyms]
    for other in (substance, *filed_under):
        if other and name_key(other) not in {name_key(name) for name in names}:
            names.append(other)
    combined = [search for name in names if (search := combination_search(name))]
    searches: list[Callable[[], Searched | NotSent]] = [
        *(
            (lambda term=term: trials.name_search(term, indication))
            for term in dict.fromkeys([*names, *combined])
        ),
        *(
            (lambda phrase=phrase: trials.phrase_search(phrase, indication))
            for phrase in dict.fromkeys([*entity.search_phrases, *codes])
        ),
    ]
    records: list[SourceRecord] = []
    for search in searches:
        try:
            found = search()
        except UnsearchableTerm as refused:
            if unsearchable is None:
                raise
            unsearchable(refused)
            continue
        if searched is not None:
            searched(found)
        if isinstance(found, Searched):
            records += found.records
    return records


@runtime_checkable
class TrialRecords(Protocol):
    def fetch_trial(self, nct_id: str) -> SourceRecord | None: ...


def candidates_of(
    session: Session,
    trials: TrialSearch,
    entity: Entity,
    indication: str | None,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
    *,
    records: TrialRecords | None = None,
    wanted: Callable[[str], bool] = lambda _: True,
    searched: Searches | None = None,
    direct_trial_ids: Sequence[str] = (),
) -> tuple[list[SourceRecord], list[str]]:
    """Every trial that may be the intervention's: what the registry's search returns,
    then the stored trials that list the intervention and that the search did not
    return (openspec entity-resolution, "Stored trials that list the intervention are
    candidates"). With them, the other names known for the intervention, for whoever
    scores: its substance's name and the names the stored trials file it under.

    A stored trial holds fewer fields than a search result, so one that is `wanted` is
    read from the registry in full through `records` before it is returned; one the
    registry no longer answers for is left out. With no `records` it is returned as
    stored. Drafting trials and trials nominated by the registry plan are fetched by ID
    when searches miss them, then scored alongside the other candidates.
    """
    codes = development_codes(session, entity)
    substance = substance_name(session, entity)
    stored = stored_trials(
        session, [entity.name, *entity.synonyms], indication, codes=codes, substance=substance
    )
    found = trials_of(
        trials, entity, indication, unsearchable, codes, substance, stored.other_names, searched
    )
    returned = {record.external_id for record in found}
    for record in stored.records:
        if record.external_id in returned or not wanted(record.external_id):
            continue
        full = records.fetch_trial(record.external_id) if records is not None else record
        if full is not None:
            found.append(full)
            returned.add(full.external_id)
    if records is not None:
        for identifier in direct_trial_ids:
            if identifier not in returned and wanted(identifier):
                full = records.fetch_trial(identifier)
                if full is not None:
                    found.append(full)
    known = {name_key(name) for name in (entity.name, *entity.synonyms)}
    also_named = [
        name
        for name in dict.fromkeys([*([substance] if substance else []), *stored.other_names])
        if name_key(name) not in known
    ]
    return found, also_named


class DoiLookup(Protocol):
    def work(self, doi: str) -> SourceRecord | None: ...


@measure.measuring(
    "registry_search", trace_of=lambda session, claim, **_: measure.claim_trace(claim.slug)
)
def resolve_claim(
    session: Session,
    claim: Claim,
    *,
    trials: TrialSearch | None,
    dois: DoiLookup | None,
    backend: Backend,
    now: datetime,
    rescore: bool = False,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
    records: TrialRecords | None = None,
    searched: Searches | None = None,
) -> list[EntityMatch]:
    """Search the registries for the claim's interventions and papers and store each new
    hit as a scored, pending candidate. Returns the candidates this run added. Each
    search of the trial registry, and each term not sent, is passed to `searched`.

    Passing only one registry restricts the search to that registry.

    The stored trials that list the intervention are candidates too, each read in full
    through `records` when it is given.

    Trials are searched within the claim's indication when the intervention's name is a
    broad one. Candidates that already exist are left exactly as they are, whatever their
    state, unless `rescore` asks for pending ones to be scored again. If a candidate
    cannot be scored, none of this run's candidates are kept.

    A candidate scored under `reject_below` is rejected by rule: kept, out of the review
    queue, and open to the operator to approve. A trial candidate scored for the claim's
    indication at or above `accept_above` is approved by rule; 0 turns that rule off.
    """
    entities = entities_of(session, claim)
    seen = {
        (match.entity_id, match.source_name, match.external_id)
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id.in_([e.id for e in entities]))
        )
    }
    found: list[tuple[Entity, SourceRecord]] = []
    also_named: dict[int, list[str]] = {}

    def consider(entity: Entity, record: SourceRecord) -> None:
        key = (entity.id, record.source_name, record.external_id)
        if key not in seen:
            seen.add(key)
            found.append((entity, record))

    for entity in entities:
        if trials is not None and entity.type is EntityType.INTERVENTION:
            candidates, also_named[entity.id] = candidates_of(
                session,
                trials,
                entity,
                claim.indication,
                unsearchable,
                records=records,
                wanted=lambda nct_id, entity=entity: (
                    (entity.id, ClinicalTrials.name, nct_id) not in seen
                ),
                searched=searched,
                direct_trial_ids=sorted(
                    set(claim.drafting_trial_ids + claim.registry_candidate_trial_ids)
                ),
            )
            for record in candidates:
                consider(entity, record)
        elif dois is not None and entity.type is EntityType.PAPER and entity.doi:
            if any(key[0] == entity.id and key[2].lower() == entity.doi.lower() for key in seen):
                continue  # Its DOI already has a match, such as an origin paper set by rule.
            record = dois.work(entity.doi)
            if record is not None:
                consider(entity, record)

    added: list[EntityMatch] = []
    for entity, record in found:
        match = EntityMatch(
            entity_id=entity.id,
            source_name=record.source_name,
            external_id=record.external_id,
            score=0.0,
            record_summary=what_it_says(record),
            record_facts=facts_of(record),
        )
        session.add(match)
        added.append(match)
    session.flush()
    try:
        score_matches(
            session,
            backend,
            claim=claim,
            candidates=[
                (entity, match, record)
                for (entity, record), match in zip(found, added, strict=True)
            ],
            now=now,
            also_named=also_named,
        )
    except DecisionFailed:
        # The decision log keeps the failure; the unscored candidates are withdrawn.
        for match in added:
            session.delete(match)
        session.flush()
        raise
    reject_near_zero(added, reject_below, now)
    approve_confident(session, added, accept_above, now)
    session.flush()
    if rescore and trials is not None:
        rescore_claim(
            session,
            claim,
            trials=trials,
            backend=backend,
            now=now,
            skip=added,
            reject_below=reject_below,
            accept_above=accept_above,
            unsearchable=unsearchable,
            records=records,
        )
    return added


def reject_near_zero(scored: list[EntityMatch], reject_below: float, now: datetime) -> None:
    for match in scored:
        if match.review_state is ReviewState.PENDING and match.score < reject_below:
            record_decision(match, ReviewState.REJECTED, by=Decider.RULE, now=now)


def _scored_for_the_indication(session: Session, match: EntityMatch) -> bool:
    """True when the latest scoring asked about the claim's indication and read the
    record neither as the same intervention for another indication nor as a trial the
    intervention is in without being what it tests."""
    scored = latest_scoring(session, match)
    if scored is None or scored.output is None:
        return False
    return OTHER_INDICATION in scored.options and scored.output.get("choice") not in (
        OTHER_INDICATION,
        NOT_WHAT_IS_TESTED,
    )


def approve_confident(
    session: Session, scored: list[EntityMatch], accept_above: float, now: datetime
) -> None:
    """Approve by rule the trial candidates scored for the indication at or above the
    threshold. Openspec auto-publish: "Confident candidates are approved by rule"."""
    if accept_above <= 0:
        return
    for match in scored:
        entity = session.get(Entity, match.entity_id)
        if (
            match.review_state is ReviewState.PENDING
            and match.score >= accept_above
            and entity is not None
            and entity.type is EntityType.INTERVENTION
            and _scored_for_the_indication(session, match)
        ):
            record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=now)


def rescore_claim(
    session: Session,
    claim: Claim,
    *,
    trials: TrialSearch,
    backend: Backend,
    now: datetime,
    skip: list[EntityMatch] | None = None,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
    records: TrialRecords | None = None,
) -> list[EntityMatch]:
    """Score again the pending trial candidates that the search still returns, and return
    them. For candidates scored before the indication was part of the question.

    A candidate a rule rejected for scoring near zero is scored again too when its
    record files the intervention under another name: an entry lists one of the
    intervention's names among its other names, or is named by a name the stored trials
    file the intervention under. Until the scoring was shown those names, such a trial
    read as a trial of something else. Once scored it waits like a pending candidate,
    and the same rules decide it.

    A candidate someone has decided keeps the score it was decided on. A pending
    candidate the search no longer returns keeps its old score, and the review queue
    says how it was scored.
    """
    just_scored = {match.id for match in skip or []}
    again: list[tuple[Entity, EntityMatch, SourceRecord]] = []
    reopened: list[EntityMatch] = []
    also_named: dict[int, list[str]] = {}
    for entity in entities_of(session, claim):
        if entity.type is not EntityType.INTERVENTION:
            continue
        pending = {
            (match.source_name, match.external_id): match
            for match in session.scalars(
                select(EntityMatch).where(
                    EntityMatch.entity_id == entity.id,
                    EntityMatch.review_state == ReviewState.PENDING,
                )
            )
            if match.id not in just_scored
        }
        rejected_by_rule = {
            (match.source_name, match.external_id): match
            for match in session.scalars(
                select(EntityMatch).where(
                    EntityMatch.entity_id == entity.id,
                    EntityMatch.source_name == ClinicalTrials.name,
                    EntityMatch.review_state == ReviewState.REJECTED,
                    EntityMatch.reviewed_by == Decider.RULE,
                )
            )
            if match.id not in just_scored
        }
        candidates, also_named[entity.id] = candidates_of(
            session,
            trials,
            entity,
            claim.indication,
            unsearchable,
            records=records,
            wanted=lambda nct_id, known=(pending, rejected_by_rule): any(
                (ClinicalTrials.name, nct_id) in matches for matches in known
            ),
            direct_trial_ids=sorted(
                set(claim.drafting_trial_ids + claim.registry_candidate_trial_ids)
            ),
        )
        names = [
            entity.name,
            *entity.synonyms,
            *development_codes(session, entity),
            *also_named[entity.id],
        ]
        for record in candidates:
            key = (record.source_name, record.external_id)
            match = pending.pop(key, None)
            if (
                match is None
                and key in rejected_by_rule
                and filed_under_another_name(record.payload, names, also_named[entity.id])
            ):
                match = rejected_by_rule.pop(key)
                reopened.append(match)
            if match is not None:
                match.record_summary = what_it_says(record)
                match.record_facts = facts_of(record)
                again.append((entity, match, record))
    score_matches(session, backend, claim=claim, candidates=again, now=now, also_named=also_named)
    # Only once every candidate is scored: a scoring that fails leaves the rule's
    # rejections as they were.
    for match in reopened:
        match.review_state = ReviewState.PENDING
        match.reviewed_at = None
        match.reviewed_by = None
    rescored = [match for _, match, _ in again]
    reject_near_zero(rescored, reject_below, now)
    approve_confident(session, rescored, accept_above, now)
    session.flush()
    return rescored


@dataclass(frozen=True, slots=True)
class RuleRedo:
    """What scoring a rule's approvals again changed for one claim. Trials are given by
    their registry identifiers."""

    scored: int
    # No longer approved and waiting for review. Approving one later does not bring its
    # events back: they stay rejected until someone approves them.
    pending: list[str]
    # No longer approved and rejected by the rule for scoring near zero.
    rejected: list[str]
    # Approved by a rule, but the registry search no longer returns them, so they were
    # not scored and stay approved. To be looked at: nothing here says they still hold.
    not_returned: list[str]
    # Events read from a match that is no longer approved, which a person or an
    # assistant had decided. They are left as they were, by their ids.
    events_kept: list[int]

    @property
    def withdrawn(self) -> list[str]:
        """Every trial the rule no longer approves."""
        return [*self.pending, *self.rejected]


def redo_rule_approvals(
    session: Session,
    claim: Claim,
    *,
    trials: TrialSearch,
    backend: Backend,
    now: datetime,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
    no_signal_years: int = 3,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
    records: TrialRecords | None = None,
) -> RuleRedo:
    """Score again, with the question as it is asked now, the trial matches a rule
    approved, and let the rule decide them again. For approvals made before the question
    showed a trial's arms, or before it asked about the claim's patients and setting.

    A match a person or an assistant decided is left alone. One the search no longer
    returns cannot be scored: it stays approved and is reported. A match the rule no
    longer approves waits for review, or is rejected when it scores near zero. The
    events read from it that a rule approved, or that still wait, are rejected by the
    rule; an event a person or an assistant decided is left and reported. The claim's
    status is then derived again. With the approval rule off nothing is scored.

    Nothing is decided until every match is scored: a scoring that fails leaves every
    approval as it was. Each scoring is logged, so the earlier score of a match stays
    in the decision log beside the new one.
    """
    if accept_above <= 0:
        return RuleRedo(0, [], [], [], [])
    again: list[tuple[Entity, EntityMatch, SourceRecord]] = []
    also_named: dict[int, list[str]] = {}
    not_returned: list[str] = []
    for entity in entities_of(session, claim):
        if entity.type is not EntityType.INTERVENTION:
            continue
        approved = {
            (match.source_name, match.external_id): match
            for match in session.scalars(
                select(EntityMatch).where(
                    EntityMatch.entity_id == entity.id,
                    EntityMatch.review_state == ReviewState.APPROVED,
                    EntityMatch.reviewed_by == Decider.RULE,
                )
            )
        }
        if not approved:
            continue
        candidates, also_named[entity.id] = candidates_of(
            session,
            trials,
            entity,
            claim.indication,
            unsearchable,
            records=records,
            wanted=lambda nct_id, approved=approved: (ClinicalTrials.name, nct_id) in approved,
            direct_trial_ids=sorted(
                set(claim.drafting_trial_ids + claim.registry_candidate_trial_ids)
            ),
        )
        for record in candidates:
            match = approved.pop((record.source_name, record.external_id), None)
            if match is not None:
                again.append((entity, match, record))
        # What is left is a trial approval the search did not return. A paper's match
        # is never returned by it and is not this function's to report.
        not_returned += [
            match.external_id
            for match in approved.values()
            if match.source_name == ClinicalTrials.name
        ]
    score_matches(session, backend, claim=claim, candidates=again, now=now, also_named=also_named)
    rescored = [match for _, match, _ in again]
    for _, match, record in again:
        match.record_summary = what_it_says(record)
        match.record_facts = facts_of(record)
        match.review_state = ReviewState.PENDING
        match.reviewed_at = None
        match.reviewed_by = None
    reject_near_zero(rescored, reject_below, now)
    approve_confident(session, rescored, accept_above, now)
    withdrawn = [match for match in rescored if match.review_state is not ReviewState.APPROVED]
    events_kept: list[int] = []
    for match in withdrawn:
        for event in session.scalars(
            select(EvidenceEvent).where(
                EvidenceEvent.entity_match_id == match.id,
                EvidenceEvent.review_state != ReviewState.REJECTED,
            )
        ):
            if event.reviewed_by in (None, Decider.RULE):
                record_decision(event, ReviewState.REJECTED, by=Decider.RULE, now=now)
            else:
                events_kept.append(event.id)
    session.flush()
    if withdrawn:
        refresh_status(session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years)
    return RuleRedo(
        scored=len(rescored),
        pending=[m.external_id for m in withdrawn if m.review_state is ReviewState.PENDING],
        rejected=[m.external_id for m in withdrawn if m.review_state is ReviewState.REJECTED],
        not_returned=sorted(not_returned),
        events_kept=events_kept,
    )


def fill_record_facts(session: Session, registry: TrialRecords) -> tuple[int, list[str]]:
    """Read the record of every shown trial match stored before its facts were kept, and
    keep them. Returns how many were filled and the identifiers the registry no longer
    answers for, which stay empty. Behavior: openspec registry-record-rows."""
    waiting = session.scalars(
        select(EntityMatch)
        .where(
            EntityMatch.source_name == ClinicalTrials.name,
            EntityMatch.record_facts.is_(None),
            EntityMatch.review_state.in_([ReviewState.APPROVED, ReviewState.PENDING]),
        )
        .order_by(EntityMatch.id)
    ).all()
    filled = 0
    missing: list[str] = []
    for match in waiting:
        record = registry.fetch_trial(match.external_id)
        facts = facts_of(record) if record is not None else None
        if facts is None:
            missing.append(match.external_id)
            continue
        match.record_facts = facts
        filled += 1
    session.flush()
    return filled, missing
