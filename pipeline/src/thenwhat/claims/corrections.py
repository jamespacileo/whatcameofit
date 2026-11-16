"""Corrections to which claim stands for a treatment, and to what its intervention is
called: merging a duplicate claim into the one that is kept, and renaming an
intervention. Behavior: openspec claims, "Merging duplicate claims" and "Renaming an
intervention".

What an article reported moves with a merge: the articles, their promises and reported
statements, the names of the intervention, and the papers, organisations and people an
article named. What a registry was found to say does not: the intervention's matches and
every evidence event stay with the merged claim, and the kept claim's registries are
searched again under the names it gained (design.md of the change `claim-merge-and-rename`
says why).
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    _DOSE,
    _HOW_GIVEN,
    EntryError,
    SlugTaken,
    claim_by_slug,
    find_article,
    find_claim,
    name_key,
    slug_for,
    tidy,
)
from thenwhat.db.models import (
    Claim,
    ClaimChange,
    Entity,
    EntityArticle,
    EntityMatch,
    EntitySubstance,
    LinkLead,
    LinkLeadLink,
    Promise,
    ReportedStatement,
    SourceArticle,
)
from thenwhat.domain import Decider, EntityType, NamedBy, ReviewState
from thenwhat.extract.names import is_a_class, is_a_name

MERGE = "merge"
RENAME = "rename"
# How a screening link names a claim (`backfill.link_screen.CLAIM`).
CLAIM_RECORD = "claim"
ORGANISATION_TYPES = (EntityType.INSTITUTION, EntityType.COMPANY)


class MergeRefused(EntryError):
    pass


class RenameRefused(EntryError):
    pass


# --- the entry rules for an intervention's name -----------------------------------

_BRACKETS = re.compile(r"[()\[\]]")
_SAYS_WHAT_FOR = re.compile(r"\bfor\b")
_POSSESSIVE_FIRST = re.compile(r"^\S+['’]s\s+\S")

NO_BRACKETS = "an intervention's name carries no brackets"
NO_DOSE = "an intervention's name carries no dose, schedule or form it is given in"
NO_MAKER = "an intervention's name does not say who makes it"
NOT_A_NAME = "a description or a class of treatments is not a name"


def name_refusal(name: str, makers: Iterable[str] = ()) -> str | None:
    """The entry rule a name for an intervention breaks, in words, or None when it
    breaks none. An intervention is entered by its name alone: no brackets, no dose or
    schedule, no maker, and not a description. `makers` are the companies the claim
    already names; a name that holds one of them beside other words names its maker."""
    key = name_key(name)
    if _BRACKETS.search(key):
        return NO_BRACKETS
    if _DOSE.search(key) or _HOW_GIVEN.search(key):
        return NO_DOSE
    # What a treatment is for is the indication's to say: "treatment for ..." names none.
    if not is_a_name(tidy(name)) or is_a_class(tidy(name)) or _SAYS_WHAT_FOR.search(key):
        return NOT_A_NAME
    words = key.split()
    for maker in makers:
        held = name_key(maker).split()
        if held and len(held) < len(words) and _holds(words, held):
            return NO_MAKER
    if _POSSESSIVE_FIRST.match(key):
        return NO_MAKER
    return None


def _holds(words: list[str], run: list[str]) -> bool:
    plain = [word.strip(".,;:'’").removesuffix("'s").removesuffix("’s") for word in words]
    return any(plain[at : at + len(run)] == run for at in range(len(plain) - len(run) + 1))


# --- shared lookups -----------------------------------------------------------------


def _intervention(session: Session, claim: Claim) -> Entity:
    entity = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).first()
    assert entity is not None, "every claim is created with its intervention entity"
    return entity


def _known(entity: Entity) -> set[str]:
    return {name_key(entity.name), *(name_key(synonym) for synonym in entity.synonyms)}


def _other_claim_covering(
    session: Session, name: str, indication: str, *, besides: Sequence[int]
) -> str | None:
    """Slug of a claim, other than these, that stands for this name and indication. A
    merged claim stands for nothing."""
    rows = session.execute(
        select(Claim.slug, Claim.indication, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(
            Entity.type == EntityType.INTERVENTION,
            Claim.merged_into_id.is_(None),
            Claim.id.not_in(besides),
        )
        .order_by(Claim.id)
    )
    wanted = name_key(name)
    for slug, condition, known_name, synonyms in rows:
        names = {name_key(known_name), *(name_key(synonym) for synonym in synonyms)}
        if wanted in names and name_key(condition) == name_key(indication):
            return slug
    return None


def _check_decider(by: Decider) -> None:
    if by not in (Decider.HUMAN, Decider.ASSISTANT):
        raise ValueError("A correction is decided by the operator or by an assistant.")


# --- merging ------------------------------------------------------------------------


@dataclass(slots=True)
class Merged:
    """What a merge did, for the operator."""

    kept: Claim
    merged: Claim
    articles_moved: int = 0
    # Articles the kept claim already had: the merged claim keeps its own copy.
    articles_already_there: int = 0
    promises_moved: int = 0
    statements_moved: int = 0
    entities_moved: int = 0
    leads_moved: int = 0
    names_gained: list[str] = field(default_factory=list)
    # Synonyms of the merged intervention that break an entry rule, and so were not
    # taken as synonyms of the kept one.
    names_left: list[str] = field(default_factory=list)
    # Why the two are held to be one treatment: a code of `SAME_BY_*`.
    same_by: str = ""
    # The kept claim now waits for the audit the merged claim was waiting for.
    kept_now_awaits_audit: bool = False
    # Approved registry records of the merged claim's intervention that the kept claim
    # does not hold approved, as "source id": to look for after the next search.
    to_find_again: list[str] = field(default_factory=list)


SAME_BY_NAME = "shared_name"
SAME_BY_SUBSTANCE = "same_substance_record"
SAME_BY_CODE = "shared_development_code"
SAME_BY_DECISION = "stated_by_the_decider"


def _same_treatment(session: Session, theirs: Entity, ours: Entity) -> str | None:
    """What shows the two interventions are one treatment, or None when nothing stored
    does: a name or synonym they share, the same record in the registry of substances,
    or a development code of one that the other is known by or also has."""
    if _known(theirs) & _known(ours):
        return SAME_BY_NAME
    mine, yours = session.get(EntitySubstance, ours.id), session.get(EntitySubstance, theirs.id)
    if (
        mine is not None
        and yours is not None
        and (mine.source_name, mine.external_id) == (yours.source_name, yours.external_id)
    ):
        return SAME_BY_SUBSTANCE
    my_codes = {name_key(code) for code in (mine.codes if mine is not None else [])}
    your_codes = {name_key(code) for code in (yours.codes if yours is not None else [])}
    if my_codes & your_codes or my_codes & _known(theirs) or your_codes & _known(ours):
        return SAME_BY_CODE
    return None


def merge_claims(
    session: Session,
    from_slug: str,
    into_slug: str,
    *,
    reason: str,
    by: Decider,
    now: datetime,
    different_indication_accepted: bool = False,
    same_treatment_accepted: bool = False,
    awaiting_audit_accepted: bool = False,
    drop_name: bool = False,
) -> Merged:
    """Fold one claim into another that stands for the same intervention and indication.

    The two must be shown to be one treatment by what is stored (a shared name, the same
    substance record, a shared development code), or the decider must state it with
    `same_treatment_accepted`; their indications must be equal, or the decider must
    state that with `different_indication_accepted`.

    Everything is checked before anything is changed, so a refusal changes nothing.
    The merged claim is archived and points at the kept claim; nothing is deleted, and
    every row the merge moved is written down so that `unmerge_claim` can put it back.
    A hold for audit is never dropped: when the merged claim awaits audit, the kept
    claim waits with it. `drop_name` leaves the merged claim's intervention name out of
    the kept claim's synonyms, for a name that is a description.
    """
    _check_decider(by)
    merged = claim_by_slug(session, from_slug)
    kept = claim_by_slug(session, into_slug)
    reason = tidy(reason)
    if merged.id == kept.id:
        raise MergeRefused("A claim cannot be merged into itself.")
    if not reason:
        raise MergeRefused("Give a reason for the merge. It is kept, and never published.")
    if merged.merged_into_id is not None:
        earlier = session.get(Claim, merged.merged_into_id)
        assert earlier is not None
        raise MergeRefused(f"Claim '{merged.slug}' was already merged into '{earlier.slug}'.")
    if kept.archived_at is not None:
        raise MergeRefused(
            f"Claim '{kept.slug}' is archived. Merge into a claim that stays on the site,"
            " or unarchive it first."
        )
    if kept.review_state is ReviewState.REJECTED:
        raise MergeRefused(f"Claim '{kept.slug}' was rejected and is never shown.")
    theirs, ours = _intervention(session, merged), _intervention(session, kept)
    same_by = _same_treatment(session, theirs, ours)
    if same_by is None and not same_treatment_accepted:
        raise MergeRefused(
            f"Nothing stored shows that '{theirs.name}' ({merged.slug}) and '{ours.name}'"
            f" ({kept.slug}) are one treatment: they share no name, synonym, substance"
            " record or development code. Two treatments for one indication are two"
            " claims. If they are one treatment, say so with --same-treatment-accepted"
            " and say in the reason how you know."
        )
    if name_key(merged.indication) != name_key(kept.indication) and (
        not different_indication_accepted
    ):
        raise MergeRefused(
            f"The indications differ: '{merged.slug}' is for '{merged.indication}' and"
            f" '{kept.slug}' is for '{kept.indication}'. A claim is one intervention for"
            " one indication. If they are one indication worded twice, say so with"
            " --different-indication-accepted and give the reason."
        )
    held = [claim.slug for claim in (merged, kept) if claim.awaiting_audit_at is not None]
    if held and not awaiting_audit_accepted:
        raise MergeRefused(
            f"Awaiting audit: {', '.join(held)}. Audit first (thenwhat audit list), or"
            " say so with --awaiting-audit-accepted: the kept claim then waits for the"
            " audit too, and is off the site until `thenwhat audit clear`."
        )

    gained, left = _names_to_gain(session, merged, kept, theirs, ours, drop_name=drop_name)
    result = Merged(
        kept=kept,
        merged=merged,
        names_gained=gained,
        names_left=left,
        same_by=same_by or SAME_BY_DECISION,
    )
    result.to_find_again = _approved_records_only_on(session, theirs, ours)
    # Every row the merge changes, so that it can be undone (`unmerge_claim`).
    record: dict[str, Any] = {
        "same_by": result.same_by,
        "names_gained": gained,
        "merged_was_archived": merged.archived_at is not None,
    }

    ours.synonyms = [*ours.synonyms, *gained]
    known_phrases = {name_key(phrase) for phrase in ours.search_phrases} | _known(ours)
    phrases = [p for p in theirs.search_phrases if name_key(p) not in known_phrases]
    ours.search_phrases = [*ours.search_phrases, *phrases]
    record["phrases_gained"] = phrases

    # Read before any article moves: a lead follows its article to the kept claim in
    # the database, and would no longer be found by the claim it pointed at.
    leads = list(
        session.scalars(
            select(LinkLead)
            .where(
                (LinkLead.claim_id == merged.id)
                | LinkLead.source_article_id.in_(
                    select(SourceArticle.id).where(SourceArticle.claim_id == merged.id)
                )
            )
            .order_by(LinkLead.id)
        )
    )
    now_at = _move_articles(session, merged, kept, result, record)
    _move_leads(session, leads, merged, kept, now_at, result, record)
    _move_entities(session, merged, kept, now_at, result, record)

    # A claim merged into the merged one earlier now leads to the kept claim, so an
    # address never leads through two claims.
    record["claims_repointed"] = []
    for earlier in session.scalars(select(Claim).where(Claim.merged_into_id == merged.id)):
        earlier.merged_into_id = kept.id
        record["claims_repointed"].append(earlier.id)
    if merged.archived_at is None:
        # A claim archived earlier keeps the day and the reason it was archived for.
        merged.archived_at = now
        merged.archive_reason = f"merged into {kept.slug}: {reason}"
    merged.merged_into_id = kept.id
    # A hold is never dropped by merging. The merged claim keeps its own, and the kept
    # claim, which now holds what was waiting to be audited, waits from the same time.
    if merged.awaiting_audit_at is not None and kept.awaiting_audit_at is None:
        kept.awaiting_audit_at = merged.awaiting_audit_at
        result.kept_now_awaits_audit = True
    record["kept_took_hold"] = result.kept_now_awaits_audit
    kept.registry_search_due_at = now
    session.add(
        ClaimChange(
            claim_id=merged.id,
            kind=MERGE,
            into_claim_id=kept.id,
            reason=reason,
            decided_by=by,
            decided_at=now,
            record=record,
        )
    )
    session.flush()
    return result


def _names_to_gain(
    session: Session, merged: Claim, kept: Claim, theirs: Entity, ours: Entity, *, drop_name: bool
) -> tuple[list[str], list[str]]:
    """The merged intervention's names the kept one gains, and its synonyms left out
    because they break an entry rule. Refuses when the name itself breaks one (the
    decider drops it explicitly), and when a third claim stands for a name."""
    if not drop_name:
        broken = name_refusal(theirs.name)
        if broken is not None:
            raise MergeRefused(
                f"'{theirs.name}', the intervention of '{merged.slug}', would become a"
                f" synonym, and every synonym is searched for in the registries: {broken}."
                " Leave it out with --drop-name."
            )
    known = _known(ours)
    gained: list[str] = []
    left: list[str] = []
    for name in [*([] if drop_name else [theirs.name]), *theirs.synonyms]:
        if name_key(name) in known:
            continue
        if name_refusal(name) is not None:
            left.append(tidy(name))
            continue
        other = _other_claim_covering(session, name, kept.indication, besides=[merged.id, kept.id])
        if other is not None:
            raise MergeRefused(
                f"Claim '{other}' also stands for '{name}' and '{kept.indication}'."
                " Merge that one first."
            )
        known.add(name_key(name))
        gained.append(tidy(name))
    return gained, left


def _approved_records_only_on(session: Session, theirs: Entity, ours: Entity) -> list[str]:
    def approved(entity: Entity) -> set[tuple[str, str]]:
        rows = session.execute(
            select(EntityMatch.source_name, EntityMatch.external_id).where(
                EntityMatch.entity_id == entity.id,
                EntityMatch.review_state == ReviewState.APPROVED,
            )
        )
        return {(source, external) for source, external in rows}

    return [
        f"{source} {external}" for source, external in sorted(approved(theirs) - approved(ours))
    ]


def _move_articles(
    session: Session, merged: Claim, kept: Claim, result: Merged, record: dict[str, Any]
) -> dict[int, int]:
    """Move the merged claim's articles, with their promises and reported statements.
    Returns, for each article the kept claim already had, the kept claim's own copy: the
    merged claim keeps its copy, and what was read from it moves to the kept one's where
    that does not have it."""
    now_at: dict[int, int] = {}
    moved_articles: list[int] = record.setdefault("articles", [])
    # Each as [id, the article it was read from].
    moved_promises: list[list[int]] = record.setdefault("promises", [])
    moved_statements: list[list[int]] = record.setdefault("statements", [])
    articles = list(
        session.scalars(
            select(SourceArticle)
            .where(SourceArticle.claim_id == merged.id)
            .order_by(SourceArticle.published_date, SourceArticle.id)
        )
    )
    for article in articles:
        own = find_article(session, kept, article.url)
        promises = list(
            session.scalars(select(Promise).where(Promise.source_article_id == article.id))
        )
        statements = list(
            session.scalars(
                select(ReportedStatement).where(ReportedStatement.source_article_id == article.id)
            )
        )
        if own is None:
            article.claim_id = kept.id
            # Written at once: the database holds each promise, statement and lead to
            # its article's claim, and moves them with the article.
            session.flush()
            moved_articles.append(article.id)
            for promise in promises:
                promise.claim_id = kept.id
                moved_promises.append([promise.id, article.id])
            for statement in statements:
                statement.claim_id = kept.id
                moved_statements.append([statement.id, article.id])
        else:
            now_at[article.id] = own.id
            result.articles_already_there += 1
            said = {
                name_key(description)
                for description in session.scalars(
                    select(Promise.description).where(Promise.source_article_id == own.id)
                )
            }
            for promise in promises:
                if name_key(promise.description) not in said:
                    promise.claim_id, promise.source_article_id = kept.id, own.id
                    said.add(name_key(promise.description))
                    moved_promises.append([promise.id, article.id])
            stated = set(
                session.scalars(
                    select(ReportedStatement.text_key).where(
                        ReportedStatement.source_article_id == own.id
                    )
                )
            )
            for statement in statements:
                if statement.text_key not in stated:
                    statement.claim_id, statement.source_article_id = kept.id, own.id
                    stated.add(statement.text_key)
                    moved_statements.append([statement.id, article.id])
        if kept.first_reported_date is None or article.published_date < kept.first_reported_date:
            kept.first_reported_date = article.published_date
    result.articles_moved = len(moved_articles)
    result.promises_moved = len(moved_promises)
    result.statements_moved = len(moved_statements)
    session.flush()
    return now_at


def _move_leads(
    session: Session,
    leads: list[LinkLead],
    merged: Claim,
    kept: Claim,
    now_at: dict[int, int],
    result: Merged,
    record: dict[str, Any],
) -> None:
    """Point at the kept claim every link lead that pointed at the merged one, and every
    claim that screening linked a lead to. Only the pointers move: what a lead's read
    found (`read_outcome`, `read_detail`) stays as the read left it, so the lead that
    drafted the merged claim still says so, and the record of the merge names each lead."""
    # Each as [id, the claim it pointed at, the article it pointed at].
    moved: list[list[int | None]] = record.setdefault("leads", [])
    for lead in leads:
        moved.append([lead.id, lead.claim_id, lead.source_article_id])
        lead.claim_id = kept.id
        if lead.source_article_id in now_at:
            lead.source_article_id = now_at[lead.source_article_id]
    result.leads_moved = len(moved)
    linked = {
        (link.link_lead_id, link.reason)
        for link in session.scalars(
            select(LinkLeadLink).where(
                LinkLeadLink.record_kind == CLAIM_RECORD, LinkLeadLink.record_id == kept.id
            )
        )
    }
    repointed: list[int] = record.setdefault("lead_links", [])
    for link in session.scalars(
        select(LinkLeadLink).where(
            LinkLeadLink.record_kind == CLAIM_RECORD, LinkLeadLink.record_id == merged.id
        )
    ):
        # One the kept claim already has for that lead and reason stays where it is.
        if (link.link_lead_id, link.reason) not in linked:
            link.record_id = kept.id
            repointed.append(link.id)
    session.flush()


def _twin(entity: Entity, among: list[Entity]) -> Entity | None:
    """The kept claim's entity that is the same paper or organisation: the same DOI, or
    a name they share. Never a person: two people are not one because of a name."""
    if entity.type is EntityType.PERSON:
        return None
    names = _known(entity)
    for other in among:
        same_kind = other.type is entity.type or (
            other.type in ORGANISATION_TYPES and entity.type in ORGANISATION_TYPES
        )
        if not same_kind:
            continue
        same_doi = bool(entity.doi) and (entity.doi or "").lower() == (other.doi or "").lower()
        if same_doi or names & _known(other):
            return other
    return None


def _move_entities(
    session: Session,
    merged: Claim,
    kept: Claim,
    now_at: dict[int, int],
    result: Merged,
    record: dict[str, Any],
) -> None:
    """Move the papers, organisations and people an article named, with the registry
    records that say who or what each is. For one the kept claim already has, the kept
    claim's entity gains its other names, its article links and the registry records it
    lacks; the merged claim's entity stays. One only a registry record named (a trial's
    sponsor) stays, and comes back when the kept claim's search finds that trial. A
    person the kept claim already has by name stays too: nothing says they are one."""
    theirs = list(
        session.scalars(
            select(Entity)
            .where(Entity.claim_id == merged.id, Entity.type != EntityType.INTERVENTION)
            .order_by(Entity.id)
        )
    )
    ours = list(
        session.scalars(
            select(Entity).where(Entity.claim_id == kept.id, Entity.type != EntityType.INTERVENTION)
        )
    )
    moved: list[list[Any]] = record.setdefault("entities", [])  # [id, was origin paper]
    twins: list[dict[str, Any]] = record.setdefault("twins", [])
    links_removed: list[list[int]] = record.setdefault("entity_articles_removed", [])
    links_added: list[list[int]] = record.setdefault("entity_articles_added", [])
    matches_moved: list[list[int]] = record.setdefault("matches", [])  # [id, entity it was on]
    has_origin_paper = any(entity.is_origin_paper for entity in ours)
    for entity in theirs:
        if NamedBy.ARTICLE.value not in entity.named_by:
            continue
        if entity.type is EntityType.PERSON and any(
            other.type is EntityType.PERSON and _known(other) & _known(entity) for other in ours
        ):
            continue
        links = list(
            session.scalars(select(EntityArticle).where(EntityArticle.entity_id == entity.id))
        )
        twin = _twin(entity, ours)
        if twin is None:
            moved.append([entity.id, entity.is_origin_paper])
            if entity.is_origin_paper and has_origin_paper:
                entity.is_origin_paper = False
                session.flush()  # cleared before it joins a claim that has one
            has_origin_paper = has_origin_paper or entity.is_origin_paper
            entity.claim_id = kept.id
            ours.append(entity)
            destination = entity
        else:
            known = _known(twin)
            change: dict[str, Any] = {"id": twin.id, "names": [], "marked": False, "doi": False}
            for name in [entity.name, *entity.synonyms]:
                if name_key(name) not in known:
                    twin.synonyms = [*twin.synonyms, name]
                    known.add(name_key(name))
                    change["names"].append(name)
            if NamedBy.ARTICLE.value not in twin.named_by:
                twin.named_by = [*twin.named_by, NamedBy.ARTICLE.value]
                change["marked"] = True
            if twin.doi is None and entity.doi and twin.type is EntityType.PAPER:
                twin.doi = entity.doi
                change["doi"] = True
            twins.append(change)
            # The records that say which paper or organisation this is go to the kept
            # claim's entity, where it does not have that record already.
            has = {
                (source, external)
                for source, external in session.execute(
                    select(EntityMatch.source_name, EntityMatch.external_id).where(
                        EntityMatch.entity_id == twin.id
                    )
                )
            }
            for match in session.scalars(
                select(EntityMatch).where(EntityMatch.entity_id == entity.id)
            ):
                if (match.source_name, match.external_id) not in has:
                    matches_moved.append([match.id, entity.id])
                    match.entity_id = twin.id
            destination = twin
        session.flush()
        for link in links:
            article_id = now_at.get(link.source_article_id, link.source_article_id)
            if (destination.id, article_id) == (link.entity_id, link.source_article_id):
                continue
            links_removed.append([link.entity_id, link.source_article_id])
            session.delete(link)
            session.flush()
            if session.get(EntityArticle, (destination.id, article_id)) is None:
                session.add(EntityArticle(entity_id=destination.id, source_article_id=article_id))
                links_added.append([destination.id, article_id])
                session.flush()
    result.entities_moved = len(moved)


# --- undoing a merge ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Unmerged:
    claim: Claim
    kept: Claim
    articles_back: int
    names_removed: list[str]
    # The claim came back archived, because it was archived before it was merged.
    still_archived: bool
    # The kept claim's hold, taken with the merge, was let go with what it was for.
    kept_hold_released: bool


def unmerge_claim(
    session: Session, slug: str, *, reason: str, by: Decider, now: datetime
) -> Unmerged:
    """Undo a merge: every row the merge moved goes back to the claim it was merged
    from, the kept claim loses the names it gained, and the claim stands for its
    intervention again. Whatever either claim gained since stays where it is, and so do
    the registry records found for the kept claim since under the names it now loses:
    its registry search is due, and those are for the operator to look at."""
    _check_decider(by)
    claim = claim_by_slug(session, slug)
    reason = tidy(reason)
    if claim.merged_into_id is None:
        raise MergeRefused(f"Claim '{slug}' is not merged into another.")
    if not reason:
        raise MergeRefused("Give a reason for undoing the merge. It is kept, never published.")
    now_in = session.get(Claim, claim.merged_into_id)
    assert now_in is not None
    change = session.scalars(
        select(ClaimChange)
        .where(
            ClaimChange.claim_id == claim.id,
            ClaimChange.kind == MERGE,
            ClaimChange.undone_at.is_(None),
        )
        .order_by(ClaimChange.id.desc())
    ).first()
    assert change is not None and change.record is not None, "every merge is written down"
    if change.into_claim_id != now_in.id:
        via = session.get(Claim, change.into_claim_id)
        assert via is not None
        raise MergeRefused(
            f"Claim '{slug}' was merged into '{via.slug}', which was then merged into"
            f" '{now_in.slug}'. Undo that merge first: thenwhat claim unmerge {via.slug}"
        )
    kept, record = now_in, change.record
    other = None
    for name in [n for e in [_intervention(session, claim)] for n in (e.name, *e.synonyms)]:
        other = other or _other_claim_covering(
            session, name, claim.indication, besides=[claim.id, kept.id]
        )
    if other is not None:
        raise MergeRefused(
            f"Claim '{other}' now stands for a name of '{slug}' and its indication."
            " Two claims cannot stand for one name."
        )

    def here(model: Any, ids: list[int]) -> list[Any]:
        return list(session.scalars(select(model).where(model.id.in_(ids)))) if ids else []

    # Entity links first: they are put back as they were before articles go home.
    for entity_id, article_id in record["entity_articles_added"]:
        link = session.get(EntityArticle, (entity_id, article_id))
        if link is not None:
            session.delete(link)
    session.flush()
    for entity_id, article_id in record["entity_articles_removed"]:
        if session.get(EntityArticle, (entity_id, article_id)) is None:
            session.add(EntityArticle(entity_id=entity_id, source_article_id=article_id))
    was_on = dict(record["matches"])
    for match in here(EntityMatch, list(was_on)):
        match.entity_id = was_on[match.id]
    for twin_change in record["twins"]:
        twin = session.get(Entity, twin_change["id"])
        if twin is None:
            continue
        gone = {name_key(name) for name in twin_change["names"]}
        twin.synonyms = [s for s in twin.synonyms if name_key(s) not in gone]
        if twin_change["marked"]:
            twin.named_by = [mark for mark in twin.named_by if mark != NamedBy.ARTICLE.value]
        if twin_change["doi"]:
            twin.doi = None
    was_origin = dict(record["entities"])
    for entity in here(Entity, list(was_origin)):
        if entity.claim_id == kept.id:
            entity.claim_id = claim.id
    session.flush()
    for entity in here(Entity, [i for i, origin in was_origin.items() if origin]):
        if entity.claim_id == claim.id:
            entity.is_origin_paper = True

    articles = [a for a in here(SourceArticle, record["articles"]) if a.claim_id == kept.id]
    for article in articles:
        article.claim_id = claim.id
    # Written at once, as in the merge: what was read from an article follows it.
    session.flush()
    for model, key in ((Promise, "promises"), (ReportedStatement, "statements")):
        read_from = dict(record[key])
        for row in here(model, list(read_from)):
            if row.claim_id == kept.id:
                row.claim_id, row.source_article_id = claim.id, read_from[row.id]
    for lead_id, claim_id, article_id in record["leads"]:
        lead = session.get(LinkLead, lead_id)
        if lead is not None and lead.claim_id == kept.id:
            lead.claim_id, lead.source_article_id = claim_id, article_id
    for link in here(LinkLeadLink, record["lead_links"]):
        if link.record_id == kept.id:
            link.record_id = claim.id
    for earlier in here(Claim, record["claims_repointed"]):
        if earlier.merged_into_id == kept.id:
            earlier.merged_into_id = claim.id

    ours = _intervention(session, kept)
    removed = {name_key(name) for name in record["names_gained"]}
    names_removed = [s for s in ours.synonyms if name_key(s) in removed]
    ours.synonyms = [s for s in ours.synonyms if name_key(s) not in removed]
    phrases = {name_key(phrase) for phrase in record["phrases_gained"]}
    ours.search_phrases = [p for p in ours.search_phrases if name_key(p) not in phrases]
    session.flush()
    kept.first_reported_date = session.scalar(
        select(func.min(SourceArticle.published_date)).where(SourceArticle.claim_id == kept.id)
    )
    kept.registry_search_due_at = now
    # The hold the kept claim took with the merge was for what has now gone back. One
    # an audit has cleared since stays cleared; the claim keeps its own hold throughout.
    released = bool(record["kept_took_hold"]) and kept.awaiting_audit_at is not None
    if released:
        kept.awaiting_audit_at = None

    claim.merged_into_id = None
    still_archived = bool(record["merged_was_archived"])
    if not still_archived:
        claim.archived_at = None
        claim.archive_reason = None
    claim.registry_search_due_at = now
    change.undone_at, change.undone_by, change.undone_reason = now, by, reason
    session.flush()
    return Unmerged(claim, kept, len(articles), names_removed, still_archived, released)


# --- renaming -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Renamed:
    claim: Claim
    entity: Entity
    old_name: str
    kept_as_synonym: bool
    # The slug the claim had, when the rename made it a new one.
    old_slug: str | None


def rename_intervention(
    session: Session,
    claim_slug: str,
    old_name: str,
    new_name: str,
    *,
    by: Decider,
    now: datetime,
    old_is_description: bool = False,
    reslug: bool = False,
) -> Renamed:
    """Correct what a claim's intervention is called. The old name stays as a synonym
    unless it is a description. The claim's registries are due to be searched again.
    With `reslug` the slug is made again by rule from the new name, and the old address
    leads to the new one."""
    _check_decider(by)
    claim = claim_by_slug(session, claim_slug)
    if claim.merged_into_id is not None:
        kept = session.get(Claim, claim.merged_into_id)
        assert kept is not None
        raise RenameRefused(
            f"Claim '{claim.slug}' was merged into '{kept.slug}'. Rename that claim's"
            " intervention instead."
        )
    entity = _intervention(session, claim)
    if name_key(entity.name) != name_key(old_name):
        raise RenameRefused(
            f"The intervention of '{claim.slug}' is called '{entity.name}', not '{tidy(old_name)}'."
        )
    new_name = tidy(new_name)
    if not new_name:
        raise RenameRefused("The new name is required.")
    if new_name == entity.name:
        raise RenameRefused(f"The intervention of '{claim.slug}' is already called '{new_name}'.")
    makers = [
        name
        for company in session.scalars(
            select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.COMPANY)
        )
        for name in (company.name, *company.synonyms)
    ]
    broken = name_refusal(new_name, makers)
    if broken is not None:
        raise RenameRefused(f"'{new_name}' is refused: {broken}.")
    other = _other_claim_covering(session, new_name, claim.indication, besides=[claim.id])
    if other is not None:
        raise RenameRefused(
            f"Claim '{other}' already stands for '{new_name}' and '{claim.indication}'."
            f" Two claims for one treatment are merged, not renamed:"
            f' thenwhat claim merge {claim.slug} {other} --reason "..."'
        )
    old = entity.name
    same_name = name_key(old) == name_key(new_name)
    keep = not old_is_description and not same_name
    if keep:
        broken = name_refusal(old, makers)
        if broken is not None:
            raise RenameRefused(
                f"'{old}' would stay as a synonym, and every synonym is searched for in"
                f" the registries: {broken}. Drop it with --old-is-description."
            )

    old_slug = _reslug(session, claim, new_name) if reslug else None

    synonyms = [
        s for s in entity.synonyms if name_key(s) not in (name_key(new_name), name_key(old))
    ]
    entity.synonyms = [*synonyms, old] if keep else synonyms
    entity.name = new_name
    claim.registry_search_due_at = now
    # A slug is written down as a former slug once: a claim that leaves the same slug a
    # second time already has the change that says so.
    recorded = old_slug is not None and session.scalar(
        select(ClaimChange.id).where(ClaimChange.former_slug == old_slug)
    )
    former_slug = old_slug if claim.published_at is not None and not recorded else None
    session.add(
        ClaimChange(
            claim_id=claim.id,
            kind=RENAME,
            old_name=old,
            new_name=new_name,
            former_slug=former_slug,
            decided_by=by,
            decided_at=now,
        )
    )
    session.flush()
    return Renamed(claim, entity, old, keep, old_slug)


def _reslug(session: Session, claim: Claim, new_name: str) -> str | None:
    """Give the claim the slug the rule makes from its new name. Returns the slug it
    had, or None when the rule makes the same one. A slug the claim itself had before is
    taken back, and the change that recorded it as a former slug is left as it was
    written; any other slug in use is refused."""
    new_slug = slug_for(new_name, claim.indication)
    if new_slug == claim.slug:
        return None
    if find_claim(session, new_slug) is not None:
        raise SlugTaken(
            f"The slug '{new_slug}', made by rule from the new name, belongs to another"
            " claim. Rename without --reslug, or merge the two claims."
        )
    former = session.scalars(
        select(ClaimChange).where(ClaimChange.former_slug == new_slug)
    ).one_or_none()
    if former is not None and former.claim_id != claim.id:
        raise SlugTaken(
            f"The slug '{new_slug}', made by rule from the new name, was another"
            " claim's address and still leads to it."
        )
    old_slug, claim.slug = claim.slug, new_slug
    session.flush()
    return old_slug


# --- addresses that moved -------------------------------------------------------------


def moved_addresses(session: Session) -> list[tuple[str, Claim]]:
    """Every published address that no longer has a page of its own, with the claim it
    leads to: a merged claim's slug with the claim it was merged into, and a slug a
    rename replaced with the renamed claim, or the claim that one was merged into. In
    slug order. Whether the claim it leads to is on the site is the export's to say."""
    moved: dict[str, Claim] = {}
    merged = session.scalars(
        select(Claim).where(Claim.merged_into_id.is_not(None), Claim.published_at.is_not(None))
    )
    for claim in merged:
        kept = session.get(Claim, claim.merged_into_id)
        assert kept is not None
        moved[claim.slug] = kept
    renames = session.execute(
        select(ClaimChange.former_slug, Claim)
        .join(Claim, Claim.id == ClaimChange.claim_id)
        .where(ClaimChange.former_slug.is_not(None))
    )
    for former_slug, claim in renames:
        if former_slug == claim.slug:
            continue  # the claim has taken its former slug back
        leads_to = session.get(Claim, claim.merged_into_id) if claim.merged_into_id else claim
        assert leads_to is not None and former_slug is not None
        moved[former_slug] = leads_to
    return sorted(moved.items())
