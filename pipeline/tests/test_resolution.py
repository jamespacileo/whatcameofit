"""Entities and candidate matches, tested through `thenwhat.claims.entities` and
`resolve_claim` with fake registries and a fake decision backend on a real database.

Scenario names are from openspec entity-resolution and decision-steps.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import (
    EntityNotFound,
    add_entity,
    add_synonym,
    entities_of,
    set_origin_paper,
)
from thenwhat.claims.entry import DuplicateClaim, add_claim
from thenwhat.db.models import Claim, DecisionLog, EntityMatch
from thenwhat.decide.core import BackendAnswer, DecisionFailed
from thenwhat.decide.steps import suggest_evidence_stage
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.resolve.service import resolve_claim
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
DOI = "10.1000/example.2018.1"


def trial(nct_id: str, title: str = "A trial") -> SourceRecord:
    payload = {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": title},
            "armsInterventionsModule": {"interventions": [{"name": "EX-1"}]},
        }
    }
    return SourceRecord(
        "clinicaltrials.gov", nct_id, f"https://clinicaltrials.gov/study/{nct_id}", payload, NOW
    )


class FakeTrials:
    """A trial registry that answers each search term from a table."""

    def __init__(self, results: dict[str, list[SourceRecord]]) -> None:
        self.results = results
        self.searched: list[str] = []

    def search_trials(self, intervention: str) -> list[SourceRecord]:
        self.searched.append(intervention)
        return self.results.get(intervention, [])


class FakeDois:
    def __init__(self, known: set[str]) -> None:
        self.known = known

    def work(self, doi: str) -> SourceRecord | None:
        if doi not in self.known:
            return None
        return SourceRecord("crossref", doi, f"https://doi.org/{doi}", {"title": ["A paper"]}, NOW)


class Scoring:
    """A decision backend that gives every candidate the same probability of being a match."""

    name = "fake"

    def __init__(self, match_probability: float = 0.7, stage: str = "animal") -> None:
        self.match_probability = match_probability
        self.stage = stage
        self.states: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        self.states.append(state)
        if step == "entity_match":
            p = self.match_probability
            choice = "match" if p >= 0.5 else "not_a_match"
            return BackendAnswer(choice, {"match": p, "not_a_match": 1 - p})
        others = (1 - 0.7) / (len(options) - 1)
        return BackendAnswer(self.stage, {o: 0.7 if o == self.stage else others for o in options})


class Broken:
    name = "broken"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise RuntimeError("no model")


def new_claim(session: Session, slug: str = "tooth-regrowth-ex1", **overrides) -> Claim:
    values = {
        "slug": slug,
        "headline": "Antibody regrows teeth in mice",
        "vertical": "dental-regeneration",
        "intervention": "EX-1 antibody",
        "indication": "tooth agenesis",
    }
    return add_claim(session, **(values | overrides))


def resolve(session: Session, claim: Claim, trials=None, dois=None, backend=None):
    return resolve_claim(
        session,
        claim,
        trials=trials or FakeTrials({}),
        dois=dois or FakeDois(set()),
        backend=backend or Scoring(),
        now=NOW,
    )


def matches(session: Session) -> list[EntityMatch]:
    return list(session.scalars(select(EntityMatch).order_by(EntityMatch.id)))


# --- entities --------------------------------------------------------------------


def test_entity_of_each_type_can_be_added(session: Session):
    claim = new_claim(session)

    add_entity(session, claim.slug, type=EntityType.COMPANY, name="Example Biopharma")
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi=DOI)

    listed = {(e.type, e.name, e.doi) for e in entities_of(session, claim)}
    assert (EntityType.COMPANY, "Example Biopharma", None) in listed
    assert (EntityType.PAPER, "A paper", DOI) in listed


def test_added_synonym_is_used_in_later_registry_searches(session: Session):
    """Scenario: Compound renamed"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "TRG-999")
    trials = FakeTrials({})

    resolve(session, claim, trials=trials)

    assert trials.searched == ["EX-1 antibody", "TRG-999"]


def test_synonym_is_not_added_twice(session: Session):
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "TRG-999")

    entity = add_synonym(session, claim.slug, "ex-1 ANTIBODY", " trg-999 ")

    assert entity.synonyms == ["TRG-999"]


def test_synonym_that_makes_two_claims_the_same_is_refused(session: Session):
    new_claim(session)
    new_claim(session, "other-claim", intervention="TRG-999")

    with pytest.raises(DuplicateClaim):
        add_synonym(session, "tooth-regrowth-ex1", "EX-1 antibody", "TRG-999")


def test_synonym_for_an_unknown_entity_is_refused(session: Session):
    claim = new_claim(session)

    with pytest.raises(EntityNotFound):
        add_synonym(session, claim.slug, "No such thing", "x")


def test_second_origin_paper_replaces_the_first(session: Session):
    """Scenario: Second origin paper"""
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="First paper")
    add_entity(session, claim.slug, type=EntityType.PAPER, name="Second paper")
    set_origin_paper(session, claim.slug, "First paper")

    set_origin_paper(session, claim.slug, "Second paper")

    origin = [e.name for e in entities_of(session, claim) if e.is_origin_paper]
    assert origin == ["Second paper"]


