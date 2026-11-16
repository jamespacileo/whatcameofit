"""Bringing stored link leads to the current form of the address key, and merging the
leads that turn out to be one article. Behavior: openspec address-identity, "Stored
leads follow the address key".

Nothing here asks a source or a model, and nothing it does makes a lead due again for a
step that does: a lead that was scored or read keeps its entry, because its article is
the one it was. Only steps that ask nothing, such as screening, are due again.
"""

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from sqlalchemy import delete, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.address import KEY_VERSION, article_key
from thenwhat.backfill.errors import KeysOutOfDate
from thenwhat.backfill.ledger import find_entry, fingerprint
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.backfill.steps import NO_SOURCE, Step
from thenwhat.db.models import LinkLead, LinkLeadLabel, LinkLeadLink, LinkShare, WorkEntry

OpenSession = Callable[[], AbstractContextManager[Session]]

RECORD_KIND = "link_lead"
# How many leads are brought up to date together. A run that stops loses at most these.
LEADS_PER_TRANSACTION = 500


@dataclass(slots=True)
class RekeyReport:
    # Leads keyed under an earlier form when the run began looking at them.
    checked: int = 0
    # The key is the same under the current form.
    unchanged: int = 0
    # The key changed and no other lead had it.
    rekeyed: int = 0
    # Another lead had the new key: the two were one article and are now one lead.
    merged: int = 0
    shares_moved: int = 0
    # Pairs of claims that two merged leads had each made or joined. Nothing is done
    # to a claim here: the operator compares them and archives one if they are one.
    claims_to_compare: list[tuple[int, int]] = field(default_factory=list)


def leads_behind(session: Session) -> int:
    """How many link leads are keyed under an earlier form of the address key."""
    return (
        session.scalar(
            select(func.count()).select_from(LinkLead).where(LinkLead.url_key_version < KEY_VERSION)
        )
        or 0
    )


def refuse_stale_keys(session: Session) -> None:
    """Refuse while a stored lead is keyed under an earlier form: an article loaded or
    looked up under the current form would not find it."""
    stale = session.scalar(
        select(LinkLead.id).where(LinkLead.url_key_version < KEY_VERSION).limit(1)
    )
    if stale is not None:
        raise KeysOutOfDate(
            f"{leads_behind(session):,} link leads were keyed under an earlier form of the "
            "address key. Run `thenwhat backfill rekey-links --apply` first; it asks no "
            "source and no model."
        )


def survey(session: Session) -> RekeyReport:
    """What bringing the leads up to date would do, without doing it. Two leads behind
    that would meet each other are counted as one merge."""
    report = RekeyReport()
    seen: set[str] = set()
    behind = session.execute(
        select(LinkLead.url, LinkLead.url_key)
        .where(LinkLead.url_key_version < KEY_VERSION)
        .order_by(LinkLead.id)
        .execution_options(yield_per=5000)
    )
    changed: list[str] = []
    for url, old in behind:
        report.checked += 1
        key = article_key(url) or old
        if key == old:
            report.unchanged += 1
            seen.add(key)
        else:
            changed.append(key)
    for start in range(0, len(changed), 5000):
        seen.update(
            session.scalars(
                select(LinkLead.url_key).where(LinkLead.url_key.in_(changed[start : start + 5000]))
            )
        )
    for key in changed:
        if key in seen:
            report.merged += 1
        else:
            report.rekeyed += 1
            seen.add(key)
    return report


def _progress(lead: LinkLead) -> tuple[bool, bool, bool, int]:
    """How far a lead has come. Of two leads for one article the one that has come
    furthest is kept, so that nothing paid for is thrown away; the older one on a tie."""
    return (
        lead.read_outcome is not None,
        lead.triage_score is not None,
        lead.screen_outcome is not None,
        -lead.id,
    )


def _fingerprints(steps: Sequence[Step], lead: LinkLead) -> dict[str, str]:
    return {
        step.name: fingerprint(step.inputs(lead))
        for step in steps
        if step.record_kind == RECORD_KIND
    }


def _keep_entries(
    session: Session, steps: Sequence[Step], lead: LinkLead, before: dict[str, str]
) -> None:
    """After a lead's key, outlet or first share changed. A step that asks nothing is due
    again when what it reads is different. A step that asks a source or a model keeps
    its entry, now for the lead as it is: the article is the same one, and asking again
    would pay twice for one answer."""
    for step in steps:
        if step.record_kind != RECORD_KIND:
            continue
        entry = find_entry(session, step, lead)
        if entry is None:
            continue
        now = fingerprint(step.inputs(lead))
        if step.source == NO_SOURCE:
            if entry.fingerprint != now:
                entry.stale = True
        elif not entry.stale and entry.fingerprint == before[step.name]:
            entry.fingerprint = now
    session.flush()


