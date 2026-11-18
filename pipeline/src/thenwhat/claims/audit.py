"""Draw, record and release sampled publication audits on the writer."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from secrets import token_hex

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.claims.audit_rules import assess_release, draw_claims
from thenwhat.claims.entry import SLUG_PATTERN, AuditRefused, archive_claim
from thenwhat.db.models import AuditBatch, AuditJudgement, AuditSample, Claim, Entity, EntityMatch
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.store.form import payload_of


def register_audit_batch(session: Session, batch: str) -> None:
    """Name the batch before recording its registry drafts."""
    if len(batch) > 60 or not SLUG_PATTERN.fullmatch(batch):
        raise AuditRefused("Use a batch name with lowercase letters, digits and single hyphens.")
    session.execute(insert(AuditBatch).values(name=batch).on_conflict_do_nothing())


def _lock_batch(session: Session, batch: str) -> None:
    if session.get(AuditBatch, batch, with_for_update=True) is None:
        raise AuditRefused(f"No audit batch is named '{batch}'.")


def _latest_sample(session: Session, batch: str) -> AuditSample | None:
    return session.scalar(
        select(AuditSample)
        .where(AuditSample.batch == batch)
        .order_by(AuditSample.id.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )


def _held(session: Session, batch: str) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .where(
                Claim.audit_batch == batch,
                Claim.awaiting_audit_at.is_not(None),
                Claim.archived_at.is_(None),
                Claim.review_state == ReviewState.APPROVED,
            )
            .order_by(Claim.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )


def _judgements(session: Session, sample_id: int) -> dict[int, AuditJudgement]:
    return {
        row.claim_id: row
        for row in session.scalars(
            select(AuditJudgement)
            .where(AuditJudgement.sample_id == sample_id)
            .order_by(AuditJudgement.judged_by)
        )
    }


def sample_batch(
    session: Session,
    batch: str,
    *,
    size: int | None,
    whole: bool,
    fresh: bool,
    now: datetime,
) -> AuditSample:
    _lock_batch(session, batch)
    existing = _latest_sample(session, batch)
    if existing is not None and not fresh:
        return existing
    if (
        existing is not None
        and (not whole or existing.claim_ids == existing.population_ids)
        and len(_judgements(session, existing.id)) < len(existing.claim_ids)
    ):
        raise AuditRefused("Finish the current sample or switch to a whole audit.")
    held = _held(session, batch)
    if existing is not None and not whole:
        wrong = {
            identifier: note
            for identifier, note in _judgements(session, existing.id).items()
            if not note.right
        }
        for claim in held:
            note = wrong.get(claim.id)
            if note is not None and _facts(session, claim) == note.facts_sha256:
                raise AuditRefused(
                    f"Correct or archive '{claim.slug}' before drawing a fresh partial sample."
                )
    population = [claim.id for claim in held]
    if not population:
        raise AuditRefused(f"No approved claims in batch '{batch}' are awaiting audit.")
    if size is None and not whole:
        raise AuditRefused("Set AUDIT_SAMPLE_SIZE or use audit sample --all to judge every claim.")
    seed = token_hex(16)
    selected = draw_claims(population, size=len(population) if whole else int(size or 0), seed=seed)
    sample = AuditSample(
        batch=batch,
        seed=seed,
        population_ids=population,
        claim_ids=list(selected),
        drawn_at=now,
    )
    session.add(sample)
    session.flush()
    return sample


def sample_slugs(session: Session, sample: AuditSample) -> tuple[str, ...]:
    return tuple(
        session.scalars(
            select(Claim.slug).where(Claim.id.in_(sample.claim_ids)).order_by(Claim.slug)
        )
    )


def _assistant_judgements(session: Session, sample: AuditSample) -> dict[int, AuditJudgement]:
    return {
        note.claim_id: note
        for note in session.scalars(
            select(AuditJudgement).where(
                AuditJudgement.sample_id == sample.id, AuditJudgement.judged_by == Decider.ASSISTANT
            )
        )
    }


@dataclass(frozen=True, slots=True)
class SpotCheck:
    sample: int
    seed: str
    claims: tuple[str, ...]
    checked: int
    differed: int


def spot_check_batch(session: Session, batch: str, *, size: int | None) -> SpotCheck:
    _lock_batch(session, batch)
    sample = _latest_sample(session, batch)
    if sample is None:
        raise AuditRefused(f"Draw an audit sample for batch '{batch}' first.")
    notes = _judgements(session, sample.id)
    assistant = _assistant_judgements(session, sample)
    if not assistant:
        raise AuditRefused("This sample has no assistant judgements to spot-check.")
    if len(notes) != len(sample.claim_ids):
        raise AuditRefused("Finish judging the sample before drawing a spot-check.")
    if sample.spot_claim_ids is None:
        if size is None:
            raise AuditRefused("Give the number of assistant judgements to spot-check with --size.")
        seed = token_hex(16)
        sample.spot_seed = seed
        sample.spot_claim_ids = list(draw_claims(assistant, size=size, seed=seed))
        session.flush()
    spot_ids = sample.spot_claim_ids
    assert sample.spot_seed is not None and spot_ids is not None
    slugs = tuple(
        session.scalars(select(Claim.slug).where(Claim.id.in_(spot_ids)).order_by(Claim.slug))
    )
    checked = [
        identifier for identifier in spot_ids if notes[identifier].judged_by is Decider.HUMAN
    ]
    return SpotCheck(
        sample.id,
        sample.spot_seed,
        slugs,
        len(checked),
        sum(notes[identifier].right != assistant[identifier].right for identifier in checked),
    )


def _facts(session: Session, claim: Claim) -> str:
    intervention = session.execute(
        select(Entity.id, Entity.name, Entity.synonyms).where(
            Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
        )
    ).one()
    matches = session.execute(
        select(EntityMatch.source_name, EntityMatch.external_id, EntityMatch.record_facts)
        .where(
            EntityMatch.entity_id == intervention.id,
            EntityMatch.review_state == ReviewState.APPROVED,
        )
        .order_by(EntityMatch.source_name, EntityMatch.external_id)
    )
    return payload_of(
        {
            "intervention": intervention.name,
            "synonyms": sorted(intervention.synonyms),
            "indication": claim.indication,
            "vertical": claim.vertical,
            "matches": [list(match) for match in matches],
        }
    ).sha256


@dataclass(frozen=True, slots=True)
class AuditOpinion:
    right: bool
    by: Decider
    reviewer: str
    category: str | None
    detail: str | None


def judge_claim(
    session: Session, sample_id: int, slug: str, opinion: AuditOpinion, *, now: datetime
) -> None:
    sample = session.get(AuditSample, sample_id)
    if sample is None:
        raise AuditRefused(f"No audit sample has number {sample_id}.")
    _lock_batch(session, sample.batch)
    active = _latest_sample(session, sample.batch)
    if active is None or active.id != sample.id or active.released_at is not None:
        raise AuditRefused("Judgements belong to the current unreleased sample.")
    claim = session.scalar(
        select(Claim)
        .where(Claim.slug == slug)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if claim is None or claim.id not in sample.claim_ids:
        raise AuditRefused(f"Claim '{slug}' is outside audit sample {sample_id}.")
    reviewer = opinion.reviewer.strip()
    category = (opinion.category or "").strip() or None
    detail = (opinion.detail or "").strip() or None
    if not reviewer or opinion.by not in (Decider.HUMAN, Decider.ASSISTANT):
        raise AuditRefused("Give the reviewer and record whether they are a person or assistant.")
    if (opinion.right and (category or detail)) or (
        not opinion.right and not (category and detail)
    ):
        raise AuditRefused("A wrong judgement needs a defect category and detail.")
    facts = _facts(session, claim)
    existing = session.get(AuditJudgement, (sample.id, claim.id, opinion.by))
    if existing is not None:
        old = AuditOpinion(
            existing.right,
            existing.judged_by,
            existing.reviewer,
            existing.category,
            existing.detail,
        )
        if (
            old == AuditOpinion(opinion.right, opinion.by, reviewer, category, detail)
            and existing.facts_sha256 == facts
        ):
            return
        raise AuditRefused(f"Claim '{slug}' already has a judgement in this sample.")
    other = session.get(
        AuditJudgement,
        (sample.id, claim.id, Decider.ASSISTANT if opinion.by is Decider.HUMAN else Decider.HUMAN),
    )
    if other is not None and (
        opinion.by is not Decider.HUMAN or claim.id not in (sample.spot_claim_ids or ())
    ):
        raise AuditRefused(f"Claim '{slug}' already has a judgement in this sample.")
    session.add(
        AuditJudgement(
            sample_id=sample.id,
            claim_id=claim.id,
            judged_by=opinion.by,
            reviewer=reviewer,
            judged_at=now,
            facts_sha256=facts,
            right=opinion.right,
            category=category,
            detail=detail,
        )
    )
    session.flush()


def _wrong_in_history(session: Session, batch: str) -> set[int]:
    latest: dict[int, bool] = {}
    for claim_id, right in session.execute(
        select(AuditJudgement.claim_id, AuditJudgement.right)
        .join(AuditSample, AuditSample.id == AuditJudgement.sample_id)
        .where(AuditSample.batch == batch)
        .order_by(AuditJudgement.sample_id.desc(), AuditJudgement.judged_by.desc())
    ):
        latest.setdefault(claim_id, right)
    return {claim_id for claim_id, right in latest.items() if not right}


def release_batch(
    session: Session, batch: str, *, max_wrong_share: Decimal | None, now: datetime
) -> int:
    _lock_batch(session, batch)
    sample = _latest_sample(session, batch)
    if sample is None:
        raise AuditRefused(f"Draw an audit sample for batch '{batch}' first.")
    if sample.released_at is not None:
        return 0
    notes = _judgements(session, sample.id)
    result = assess_release(
        sample.population_ids,
        sample.claim_ids,
        {key: note.right for key, note in notes.items()},
        max_wrong_share=max_wrong_share,
    )
    if result.refusal == "unfinished":
        raise AuditRefused(f"{len(result.missing)} sampled claims still need a judgement.")
    if _assistant_judgements(session, sample):
        if sample.spot_claim_ids is None:
            raise AuditRefused("Draw an operator spot-check for the assistant's judgements.")
        waiting = sum(
            notes[identifier].judged_by is not Decider.HUMAN for identifier in sample.spot_claim_ids
        )
        if waiting:
            raise AuditRefused(f"{waiting} spot-check judgements are due from the operator.")
    if result.refusal == "threshold_unset":
        raise AuditRefused("Set AUDIT_MAX_WRONG_SHARE or draw a whole audit with --fresh --all.")
    if result.refusal == "over_threshold":
        categories = Counter(notes[identifier].category for identifier in result.wrong)
        summary = ", ".join(f"{category}: {count}" for category, count in categories.items())
        raise AuditRefused(
            f"{len(result.wrong)} of {len(sample.claim_ids)} sampled claims were wrong. "
            f"The batch stays held. Defects: {summary}."
        )
    held = _held(session, batch)
    if {claim.id for claim in held} - set(sample.population_ids):
        raise AuditRefused("New claims await audit in this batch. Draw a fresh sample.")
    excluded = _wrong_in_history(session, batch)
    cleared = set(result.clear) - excluded
    for claim in held:
        note = notes.get(claim.id)
        if note is not None and _facts(session, claim) != note.facts_sha256:
            raise AuditRefused(
                f"Claim '{claim.slug}' changed since judgement. Draw a fresh sample."
            )
    count = 0
    for claim in held:
        note = notes.get(claim.id)
        if note is not None and not note.right:
            archive_claim(session, claim.slug, reason=f"{note.category}: {note.detail}", now=now)
        elif claim.id in cleared:
            claim.awaiting_audit_at = None
            claim.audit_cleared_at = now
            count += 1
    sample.released_at = now
    sample.max_wrong_share = max_wrong_share
    session.flush()
    return count