def test_only_a_paper_can_be_the_origin_paper(session: Session):
    claim = new_claim(session)

    with pytest.raises(EntityNotFound):
        set_origin_paper(session, claim.slug, "EX-1 antibody")


# --- candidate matches -------------------------------------------------------------


def test_each_search_term_contributes_its_trials(session: Session):
    """Scenario: Intervention with two synonyms"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "EX-1")
    add_synonym(session, claim.slug, "EX-1 antibody", "TRG-999")
    trials = FakeTrials(
        {
            "EX-1 antibody": [trial("NCT00000001")],
            "EX-1": [trial("NCT00000002")],
            "TRG-999": [trial("NCT00000003")],
        }
    )

    resolve(session, claim, trials=trials)

    assert [(m.source_name, m.external_id) for m in matches(session)] == [
        ("clinicaltrials.gov", "NCT00000001"),
        ("clinicaltrials.gov", "NCT00000002"),
        ("clinicaltrials.gov", "NCT00000003"),
    ]


def test_trial_found_by_two_terms_is_one_candidate(session: Session):
    """Scenario: Same trial found by two terms"""
    claim = new_claim(session)
    add_synonym(session, claim.slug, "EX-1 antibody", "EX-1")
    same = trial("NCT00000001")

    resolve(session, claim, trials=FakeTrials({"EX-1 antibody": [same], "EX-1": [same]}))

    assert len(matches(session)) == 1


def test_paper_with_a_doi_is_looked_up(session: Session):
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi=DOI)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="No DOI given")

    resolve(session, claim, dois=FakeDois({DOI}))

    assert [(m.source_name, m.external_id) for m in matches(session)] == [("crossref", DOI)]


def test_doi_the_registry_does_not_know_gives_no_candidate(session: Session):
    claim = new_claim(session)
    add_entity(session, claim.slug, type=EntityType.PAPER, name="A paper", doi=DOI)

    resolve(session, claim, dois=FakeDois(set()))

    assert matches(session) == []


def test_high_scoring_match_stays_pending(session: Session):
    """Scenario: High-scoring match"""
    claim = new_claim(session)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
        backend=Scoring(0.99),
    )

    [match] = matches(session)
    assert (match.score, match.review_state) == (pytest.approx(0.99), ReviewState.PENDING)


def test_low_scoring_match_stays_pending_and_visible(session: Session):
    """Scenario: Low-scoring match"""
    claim = new_claim(session)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
        backend=Scoring(0.05),
    )

    [match] = matches(session)
    assert (match.score, match.review_state) == (pytest.approx(0.05), ReviewState.PENDING)


def test_rejected_match_found_again_stays_rejected(session: Session):
    """Scenario: Rejected match found again"""
    claim = new_claim(session)
    trials = FakeTrials({"EX-1 antibody": [trial("NCT00000001")]})
    resolve(session, claim, trials=trials)
    record_decision(matches(session)[0], ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)

    again = resolve(session, claim, trials=trials)

    assert again == []
    assert [m.review_state for m in matches(session)] == [ReviewState.REJECTED]


def test_resolve_returns_only_the_new_candidates(session: Session):
    claim = new_claim(session)
    resolve(session, claim, trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}))

    new = resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001"), trial("NCT00000002")]}),
    )

    assert [m.external_id for m in new] == ["NCT00000002"]


# --- decision steps ----------------------------------------------------------------


def test_candidate_score_is_the_logged_probability_of_a_match(session: Session):
    """Scenario: Scoring a candidate match"""
    claim = new_claim(session)
    backend = Scoring(0.83)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001", "EX-1 in adults")]}),
        backend=backend,
    )

    [match] = matches(session)
    [entry] = session.scalars(select(DecisionLog)).all()
    assert (entry.step, entry.input_ref) == ("entity_match", f"entity_match:{match.id}")
    assert entry.options == ["match", "not_a_match"]
    assert entry.output is not None
    assert (
        match.score == pytest.approx(entry.output["probabilities"]["match"]) == pytest.approx(0.83)
    )
    assert "EX-1 antibody" in backend.states[0] and "EX-1 in adults" in backend.states[0]


def test_confident_decision_still_leaves_the_candidate_pending(session: Session):
    """Scenario: Confident decision"""
    claim = new_claim(session)

    resolve(
        session,
        claim,
        trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
        backend=Scoring(0.99),
    )

    assert matches(session)[0].review_state is ReviewState.PENDING


def test_failed_scoring_stores_no_candidates(session: Session):
    claim = new_claim(session)

    with pytest.raises(DecisionFailed):
        resolve(
            session,
            claim,
            trials=FakeTrials({"EX-1 antibody": [trial("NCT00000001")]}),
            backend=Broken(),
        )

    assert matches(session) == []


def test_suggested_stage_is_logged_and_the_claims_stage_stays_empty(session: Session):
    """Scenario: Suggested but unconfirmed stage"""
    claim = new_claim(session)

    decision = suggest_evidence_stage(session, Scoring(stage="animal"), claim, now=NOW)

    [entry] = session.scalars(select(DecisionLog)).all()
    assert decision.choice == "animal"
    assert (entry.step, entry.input_ref, entry.human_label) == (
        "evidence_stage",
        f"claim:{claim.id}",
        None,
    )
    assert entry.options == ["in_vitro", "animal", "early_human", "late_human"]
    assert claim.evidence_stage is None