def _merge(session: Session, kept: LinkLead, gone: LinkLead, report: RekeyReport) -> None:
    """Move what belongs to one lead onto the other and remove it. A share both leads
    hold is kept once; a label is kept unless the same reader labelled both."""
    moved = session.execute(
        insert(LinkShare)
        .from_select(
            ["link_lead_id", "platform", "community", "shared_at", "score", "item_number"],
            select(
                literal(kept.id),
                LinkShare.platform,
                LinkShare.community,
                LinkShare.shared_at,
                LinkShare.score,
                LinkShare.item_number,
            ).where(LinkShare.link_lead_id == gone.id),
        )
        .on_conflict_do_nothing(constraint="uq_link_share_lead_place_time")
        .returning(LinkShare.id)
    ).all()
    report.shares_moved += len(moved)
    session.execute(delete(LinkShare).where(LinkShare.link_lead_id == gone.id))
    labelled = select(LinkLeadLabel.labelled_by).where(LinkLeadLabel.link_lead_id == kept.id)
    session.execute(
        update(LinkLeadLabel)
        .where(LinkLeadLabel.link_lead_id == gone.id, LinkLeadLabel.labelled_by.not_in(labelled))
        .values(link_lead_id=kept.id)
    )
    session.execute(delete(LinkLeadLabel).where(LinkLeadLabel.link_lead_id == gone.id))
    session.execute(delete(LinkLeadLink).where(LinkLeadLink.link_lead_id == gone.id))
    session.execute(
        delete(WorkEntry).where(
            WorkEntry.record_kind == RECORD_KIND, WorkEntry.record_id == gone.id
        )
    )
    if kept.claim_id and gone.claim_id and kept.claim_id != gone.claim_id:
        report.claims_to_compare.append(
            (min(kept.claim_id, gone.claim_id), max(kept.claim_id, gone.claim_id))
        )
    kept.first_shared_at = min(kept.first_shared_at, gone.first_shared_at)
    # Deleted here and now: the kept lead may be about to take the key this one holds.
    session.execute(delete(LinkLead).where(LinkLead.id == gone.id))
    session.expunge(gone)
    report.merged += 1


def rekey(session: Session, steps: Sequence[Step], lead: LinkLead, report: RekeyReport) -> LinkLead:
    """Bring one lead to the current form of the key, merging it with the lead that
    already has that key if there is one. Returns the lead that remains."""
    report.checked += 1
    # An address the current form gives no key keeps the one it has.
    key = article_key(lead.url) or lead.url_key
    if key == lead.url_key:
        lead.url_key_version = KEY_VERSION
        report.unchanged += 1
        return lead
    other = session.scalars(
        select(LinkLead).where(LinkLead.url_key == key).with_for_update()
    ).one_or_none()
    kept = lead if other is None else max(lead, other, key=_progress)
    before = _fingerprints(steps, kept)
    if other is None:
        report.rekeyed += 1
    else:
        _merge(session, kept, other if kept is lead else lead, report)
    if kept is lead:
        outlet = key.split("/", 1)[0].split("?", 1)[0]
        lead.url_key = key
        lead.outlet = outlet
        lead.outlet_kind = kind_of(outlet)
        lead.url_key_version = KEY_VERSION
    session.flush()
    _keep_entries(session, steps, kept, before)
    return kept


def rekey_links(open_session: OpenSession, steps: Sequence[Step]) -> RekeyReport:
    """Bring every lead keyed under an earlier form up to date, five hundred to a
    transaction. A run that was stopped is simply run again: a lead that is up to date
    is not looked at twice."""
    report = RekeyReport()
    while True:
        with open_session() as session:
            behind = session.scalars(
                select(LinkLead.id)
                .where(LinkLead.url_key_version < KEY_VERSION)
                .order_by(LinkLead.id)
                .limit(LEADS_PER_TRANSACTION)
            ).all()
            if not behind:
                return report
            for lead_id in behind:
                lead = session.scalars(
                    select(LinkLead)
                    .where(LinkLead.id == lead_id, LinkLead.url_key_version < KEY_VERSION)
                    .with_for_update()
                ).one_or_none()
                # Gone or up to date already: merged with an earlier lead of this batch.
                if lead is not None:
                    rekey(session, steps, lead, report)
