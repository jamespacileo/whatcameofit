"""What `thenwhat prepare` decides for a claim a read drafted, by how each of its steps
ended: characterisation tests.

These tests pin present behaviour for openspec change `one-work-runner`, task 1.2, at the
level `test_prepare.py` tests the command: its steps are faked by what each exited with
and said, with the fakes of `test_prepare.py`, and `resolve` itself with the fakes of
`test_cli_resolve.py`. A case an existing test asserts in full is not repeated here; it
is listed with that test.

Coverage, case -> test (this module unless a module is named):

  every step succeeds: approved by rule -> test_prepare.py::
    test_prepare_approves_a_reads_claim_only_when_every_step_succeeded
  the registry search fails: the claim stays pending
    -> test_a_claim_whose_registry_search_failed_stays_pending
  terms fail: the claim is still decided -> test_prepare.py::
    test_a_claim_whose_terms_failed_is_still_decided
  the substance lookup fails inside resolve: resolve still exits 0
    -> test_resolve_succeeds_when_the_substance_lookup_failed
  ... and prepare then decides the claim
    -> test_a_claim_whose_substance_lookup_failed_is_still_decided
"""

# CHANGES under one-work-runner:
# test_resolve_succeeds_when_the_substance_lookup_failed: the search is left unfinished.
# test_a_claim_whose_substance_lookup_failed_is_still_decided: the claim waits instead.
# test_prepare.py::test_a_claim_whose_terms_failed_is_still_decided: terms leave the
#   decision gate; the claim is decided and its terms are due again on the next run.

import re

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import test_cli_resolve
import test_prepare
import thenwhat.cli.prepare
from test_prepare import claim_with_articles, drafted_by_a_read
from thenwhat.claims.entry import add_claim, find_claim
from thenwhat.db.models import Claim, EntitySubstance
from thenwhat.domain import Decider, ReviewState

# The `prepare` command with its steps faked, and the `resolve` command with its sources
# faked, each as its own tests have them.
prepared = test_prepare.run
resolved = test_cli_resolve.run

# What `resolve` says when the substance lookup failed, as the fakes make it fail.
LOOKUP_FAILED = "Development codes were not looked up: rxnorm did not answer after 2 attempts."


def answering(monkeypatch: pytest.MonkeyPatch, command: str, exited: int, said: str) -> None:
    """Have one command of the faked steps exit and say what is given. Every step is
    still recorded by the fake the `prepared` fixture set."""
    faked = thenwhat.cli.prepare.run_step

    def run_step(arguments: list[str]) -> tuple[int, str]:
        answer = faked(arguments)
        return (exited, said) if arguments[0] == command else answer

    monkeypatch.setattr("thenwhat.cli.prepare.run_step", run_step)


def claim_of(session: Session, slug: str) -> Claim:
    claim = find_claim(session, slug)
    assert claim is not None
    return claim


def test_a_claim_whose_registry_search_failed_stays_pending(
    prepared, session: Session, monkeypatch: pytest.MonkeyPatch
):
    claim_with_articles(session, "unsearched", "https://news.example.org/a")
    drafted_by_a_read(session, "unsearched")
    answering(monkeypatch, "resolve", 1, "SourceUnavailable: the registry did not answer.")

    result, ran = prepared("prepare", "unsearched")

    # The command succeeds; the failed step is reported and the steps after it still run.
    assert result.exit_code == 0, result.output
    assert [step[0] for step in ran] == ["extract", "resolve", "fetch", "readings", "terms"]
    assert "resolve failed" in result.output
    assert "approved by rule" not in result.output
    claim = claim_of(session, "unsearched")
    assert (claim.review_state, claim.reviewed_by, claim.awaiting_audit_at) == (
        ReviewState.PENDING,
        None,
        None,
    )


def test_resolve_succeeds_when_the_substance_lookup_failed(resolved, session: Session):
    add_claim(
        session,
        slug="downvax-tooth-agenesis",
        headline="Vaccine regrows teeth",
        vertical="mouth-and-teeth",
        intervention="Downvax",
        indication="tooth agenesis",
    )

    result = resolved("resolve", "downvax-tooth-agenesis")

    assert result.exit_code == 0, result.output
    assert LOOKUP_FAILED in " ".join(result.output.split())
    assert session.scalars(select(EntitySubstance)).all() == []


def test_a_claim_whose_substance_lookup_failed_is_still_decided(
    prepared, session: Session, monkeypatch: pytest.MonkeyPatch
):
    claim_with_articles(session, "unlooked", "https://news.example.org/a")
    drafted_by_a_read(session, "unlooked")
    # `resolve` exits 0 when the substance lookup failed, and says so last.
    answering(monkeypatch, "resolve", 0, LOOKUP_FAILED)

    result, ran = prepared("prepare", "unlooked")

    assert result.exit_code == 0, result.output
    assert [step[0] for step in ran] == ["extract", "resolve", "fetch", "readings", "terms"]
    assert re.search(rf"resolve \(\d+s\): {re.escape(LOOKUP_FAILED)}", result.output)
    assert "resolve failed" not in result.output
    assert "approved by rule, now that its registries have been searched" in result.output
    # Decided with no substance record, so no claim for its substance could be found.
    claim = claim_of(session, "unlooked")
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    assert claim.awaiting_audit_at is not None
    assert session.scalars(select(EntitySubstance)).all() == []
