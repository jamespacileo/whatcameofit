"""What `thenwhat prepare` decides for a claim a read drafted, by how each part of its
preparation ended: characterisation tests.

Written for openspec change `one-work-runner`, task 1.2, against the process-per-step
runner, and kept, rewritten for the steps of the work ledger that replaced it, for the
cases that change made. A case an existing test asserts in full is not repeated here; it
is listed with that test.

Coverage, case -> test (this module unless a module is named):

  every step succeeds: approved by rule -> test_prepare.py::
    test_prepare_works_through_every_step_and_decides_a_reads_draft
  the registry search fails: the claim stays pending
    -> test_a_claim_whose_registry_search_failed_stays_pending
  terms fail: the claim is decided, and its terms are due again -> test_claim_steps.py::
    test_a_claim_whose_terms_failed_is_decided_and_its_terms_are_due_next_run
  the substance lookup fails inside resolve: the search is left unfinished
    -> test_resolve_leaves_the_search_unfinished_when_the_substance_lookup_failed
  ... and prepare then leaves the claim waiting
    -> test_a_claim_whose_substance_lookup_failed_waits
"""

# LANDED under one-work-runner (task 7, 2026-11-17):
# test_resolve_leaves_the_search_unfinished_when_the_substance_lookup_failed: `resolve`
#   exited 0 when the substance lookup failed; the lookup is now a step of its own, put
#   off, the trial search waits for it, and the command exits 1.
# test_a_claim_whose_substance_lookup_failed_waits: the claim was decided on a search
#   that did not run; it now waits until the lookup finishes.
# test_claim_steps.py::test_a_claim_whose_terms_failed_is_decided_and_its_terms_are_due_next_run:
#   terms left the decision gate before this change; now they also stay due, and the
#   next run proposes them, for a decided claim as for one that is not.

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import test_cli_resolve
from claim_support import (
    SLUG,
    Registry,
    Sources,
    Substances,
    drafted_by_a_read,
    entry,
    new_claim,
    prepare,
)
from thenwhat.db.models import EntitySubstance
from thenwhat.domain import ReviewState, WorkOutcome
from thenwhat.sources.base import SourceUnavailable

# The `resolve` command with its sources faked, as its own tests have it.
resolved = test_cli_resolve.run


def test_a_claim_whose_registry_search_failed_stays_pending(session: Session):
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)

    prepare(session, Sources(Registry(down=True)))

    assert entry(session, "claim_trials", claim).outcome is WorkOutcome.LATER
    assert (claim.review_state, claim.reviewed_by, claim.awaiting_audit_at) == (
        ReviewState.PENDING,
        None,
        None,
    )


def test_resolve_leaves_the_search_unfinished_when_the_substance_lookup_failed(
    resolved, session: Session, monkeypatch: pytest.MonkeyPatch
):
    class Down(test_cli_resolve.Substances):
        def substances_named(self, name: str):
            raise SourceUnavailable("gsrs did not answer after 4 attempts.")

    monkeypatch.setattr("thenwhat.cli.resolve.make_substances", lambda s: Down())

    result = resolved("resolve", test_cli_resolve.SLUG)

    said = " ".join(result.output.split())
    assert result.exit_code == 1
    assert "claim_substance put off until" in said and "gsrs did not answer" in said
    assert "claim_trials did not run: an earlier step has not finished." in said
    assert session.scalars(select(EntitySubstance)).all() == []


def test_a_claim_whose_substance_lookup_failed_waits(session: Session):
    claim = new_claim(session)
    drafted_by_a_read(session, SLUG)

    prepare(session, Sources(substances=Substances(down=True)))

    assert entry(session, "claim_substance", claim).outcome is WorkOutcome.LATER
    assert claim.review_state is ReviewState.PENDING
    assert session.scalars(select(EntitySubstance)).all() == []
