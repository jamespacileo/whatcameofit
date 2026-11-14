"""Registry numbers and papers an article's page gives, tested through
`candidates_named_in_article` on a real database with a fake registry, literature
source and decision backend.

Scenario names are from openspec lead-reading. The papers and trials are made up.
"""

import pytest
from sqlalchemy.orm import Session

from test_related_research import (
    NOW,
    PHRASE_SEARCH,
    SLUG,
    Broken,
    FakePapers,
    Reading,
    Registry,
    find,
    new_claim,
    paper,
    paper_matches,
)
from thenwhat.db.models import Claim, EntityMatch
from thenwhat.decide.core import DecisionFailed
from thenwhat.domain import Decider, ReviewState
from thenwhat.resolve.named import candidates_named_in_article
from thenwhat.resolve.papers import rescore_papers
from thenwhat.resolve.reasons import NAMED_IN_ARTICLE
from thenwhat.review.queue import pending_items

TRIAL = "NCT04184622"
DOI = "10.1000/named"
NAMED = FakePapers({"x": [paper(DOI, "Median nerve stimulation for tics")]})


def named(session: Session, claim: Claim, *, backend=None, registry=None, papers=NAMED, **rules):
    return candidates_named_in_article(
        session,
        claim,
        registry_numbers=rules.pop("registry_numbers", [TRIAL]),
        dois=rules.pop("dois", [DOI]),
        registry=registry or Registry(),
        papers=papers,
        backend=backend or Reading(default=0.7),
        now=NOW,
        **rules,
    )


def test_an_article_that_links_its_trial_gives_a_pending_scored_candidate(session: Session):
    """Scenario: An article that links its trial"""
    claim = new_claim(session)
    registry = Registry()

    trial, cited = named(session, claim, registry=registry, registry_numbers=["nct04184622", TRIAL])

    assert (trial.source_name, trial.external_id) == ("clinicaltrials.gov", TRIAL)
    assert trial.reasons == [NAMED_IN_ARTICLE]
    assert trial.score == pytest.approx(0.7)
    assert trial.review_state is ReviewState.PENDING
    assert trial.record_summary == "A trial. For: Tourette Syndrome."
    assert (cited.source_name, cited.external_id) == ("openalex", DOI)
    assert cited.reasons[-1] == NAMED_IN_ARTICLE and cited.review_state is ReviewState.PENDING
    assert registry.fetched == [TRIAL]
    [first, _] = pending_items(session, claim_slug=SLUG, kind="match")
    assert NAMED_IN_ARTICLE in first.reasons


@pytest.mark.parametrize(
    ("probability", "state", "by"),
    [
        (0.7, ReviewState.PENDING, None),
        (0.01, ReviewState.REJECTED, Decider.RULE),
        (0.9, ReviewState.APPROVED, Decider.RULE),
    ],
)
def test_being_named_approves_nothing_and_the_rules_decide_as_for_any_candidate(
    session: Session, probability: float, state: ReviewState, by: Decider | None
):
    claim = new_claim(session)

    decided = named(
        session,
        claim,
        backend=Reading(default=probability),
        reject_below=0.05,
        accept_trial_above=0.8,
        accept_paper_above=0.8,
    )

    assert [m.review_state for m in decided] == [state, state]
    assert [m.reviewed_by for m in decided] == [by, by]


def test_a_candidate_the_claim_has_keeps_its_state_and_gains_the_reason(session: Session):
    claim = new_claim(session)
    [searched] = find(session, claim, FakePapers({PHRASE_SEARCH: [paper(DOI)]}), accept_above=0.8)
    before = (searched.score, searched.review_state)
    registry = Registry()

    [trial] = named(session, claim, registry=registry)
    again = named(session, claim, registry=registry)

    assert again == [] and registry.fetched == [TRIAL]
    assert (searched.score, searched.review_state) == before
    assert searched.reasons[-1] == NAMED_IN_ARTICLE
    assert searched.reasons.count(NAMED_IN_ARTICLE) == 1
    assert trial.external_id == TRIAL and len(paper_matches(session)) == 1


def test_an_identifier_its_source_does_not_have_adds_nothing(session: Session):
    claim = new_claim(session)

    class Empty(Registry):
        def fetch_trial(self, nct_id: str):
            return None

    assert named(session, claim, registry=Empty(), papers=FakePapers()) == []


def test_a_failed_scoring_keeps_none_of_the_candidates(session: Session):
    claim = new_claim(session)

    with pytest.raises(DecisionFailed):
        named(session, claim, backend=Broken())

    assert session.query(EntityMatch).count() == 0


def test_the_reason_survives_a_rescore(session: Session):
    claim = new_claim(session)
    _, cited = named(session, claim)

    rescore_papers(session, claim, papers=NAMED, backend=Reading(default=0.9), now=NOW)

    assert cited.reasons[-1] == NAMED_IN_ARTICLE
