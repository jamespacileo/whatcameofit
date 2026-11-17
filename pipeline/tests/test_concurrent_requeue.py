"""PostgreSQL row-lock ordering between a worker and the link-read requeue command."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from backfill_support import NOW
from test_link_reading import step
from thenwhat.db.models import LinkLead, WorkEntry
from thenwhat.domain import OutletKind, ReadOutcome, WorkOutcome
from thenwhat.work.ledger import requeue


@pytest.mark.parametrize("retry_first", [True, False])
def test_requeue_counts_only_reads_it_reopened(engine, retry_first):
    read = step()
    with Session(engine) as setup, setup.begin():
        lead = LinkLead(
            url="https://example.test/queued",
            url_key="example.test/queued",
            title="Synthetic lead",
            outlet="example.test",
            outlet_kind=OutletKind.GENERAL_NEWS,
            first_shared_at=NOW,
            read_outcome=ReadOutcome.CANNOT_BE_READ,
        )
        setup.add(lead)
        setup.flush()
        entry = WorkEntry(
            record_kind=read.record_kind,
            record_id=lead.id,
            step=read.name,
            step_version=read.version,
            outcome=WorkOutcome.LATER,
            reason="site_busy",
            attempts=0,
            requests_used=1,
            fingerprint="old",
            last_attempt_at=NOW,
            not_before=NOW,
        )
        setup.add(entry)
        setup.flush()
        lead_id, entry_id = lead.id, entry.id

    def retry(session):
        lead = session.scalars(
            select(LinkLead).where(LinkLead.id == lead_id).with_for_update()
        ).one()
        entry = session.get(WorkEntry, entry_id)
        lead.read_outcome = ReadOutcome.NOT_ONE_TREATMENT
        entry.outcome, entry.reason, entry.not_before = WorkOutcome.DONE, None, None
        entry.stale = False
        session.flush()

    def reopen(session):
        ids = requeue(session, read, reason="site_busy")
        read.made_due(session, ids)
        return ids

    ready = Event()
    pids = []

    def second():
        with Session(engine) as session, session.begin():
            pids.append(session.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            return reopen(session) if retry_first else retry(session)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with Session(engine) as first, first.begin():
                if retry_first:
                    retry(first)
                else:
                    assert reopen(first) == [lead_id]
                future = pool.submit(second)
                assert ready.wait(5)
                deadline = monotonic() + 5
                while not first.scalar(
                    text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": pids[0]}
                ):
                    assert not future.done() and monotonic() < deadline
                    sleep(0.005)
            assert future.result(timeout=5) == ([] if retry_first else None)
        with Session(engine) as checked:
            entry = checked.get(WorkEntry, entry_id)
            assert (entry.stale, entry.outcome, entry.reason) == (False, WorkOutcome.DONE, None)
            assert checked.get(LinkLead, lead_id).read_outcome is ReadOutcome.NOT_ONE_TREATMENT
    finally:
        with Session(engine) as clean, clean.begin():
            clean.execute(delete(WorkEntry).where(WorkEntry.id == entry_id))
            clean.execute(delete(LinkLead).where(LinkLead.id == lead_id))
