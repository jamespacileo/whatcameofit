"""Storing shared links as link leads: one lead per article address, one share per
place and time. Behavior: openspec link-leads.

Nothing here asks a platform or an outlet for anything: the posts come from a file on
the operator's disk. Loading the same file again adds nothing, so a load that was
stopped is simply run again.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from itertools import batched

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.backfill.ledger import mark_changed
from thenwhat.backfill.link_readers import SharedLink, Skip
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.backfill.steps import Step
from thenwhat.db.models import LinkLead, LinkShare

OpenSession = Callable[[], AbstractContextManager[Session]]

RECORD_KIND = "link_lead"
# How many posts are saved together. A load that stops loses at most this many.
POSTS_PER_TRANSACTION = 1000


@dataclass(slots=True)
class LoadReport:
    read: int = 0
    new_leads: int = 0
    # A share added to a lead that an earlier post had already made.
    added_shares: int = 0
    # A share that was stored by an earlier load of the same post.
    already_stored: int = 0
    skipped: Counter[Skip] = field(default_factory=Counter)


def outlet_of_key(key: str) -> str:
    """The outlet's domain, from an address in comparison form."""
    return key.split("/", 1)[0].split("?", 1)[0]


def store(
    session: Session,
    platform: str,
    post: SharedLink,
    steps: Sequence[Step],
    report: LoadReport,
) -> None:
    """Store one shared link: its lead if the address is new, and its share."""
    key = article_key(post.url)
    if key is None:
        report.skipped[Skip.UNUSABLE] += 1
        return
    outlet = outlet_of_key(key)
    lead_id = session.scalar(
        insert(LinkLead)
        .values(
            url=post.url,
            url_key=key,
            outlet=outlet,
            outlet_kind=kind_of(outlet),
            title=post.title,
            first_shared_at=post.shared_at,
        )
        .on_conflict_do_nothing(index_elements=[LinkLead.url_key])
        .returning(LinkLead.id)
    )
    is_new = lead_id is not None
    if not is_new:
        lead = session.scalars(
            select(LinkLead).where(LinkLead.url_key == key).with_for_update()
        ).one()
        lead_id = lead.id
        if post.shared_at < lead.first_shared_at:
            # The lead carries the title of its earliest share. Steps that read the
            # title are due again when it changes.
            lead.first_shared_at = post.shared_at
            if lead.title != post.title:
                lead.title = post.title
                session.flush()
                mark_changed(session, steps, RECORD_KIND, lead)
    share_id = session.scalar(
        insert(LinkShare)
        .values(
            link_lead_id=lead_id,
            platform=platform,
            community=post.community,
            shared_at=post.shared_at,
            score=post.score,
            item_number=post.item_number,
        )
        .on_conflict_do_nothing(constraint="uq_link_share_lead_place_time")
        .returning(LinkShare.id)
    )
    if is_new:
        report.new_leads += 1
    elif share_id is not None:
        report.added_shares += 1
    else:
        report.already_stored += 1


def load_links(
    open_session: OpenSession,
    platform: str,
    posts: Iterable[SharedLink | Skip],
    steps: Sequence[Step],
) -> LoadReport:
    """Store every post of a file that links to an address, and count the rest by the
    reason they were skipped. Posts are saved a thousand at a time."""
    report = LoadReport()
    for chunk in batched(posts, POSTS_PER_TRANSACTION):
        with open_session() as session:
            for post in chunk:
                report.read += 1
                if isinstance(post, Skip):
                    report.skipped[post] += 1
                else:
                    store(session, platform, post, steps, report)
    return report
